"""Core workflow for estimating future aortic dimensions in BAV follow-up.

The code follows the workflow used in the manuscript:
1. check the local structured echocardiography schema;
2. normalize BAV morphology and valve dysfunction labels;
3. construct current-to-future pairs without using future measurements as inputs;
4. fit a residual model for aortic sinus and ascending aorta dimensions;
5. evaluate training-period and deployment-period predictions;
6. export tabular outputs for manuscript figures and local audit.

The implementation is intentionally explicit. Each step can be inspected, replaced,
or extended by a local clinical-data team before deployment.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from .schema import (
    CATEGORICAL_COLUMNS,
    DEFAULT_FEATURE_COLUMNS,
    NUMERIC_COLUMNS,
    TARGET_COLUMNS,
    check_schema,
)


def _clean_grade(x: Any) -> str:
    """Map local valve dysfunction labels to compact ordinal categories."""
    if pd.isna(x):
        return "unknown"
    s = str(x).strip().lower().replace(" ", "_").replace("-", "_")
    mapping = {
        "0": "none",
        "1": "mild",
        "2": "moderate",
        "3": "severe",
        "nan": "unknown",
        "": "unknown",
    }
    return mapping.get(s, s)


def _clean_morphology(x: Any) -> str:
    """Map common local BAV morphology labels to a standard vocabulary."""
    if pd.isna(x):
        return "unknown"
    s = str(x).strip().lower().replace(" ", "_").replace("-", "_")
    synonyms = {
        "right_left": "rl_fusion",
        "rl": "rl_fusion",
        "right_non": "rn_fusion",
        "r_n": "rn_fusion",
        "left_non": "ln_fusion",
        "l_n": "ln_fusion",
        "two_sinus": "two_sinus",
        "three_sinus": "three_sinus",
        "trileaflet": "trileaflet",
    }
    return synonyms.get(s, s if s else "unknown")


def load_and_standardize(path: str | Path) -> pd.DataFrame:
    """Load a local CSV and standardize dates, categories, and derived features."""
    path = Path(path)
    df = pd.read_csv(path)
    report = check_schema(df.columns)
    if not report.ok:
        raise ValueError(f"Missing required columns: {report.missing_required}")

    df = df.copy()
    df["exam_date"] = pd.to_datetime(df["exam_date"], errors="coerce")
    if df["exam_date"].isna().any():
        raise ValueError("exam_date contains missing or unparsable values.")

    df["bav_positive"] = df["bav_positive"].astype(int)
    for col in ["aortic_stenosis_grade", "aortic_regurgitation_grade"]:
        df[col] = df[col].map(_clean_grade)
    for col in ["vmc1", "vmc2"]:
        df[col] = df[col].map(_clean_morphology)
    df["sex"] = df["sex"].astype(str).str.strip().str.lower().replace({"m": "male", "f": "female"})

    if "body_surface_area_m2" not in df.columns:
        # Mosteller estimate. Use a site-provided value when available.
        df["body_surface_area_m2"] = np.sqrt((df["height_cm"] * df["weight_kg"]) / 3600.0)
    df["pulse_pressure"] = df["systolic_bp"] - df["diastolic_bp"]

    # Keep the feature matrix stable even if optional variables are absent locally.
    for col in NUMERIC_COLUMNS:
        if col not in df.columns and col != "horizon_years":
            df[col] = np.nan

    return df


def build_consecutive_pairs(
    df: pd.DataFrame,
    min_horizon_years: float = 0.5,
    max_horizon_years: float | None = 5.0,
) -> pd.DataFrame:
    """Construct current-to-future pairs for BAV-positive records.

    Pseudocode:
        for each BAV-positive patient:
            sort examinations by date
            pair each examination with the next examination
            keep pairs inside the allowed follow-up interval
            use the earlier examination as predictors
            use the later examination only as endpoints

    This structure mirrors serial imaging review and avoids target leakage from the
    later examination into the model input.
    """
    rows: list[dict[str, Any]] = []
    bav = df[df["bav_positive"] == 1].sort_values(["patient_id", "exam_date"])
    for patient_id, group in bav.groupby("patient_id", sort=False):
        group = group.sort_values("exam_date").reset_index(drop=True)
        if len(group) < 2:
            continue
        for i in range(len(group) - 1):
            cur = group.iloc[i]
            fut = group.iloc[i + 1]
            horizon_years = (fut["exam_date"] - cur["exam_date"]).days / 365.25
            if horizon_years < min_horizon_years:
                continue
            if max_horizon_years is not None and horizon_years > max_horizon_years:
                continue
            rec = {c: cur.get(c, np.nan) for c in DEFAULT_FEATURE_COLUMNS if c != "horizon_years"}
            rec.update(
                {
                    "patient_id": patient_id,
                    "current_exam_date": cur["exam_date"],
                    "future_exam_date": fut["exam_date"],
                    "horizon_years": horizon_years,
                    "future_aortic_sinus_mm": fut["aortic_sinus_mm"],
                    "future_ascending_aorta_mm": fut["ascending_aorta_mm"],
                    "delta_aortic_sinus_mm": fut["aortic_sinus_mm"] - cur["aortic_sinus_mm"],
                    "delta_ascending_aorta_mm": fut["ascending_aorta_mm"] - cur["ascending_aorta_mm"],
                }
            )
            rows.append(rec)
    return pd.DataFrame(rows)


def split_pairs_by_future_date(
    pairs: pd.DataFrame,
    validation_start: str = "2026-01-01",
    validation_end: str = "2026-03-31",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split pairs by the date of the later/reference examination."""
    start = pd.Timestamp(validation_start)
    end = pd.Timestamp(validation_end)
    future_dates = pd.to_datetime(pairs["future_exam_date"])
    val_mask = (future_dates >= start) & (future_dates <= end)
    train_mask = future_dates < start
    return pairs.loc[train_mask].reset_index(drop=True), pairs.loc[val_mask].reset_index(drop=True)


@dataclass
class TargetMetrics:
    """Target-level performance summary."""

    n: int
    mae_mm: float
    median_ae_mm: float
    within_2mm: float
    within_3mm: float
    within_5mm: float
    bias_mm: float


def evaluate_target(y_true: np.ndarray, y_pred: np.ndarray) -> TargetMetrics:
    """Compute millimeter-scale performance metrics for one target."""
    err = y_pred - y_true
    ae = np.abs(err)
    n = len(y_true)
    return TargetMetrics(
        n=int(n),
        mae_mm=float(np.mean(ae)) if n else float("nan"),
        median_ae_mm=float(np.median(ae)) if n else float("nan"),
        within_2mm=float(np.mean(ae <= 2.0) * 100.0) if n else float("nan"),
        within_3mm=float(np.mean(ae <= 3.0) * 100.0) if n else float("nan"),
        within_5mm=float(np.mean(ae <= 5.0) * 100.0) if n else float("nan"),
        bias_mm=float(np.mean(err)) if n else float("nan"),
    )


class ResidualAortaModel:
    """Two-target residual model for aortic sinus and ascending aorta dimensions."""

    def __init__(self, random_state: int = 42, xgb_params: dict[str, Any] | None = None):
        self.random_state = random_state
        default_params = {
            "n_estimators": 80,
            "max_depth": 2,
            "learning_rate": 0.05,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "reg_lambda": 1.0,
            "objective": "reg:squarederror",
            "random_state": random_state,
            "n_jobs": 1,
            "verbosity": 0,
        }
        if xgb_params:
            default_params.update(xgb_params)
        self.xgb_params = default_params
        self.feature_columns = [c for c in DEFAULT_FEATURE_COLUMNS]
        numeric_features = [c for c in NUMERIC_COLUMNS if c in self.feature_columns]
        categorical_features = [c for c in CATEGORICAL_COLUMNS if c in self.feature_columns]

        # Numeric variables are imputed with the training median. Categorical variables
        # are one-hot encoded with unknown categories ignored during later prediction.
        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", SimpleImputer(strategy="median"), numeric_features),
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("onehot", OneHotEncoder(handle_unknown="ignore")),
                        ]
                    ),
                    categorical_features,
                ),
            ]
        )
        self.models_: dict[str, Pipeline] = {}

    def fit(self, pairs: pd.DataFrame) -> "ResidualAortaModel":
        """Fit one residual regressor per aortic target."""
        if pairs.empty:
            raise ValueError("No training pairs were provided.")
        X = pairs[self.feature_columns]
        targets = {
            "aortic_sinus_mm": pairs["delta_aortic_sinus_mm"].to_numpy(),
            "ascending_aorta_mm": pairs["delta_ascending_aorta_mm"].to_numpy(),
        }
        self.models_ = {}
        for target, y in targets.items():
            pipe = Pipeline(
                steps=[
                    ("preprocess", self.preprocessor),
                    ("model", XGBRegressor(**self.xgb_params)),
                ]
            )
            pipe.fit(X, y)
            self.models_[target] = pipe
        return self

    def predict(self, pairs: pd.DataFrame) -> pd.DataFrame:
        """Predict future dimensions by adding predicted residuals to current dimensions."""
        if not self.models_:
            raise RuntimeError("Model is not fitted.")
        X = pairs[self.feature_columns]
        out = pairs[["patient_id", "current_exam_date", "future_exam_date", "horizon_years"]].copy()
        for target in TARGET_COLUMNS:
            delta = self.models_[target].predict(X)
            out[f"predicted_delta_{target}"] = delta
            out[f"predicted_future_{target}"] = pairs[target].to_numpy() + delta
            out[f"reference_future_{target}"] = pairs[f"future_{target}"]
            out[f"absolute_error_{target}"] = np.abs(
                out[f"predicted_future_{target}"] - out[f"reference_future_{target}"]
            )
        return out

    def metrics(self, pairs: pd.DataFrame) -> pd.DataFrame:
        """Return target-level metrics for a set of current-to-future pairs."""
        pred = self.predict(pairs)
        records = []
        for target in TARGET_COLUMNS:
            m = evaluate_target(
                pred[f"reference_future_{target}"].to_numpy(),
                pred[f"predicted_future_{target}"].to_numpy(),
            )
            records.append({"target": target, **asdict(m)})
        return pd.DataFrame(records)

    def export_feature_importance(self, output_csv: str | Path) -> None:
        """Export XGBoost gain-based feature importance for local review."""
        rows = []
        for target, pipe in self.models_.items():
            booster = pipe.named_steps["model"].get_booster()
            importance = booster.get_score(importance_type="gain")
            for feature, value in importance.items():
                rows.append({"target": target, "encoded_feature": feature, "gain": value})
        pd.DataFrame(rows).to_csv(output_csv, index=False)


def run_workflow(
    input_csv: str | Path,
    output_dir: str | Path,
    validation_start: str = "2026-01-01",
    validation_end: str = "2026-03-31",
) -> dict[str, Any]:
    """Run schema checking, pair construction, training, validation, and export."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_and_standardize(input_csv)
    pairs = build_consecutive_pairs(df)
    train_pairs, val_pairs = split_pairs_by_future_date(pairs, validation_start, validation_end)

    model = ResidualAortaModel().fit(train_pairs)
    train_pred = model.predict(train_pairs)
    val_pred = model.predict(val_pairs) if not val_pairs.empty else pd.DataFrame()
    train_metrics = model.metrics(train_pairs)
    val_metrics = model.metrics(val_pairs) if not val_pairs.empty else pd.DataFrame()

    pairs.to_csv(output_dir / "all_constructed_pairs.csv", index=False)
    train_pairs.to_csv(output_dir / "training_pairs.csv", index=False)
    val_pairs.to_csv(output_dir / "prospective_validation_pairs.csv", index=False)
    train_pred.to_csv(output_dir / "training_predictions.csv", index=False)
    val_pred.to_csv(output_dir / "prospective_validation_predictions.csv", index=False)
    train_metrics.to_csv(output_dir / "training_metrics.csv", index=False)
    val_metrics.to_csv(output_dir / "prospective_validation_metrics.csv", index=False)
    model.export_feature_importance(output_dir / "feature_importance_gain.csv")

    summary = {
        "n_records": int(len(df)),
        "n_pairs_total": int(len(pairs)),
        "n_training_pairs": int(len(train_pairs)),
        "n_prospective_validation_pairs": int(len(val_pairs)),
        "validation_start": validation_start,
        "validation_end": validation_end,
        "output_files": [
            "training_metrics.csv",
            "prospective_validation_metrics.csv",
            "training_predictions.csv",
            "prospective_validation_predictions.csv",
            "feature_importance_gain.csv",
        ],
    }
    with open(output_dir / "run_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary

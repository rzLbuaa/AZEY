"""Figure-generation utilities for workflow outputs.

The functions in this module read the CSV files exported by the workflow and
produce manuscript-style diagnostic plots. They are deliberately small and rely
only on tabular outputs, so the same plotting code can be used after a local run
or after a site-specific recalibration.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TARGETS = ["aortic_sinus_mm", "ascending_aorta_mm"]
TARGET_LABELS = {
    "aortic_sinus_mm": "Aortic sinus",
    "ascending_aorta_mm": "Ascending aorta",
}
HORIZON_BINS = [0.5, 1.0, 2.0, 3.0, 5.0]
HORIZON_LABELS = ["0.5-1 year", "1-2 years", "2-3 years", "3-5 years"]


@dataclass(frozen=True)
class FigurePaths:
    """Locations of generated figure files."""

    files: list[Path]


def _target_label(target: str) -> str:
    return TARGET_LABELS.get(target, target.replace("_", " ").replace(" mm", ""))


def _save_current_figure(path: Path, dpi: int = 300) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close()


def _read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def plot_predicted_vs_reference(predictions: pd.DataFrame, target: str, output_path: Path, title_prefix: str) -> None:
    """Plot predicted-versus-reference future diameter for one target.

    Expected columns:
        reference_future_<target>
        predicted_future_<target>

    The diagonal line marks perfect agreement. The annotation reports n and MAE
    calculated directly from the points shown in the figure.
    """
    ref_col = f"reference_future_{target}"
    pred_col = f"predicted_future_{target}"
    if predictions.empty or ref_col not in predictions or pred_col not in predictions:
        return

    ref = predictions[ref_col].astype(float).to_numpy()
    pred = predictions[pred_col].astype(float).to_numpy()
    valid = np.isfinite(ref) & np.isfinite(pred)
    ref = ref[valid]
    pred = pred[valid]
    if len(ref) == 0:
        return

    mae = float(np.mean(np.abs(pred - ref)))
    lower = float(min(ref.min(), pred.min()) - 2.0)
    upper = float(max(ref.max(), pred.max()) + 2.0)

    plt.figure(figsize=(4.8, 4.5))
    plt.scatter(ref, pred, s=36, alpha=0.7)
    plt.plot([lower, upper], [lower, upper], linewidth=1.2)
    plt.xlim(lower, upper)
    plt.ylim(lower, upper)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.xlabel("Reference diameter (mm)")
    plt.ylabel("Predicted diameter (mm)")
    plt.title(f"{title_prefix}: {_target_label(target)}")
    plt.text(lower + 0.6, upper - 2.0, f"n = {len(ref)}\nMAE = {mae:.2f} mm", fontsize=9)
    plt.grid(True, linewidth=0.4, alpha=0.5)
    _save_current_figure(output_path)


def plot_training_vs_validation_mae(training_metrics: pd.DataFrame, validation_metrics: pd.DataFrame, output_path: Path) -> None:
    """Plot target-level MAE for model training and prospective validation."""
    frames = []
    if not training_metrics.empty:
        tmp = training_metrics.copy()
        tmp["analysis_set"] = "Training"
        frames.append(tmp)
    if not validation_metrics.empty:
        tmp = validation_metrics.copy()
        tmp["analysis_set"] = "Prospective validation"
        frames.append(tmp)
    if not frames:
        return

    metrics = pd.concat(frames, ignore_index=True)
    labels = []
    values = []
    for analysis_set in ["Training", "Prospective validation"]:
        for target in TARGETS:
            row = metrics[(metrics["analysis_set"] == analysis_set) & (metrics["target"] == target)]
            if row.empty:
                continue
            labels.append(f"{analysis_set}\n{_target_label(target)}")
            values.append(float(row.iloc[0]["mae_mm"]))

    if not values:
        return

    plt.figure(figsize=(7.2, 4.2))
    x = np.arange(len(values))
    plt.bar(x, values)
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("MAE (mm)")
    plt.title("Training and prospective-validation MAE")
    plt.grid(axis="y", linewidth=0.4, alpha=0.5)
    _save_current_figure(output_path)


def plot_validation_tolerance(validation_metrics: pd.DataFrame, output_path: Path) -> None:
    """Plot within-2 mm, within-3 mm, and within-5 mm accuracy for validation outputs."""
    if validation_metrics.empty:
        return
    rows = []
    for target in TARGETS:
        row = validation_metrics[validation_metrics["target"] == target]
        if row.empty:
            continue
        r = row.iloc[0]
        rows.append(
            {
                "target": _target_label(target),
                "Within 2 mm": float(r["within_2mm"]),
                "Within 3 mm": float(r["within_3mm"]),
                "Within 5 mm": float(r["within_5mm"]),
            }
        )
    if not rows:
        return

    df = pd.DataFrame(rows).set_index("target")
    plt.figure(figsize=(6.2, 4.2))
    x = np.arange(len(df.index))
    width = 0.24
    for i, col in enumerate(["Within 2 mm", "Within 3 mm", "Within 5 mm"]):
        plt.bar(x + (i - 1) * width, df[col].to_numpy(), width=width, label=col)
    plt.xticks(x, df.index)
    plt.ylim(0, 105)
    plt.ylabel("Predictions within tolerance (%)")
    plt.title("Prospective-validation tolerance accuracy")
    plt.legend(frameon=False)
    plt.grid(axis="y", linewidth=0.4, alpha=0.5)
    _save_current_figure(output_path)


def _horizon_summary_from_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compute horizon-bin MAE values from validation prediction rows."""
    if predictions.empty or "horizon_years" not in predictions:
        return pd.DataFrame()
    data = predictions.copy()
    data["horizon_window"] = pd.cut(
        data["horizon_years"],
        bins=HORIZON_BINS,
        labels=HORIZON_LABELS,
        include_lowest=True,
        right=True,
    )
    records: list[dict[str, float | int | str]] = []
    for label in HORIZON_LABELS:
        subset = data[data["horizon_window"] == label]
        if subset.empty:
            continue
        rec: dict[str, float | int | str] = {"horizon_window": label, "n": int(len(subset))}
        for target in TARGETS:
            ae_col = f"absolute_error_{target}"
            if ae_col in subset:
                rec[f"mae_{target}"] = float(subset[ae_col].mean())
        records.append(rec)
    return pd.DataFrame(records)


def plot_horizon_mae(validation_predictions: pd.DataFrame, output_path: Path) -> None:
    """Plot validation MAE by follow-up window from prediction rows."""
    summary = _horizon_summary_from_predictions(validation_predictions)
    if summary.empty:
        return

    labels = summary["horizon_window"].astype(str).tolist()
    x = np.arange(len(labels))
    width = 0.36
    sinus = summary.get("mae_aortic_sinus_mm", pd.Series([np.nan] * len(summary))).to_numpy(dtype=float)
    ascending = summary.get("mae_ascending_aorta_mm", pd.Series([np.nan] * len(summary))).to_numpy(dtype=float)

    plt.figure(figsize=(6.8, 4.2))
    plt.bar(x - width / 2, sinus, width=width, label="Aortic sinus")
    plt.bar(x + width / 2, ascending, width=width, label="Ascending aorta")
    plt.xticks(x, labels, rotation=15, ha="right")
    plt.ylabel("MAE (mm)")
    plt.xlabel("Follow-up window")
    plt.title("Prospective-validation MAE by follow-up window")
    plt.legend(frameon=False)
    plt.grid(axis="y", linewidth=0.4, alpha=0.5)
    _save_current_figure(output_path)


def make_all_figures(output_dir: str | Path, figure_dir: str | Path = "figures") -> FigurePaths:
    """Generate all standard figures from workflow output CSV files."""
    output_dir = Path(output_dir)
    figure_dir = Path(figure_dir)
    figure_dir.mkdir(parents=True, exist_ok=True)

    train_pred = _read_csv_if_exists(output_dir / "training_predictions.csv")
    val_pred = _read_csv_if_exists(output_dir / "prospective_validation_predictions.csv")
    train_metrics = _read_csv_if_exists(output_dir / "training_metrics.csv")
    val_metrics = _read_csv_if_exists(output_dir / "prospective_validation_metrics.csv")

    outputs = [
        (train_pred, "aortic_sinus_mm", figure_dir / "training_aortic_sinus.png", "Model training"),
        (train_pred, "ascending_aorta_mm", figure_dir / "training_ascending_aorta.png", "Model training"),
        (val_pred, "aortic_sinus_mm", figure_dir / "validation_aortic_sinus.png", "Prospective validation"),
        (val_pred, "ascending_aorta_mm", figure_dir / "validation_ascending_aorta.png", "Prospective validation"),
    ]
    generated: list[Path] = []
    for df, target, path, title in outputs:
        before = path.exists()
        plot_predicted_vs_reference(df, target, path, title)
        if path.exists() and (not before or path not in generated):
            generated.append(path)

    grouped_outputs = [
        (lambda: plot_training_vs_validation_mae(train_metrics, val_metrics, figure_dir / "training_vs_validation_mae.png"), figure_dir / "training_vs_validation_mae.png"),
        (lambda: plot_validation_tolerance(val_metrics, figure_dir / "validation_tolerance_accuracy.png"), figure_dir / "validation_tolerance_accuracy.png"),
        (lambda: plot_horizon_mae(val_pred, figure_dir / "validation_horizon_mae.png"), figure_dir / "validation_horizon_mae.png"),
    ]
    for fn, path in grouped_outputs:
        before = path.exists()
        fn()
        if path.exists() and (not before or path not in generated):
            generated.append(path)

    return FigurePaths(files=generated)

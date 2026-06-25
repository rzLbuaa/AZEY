"""Workflow agent for BAV aortic dimension estimation.

The agent is a deterministic orchestration layer around the modelling workflow. It
keeps the operational steps explicit: schema review, label harmonization,
current-to-future pair construction, temporal deployment split, residual model
training, evaluation, and export. Local teams can replace any step while keeping
one stable interface for running the workflow.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .pipeline import (
    ResidualAortaModel,
    build_consecutive_pairs,
    load_and_standardize,
    split_pairs_by_future_date,
)
from .schema import check_schema


@dataclass(frozen=True)
class WorkflowAgentConfig:
    """Configuration for a local workflow run."""

    validation_start: str = "2026-01-01"
    validation_end: str = "2026-03-31"
    min_horizon_years: float = 0.5
    max_horizon_years: float | None = 5.0
    random_state: int = 42
    xgb_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowStepRecord:
    """Audit record for one completed workflow step."""

    step: str
    status: str
    details: dict[str, Any]


@dataclass
class WorkflowRunResult:
    """File-level output summary from a workflow-agent run."""

    n_records: int
    n_pairs_total: int
    n_training_pairs: int
    n_prospective_validation_pairs: int
    validation_start: str
    validation_end: str
    output_dir: str
    audit_steps: list[WorkflowStepRecord]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["audit_steps"] = [asdict(x) for x in self.audit_steps]
        return data


class AortaWorkflowAgent:
    """Deterministic controller for the BAV aortic dimension workflow.

    Operational sequence:
        1. Review the local table schema.
        2. Standardize dates, morphology labels, and valve dysfunction grades.
        3. Build current-to-future pairs using only earlier-visit inputs.
        4. Split pairs by the deployment/reference visit date.
        5. Train a residual model on the training-period pairs.
        6. Evaluate training and deployment-period predictions.
        7. Export pair files, predictions, metrics, feature importance, and an audit log.
    """

    def __init__(self, config: WorkflowAgentConfig | None = None):
        self.config = config or WorkflowAgentConfig()
        self.audit_steps: list[WorkflowStepRecord] = []
        self.model: ResidualAortaModel | None = None

    def _record(self, step: str, status: str, **details: Any) -> None:
        self.audit_steps.append(WorkflowStepRecord(step=step, status=status, details=details))

    def review_schema(self, input_csv: str | Path) -> dict[str, Any]:
        """Inspect the input columns before running the modelling workflow."""
        header = pd.read_csv(input_csv, nrows=0)
        report = check_schema(header.columns)
        payload = asdict(report)
        payload["ok"] = report.ok
        self._record("schema_review", "passed" if report.ok else "failed", **payload)
        if not report.ok:
            raise ValueError(f"Missing required columns: {report.missing_required}")
        return payload

    def prepare_records(self, input_csv: str | Path) -> pd.DataFrame:
        """Load and harmonize the local echocardiography table."""
        df = load_and_standardize(input_csv)
        self._record(
            "record_preparation",
            "completed",
            n_records=int(len(df)),
            n_patients=int(df["patient_id"].nunique()) if "patient_id" in df else None,
        )
        return df

    def construct_pairs(self, records: pd.DataFrame) -> pd.DataFrame:
        """Create consecutive BAV-positive current-to-future observations."""
        pairs = build_consecutive_pairs(
            records,
            min_horizon_years=self.config.min_horizon_years,
            max_horizon_years=self.config.max_horizon_years,
        )
        self._record(
            "pair_construction",
            "completed",
            n_pairs=int(len(pairs)),
            min_horizon_years=self.config.min_horizon_years,
            max_horizon_years=self.config.max_horizon_years,
        )
        return pairs

    def split_pairs(self, pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Separate training-period and deployment-period/reference pairs."""
        train_pairs, validation_pairs = split_pairs_by_future_date(
            pairs,
            validation_start=self.config.validation_start,
            validation_end=self.config.validation_end,
        )
        self._record(
            "temporal_split",
            "completed",
            n_training_pairs=int(len(train_pairs)),
            n_prospective_validation_pairs=int(len(validation_pairs)),
            validation_start=self.config.validation_start,
            validation_end=self.config.validation_end,
        )
        return train_pairs, validation_pairs

    def fit_model(self, training_pairs: pd.DataFrame) -> ResidualAortaModel:
        """Fit the two-target residual model."""
        model = ResidualAortaModel(
            random_state=self.config.random_state,
            xgb_params=self.config.xgb_params,
        ).fit(training_pairs)
        self.model = model
        self._record("model_training", "completed", n_training_pairs=int(len(training_pairs)))
        return model

    def export_outputs(
        self,
        output_dir: str | Path,
        pairs: pd.DataFrame,
        training_pairs: pd.DataFrame,
        validation_pairs: pd.DataFrame,
        model: ResidualAortaModel,
    ) -> dict[str, str]:
        """Write workflow artifacts for review, plotting, and reporting."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        training_predictions = model.predict(training_pairs)
        validation_predictions = model.predict(validation_pairs) if not validation_pairs.empty else pd.DataFrame()
        training_metrics = model.metrics(training_pairs)
        validation_metrics = model.metrics(validation_pairs) if not validation_pairs.empty else pd.DataFrame()

        files = {
            "all_pairs": "all_constructed_pairs.csv",
            "training_pairs": "training_pairs.csv",
            "prospective_validation_pairs": "prospective_validation_pairs.csv",
            "training_predictions": "training_predictions.csv",
            "prospective_validation_predictions": "prospective_validation_predictions.csv",
            "training_metrics": "training_metrics.csv",
            "prospective_validation_metrics": "prospective_validation_metrics.csv",
            "feature_importance": "feature_importance_gain.csv",
            "audit_log": "workflow_agent_audit.json",
        }
        pairs.to_csv(output_dir / files["all_pairs"], index=False)
        training_pairs.to_csv(output_dir / files["training_pairs"], index=False)
        validation_pairs.to_csv(output_dir / files["prospective_validation_pairs"], index=False)
        training_predictions.to_csv(output_dir / files["training_predictions"], index=False)
        validation_predictions.to_csv(output_dir / files["prospective_validation_predictions"], index=False)
        training_metrics.to_csv(output_dir / files["training_metrics"], index=False)
        validation_metrics.to_csv(output_dir / files["prospective_validation_metrics"], index=False)
        model.export_feature_importance(output_dir / files["feature_importance"])
        self._record("export", "completed", files=list(files.values()))
        with open(output_dir / files["audit_log"], "w", encoding="utf-8") as f:
            json.dump([asdict(x) for x in self.audit_steps], f, indent=2, ensure_ascii=False, default=str)
        return files

    def run(self, input_csv: str | Path, output_dir: str | Path) -> WorkflowRunResult:
        """Run the complete workflow through the agent interface."""
        self.review_schema(input_csv)
        records = self.prepare_records(input_csv)
        pairs = self.construct_pairs(records)
        training_pairs, validation_pairs = self.split_pairs(pairs)
        model = self.fit_model(training_pairs)
        self.export_outputs(output_dir, pairs, training_pairs, validation_pairs, model)

        result = WorkflowRunResult(
            n_records=int(len(records)),
            n_pairs_total=int(len(pairs)),
            n_training_pairs=int(len(training_pairs)),
            n_prospective_validation_pairs=int(len(validation_pairs)),
            validation_start=self.config.validation_start,
            validation_end=self.config.validation_end,
            output_dir=str(output_dir),
            audit_steps=self.audit_steps,
        )
        with open(Path(output_dir) / "run_summary.json", "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        return result

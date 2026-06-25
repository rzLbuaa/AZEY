"""Reusable workflow skill interface.

The skill interface provides a small programmatic contract for integrating the
BAV aortic dimension workflow into a local data-processing environment. It wraps
the workflow agent and exposes the expected input schema, output artifacts, and
single-call execution method.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .agent import AortaWorkflowAgent, WorkflowAgentConfig
from .schema import OPTIONAL_COLUMNS, REQUIRED_COLUMNS


@dataclass(frozen=True)
class SkillInputSpec:
    """Input contract for a workflow-skill run."""

    required_columns: list[str]
    optional_columns: list[str]
    accepted_file_format: str = "CSV"
    row_unit: str = "one row per echocardiographic examination"


@dataclass(frozen=True)
class SkillOutputSpec:
    """Output contract for a workflow-skill run."""

    output_files: list[str]


class BAVAortaPredictionSkill:
    """Packaged skill for running the aortic dimension workflow."""

    name = "bav_aorta_prediction_workflow"
    description = (
        "Estimate future aortic sinus and ascending aorta dimensions from "
        "routine structured echocardiography records."
    )

    def __init__(self, config: WorkflowAgentConfig | None = None):
        self.config = config or WorkflowAgentConfig()

    @property
    def input_spec(self) -> SkillInputSpec:
        return SkillInputSpec(required_columns=list(REQUIRED_COLUMNS), optional_columns=list(OPTIONAL_COLUMNS))

    @property
    def output_spec(self) -> SkillOutputSpec:
        return SkillOutputSpec(
            output_files=[
                "all_constructed_pairs.csv",
                "training_pairs.csv",
                "prospective_validation_pairs.csv",
                "training_predictions.csv",
                "prospective_validation_predictions.csv",
                "training_metrics.csv",
                "prospective_validation_metrics.csv",
                "feature_importance_gain.csv",
                "workflow_agent_audit.json",
                "run_summary.json",
            ]
        )

    def describe(self) -> dict[str, Any]:
        """Return a plain dictionary describing the skill contract."""
        return {
            "name": self.name,
            "description": self.description,
            "input_spec": asdict(self.input_spec),
            "output_spec": asdict(self.output_spec),
            "configuration": asdict(self.config),
        }

    def run(self, input_csv: str | Path, output_dir: str | Path) -> dict[str, Any]:
        """Execute the skill and return the run summary as a dictionary."""
        agent = AortaWorkflowAgent(self.config)
        result = agent.run(input_csv=input_csv, output_dir=output_dir)
        return result.to_dict()

"""Run the workflow through the agent interface using the example records."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bav_aorta_workflow.agent import AortaWorkflowAgent, WorkflowAgentConfig


if __name__ == "__main__":
    config = WorkflowAgentConfig(
        validation_start="2026-01-01",
        validation_end="2026-03-31",
    )
    result = AortaWorkflowAgent(config).run(
        input_csv=Path("examples/example_echo_records.csv"),
        output_dir=Path("example_outputs_agent"),
    )
    print(result.to_dict())

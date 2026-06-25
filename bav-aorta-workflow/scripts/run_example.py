"""Run the workflow using the example records created by create_example_records.py."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from bav_aorta_workflow.pipeline import run_workflow


if __name__ == "__main__":
    summary = run_workflow(
        input_csv=Path("examples/example_echo_records.csv"),
        output_dir=Path("example_outputs"),
        validation_start="2026-01-01",
        validation_end="2026-03-31",
    )
    print(summary)

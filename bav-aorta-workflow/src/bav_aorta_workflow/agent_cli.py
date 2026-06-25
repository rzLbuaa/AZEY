"""Command-line interface for the workflow-agent entry point."""
from __future__ import annotations

import argparse
import json

from .agent import AortaWorkflowAgent, WorkflowAgentConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BAV aortic dimension workflow through the agent interface.")
    parser.add_argument("--input", required=True, help="CSV file with structured echocardiography records.")
    parser.add_argument("--output-dir", required=True, help="Directory for workflow outputs.")
    parser.add_argument("--validation-start", default="2026-01-01", help="Start date for deployment-period validation.")
    parser.add_argument("--validation-end", default="2026-03-31", help="End date for deployment-period validation.")
    parser.add_argument("--min-horizon-years", type=float, default=0.5, help="Minimum follow-up interval retained for pairing.")
    parser.add_argument("--max-horizon-years", type=float, default=5.0, help="Maximum follow-up interval retained for pairing.")
    args = parser.parse_args()

    config = WorkflowAgentConfig(
        validation_start=args.validation_start,
        validation_end=args.validation_end,
        min_horizon_years=args.min_horizon_years,
        max_horizon_years=args.max_horizon_years,
    )
    result = AortaWorkflowAgent(config).run(input_csv=args.input, output_dir=args.output_dir)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

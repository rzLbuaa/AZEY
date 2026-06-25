"""Command-line interface for the BAV aortic dimension workflow."""
from __future__ import annotations

import argparse
import json

from .pipeline import run_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BAV aortic dimension workflow.")
    parser.add_argument("--input", required=True, help="CSV file with structured echocardiography records.")
    parser.add_argument("--output-dir", required=True, help="Directory for workflow outputs.")
    parser.add_argument("--validation-start", default="2026-01-01", help="Start date for deployment-period validation.")
    parser.add_argument("--validation-end", default="2026-03-31", help="End date for deployment-period validation.")
    args = parser.parse_args()
    summary = run_workflow(args.input, args.output_dir, args.validation_start, args.validation_end)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

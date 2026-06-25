"""Generate figures from workflow output CSV files."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import argparse

from bav_aorta_workflow.figures import make_all_figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate workflow figures from output CSV files.")
    parser.add_argument("--output-dir", default="example_outputs", help="Directory containing workflow CSV outputs.")
    parser.add_argument("--figure-dir", default="figures", help="Directory where figure files will be written.")
    args = parser.parse_args()
    paths = make_all_figures(args.output_dir, args.figure_dir)
    for path in paths.files:
        print(path)


if __name__ == "__main__":
    main()

"""Command-line interface for generating figures from workflow outputs."""
from __future__ import annotations

import argparse

from .figures import make_all_figures


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

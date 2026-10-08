"""Prepare G07's empty database while guarding retained G05 and G06 data."""

import argparse
import re
from pathlib import Path

from engram_experiment_support import load_credentials
from engram_goal06_prepare import main as prepare
from engram_goal07_retention import retain_previous_datasets

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args, _ = parser.parse_known_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", args.run_id):
        parser.error("Invalid run ID")
    directory = ROOT / "docs/review/spanner-compatibility/runs" / args.run_id
    if directory.exists():
        parser.error("Run ID already exists; historical evidence will not be overwritten")
    values = load_credentials(args.credentials)
    # Helper checks the run identity and retained owners before preparation writes.
    with retain_previous_datasets(values, directory):
        prepare(goal="G07", target_database="engram-g07-target")


if __name__ == "__main__":
    main()

"""G07 HTTP/worker/Spanner acceptance with read-only retained G05/G06 guards."""

import argparse
import os
import re
from pathlib import Path

from engram_experiment_support import load_credentials
from engram_goal03_implementation_demo import main as demo_main
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
    # Combined final-version fixture factory is owned by slice E.
    from engram_goal07_fixtures import fixtures

    values = load_credentials(args.credentials)
    os.environ.pop("SPANNER_EMULATOR_HOST", None)
    with retain_previous_datasets(values, directory):
        demo_main(
            goal="G07",
            fixture_factory=fixtures,
            driver_path=Path(__file__),
            retain_success=True,
            target_database="engram-g07-target",
        )


if __name__ == "__main__":
    main()

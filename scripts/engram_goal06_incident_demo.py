"""G06 HTTP/worker/Spanner journey, with a read-only G05 retention guard."""

import argparse
import json
import os
import re
from pathlib import Path

from engram_experiment_support import durable_json, fingerprint, load_credentials, read_owner
from engram_goal03_implementation_demo import main as demo_main
from engram_goal06_fixtures import fixtures
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup

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
    assert (values["GOOGLE_CLOUD_PROJECT"], values["SPANNER_INSTANCE_ID"]) == (
        "portiq-mvp",
        "engram-experiment",
    )
    os.environ.pop("SPANNER_EMULATOR_HOST", None)
    retained = json.loads(
        (
            ROOT
            / "docs/review/spanner-compatibility/runs"
            / "20261008-cloud-g05-all-01/retained-dataset.json"
        ).read_text()
    )
    client = spanner.Client(
        project=values["GOOGLE_CLOUD_PROJECT"],
        credentials=Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"]),
    )
    pool = BurstyPool()
    database = client.instance("engram-experiment").database("engram-compat-target", pool=pool)
    prepare_cleanup(database, client, pool)
    evidence = {}
    try:
        evidence["before"] = dict(fingerprints=fingerprint(database), owner=read_owner(database))
        assert evidence["before"] == dict(
            fingerprints=retained["fingerprints"], owner=[retained["owner"]]
        ), "G05 baseline differs from retained receipt"
        demo_main(
            goal="G06",
            fixture_factory=fixtures,
            driver_path=Path(__file__),
            retain_success=True,
            target_database="engram-g06-target",
        )
    finally:
        try:
            evidence["after"] = dict(fingerprints=fingerprint(database), owner=read_owner(database))
            evidence["passed"] = (
                evidence.get("before")
                == evidence["after"]
                == dict(fingerprints=retained["fingerprints"], owner=[retained["owner"]])
            )
        except BaseException as exc:
            evidence.update(passed=False, error=type(exc).__name__)
        try:
            close_database(database)
        except BaseException as exc:
            evidence.update(passed=False, close_error=type(exc).__name__)
        directory.mkdir(parents=True, exist_ok=True)
        durable_json(directory / "g05-protection.json", evidence)
        assert evidence["passed"], "G05 retention guard failed; inspect g05-protection.json"


if __name__ == "__main__":
    main()

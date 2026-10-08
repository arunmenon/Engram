"""Read-only G05/G06 receipt guards shared by G07 preparation and execution."""

import json
import os
from contextlib import contextmanager
from pathlib import Path

from engram_experiment_support import fingerprint, read_owner
from google.cloud import spanner
from google.cloud.spanner_v1.pool import BurstyPool
from google.oauth2.credentials import Credentials

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup

ROOT = Path(__file__).resolve().parents[1]
RETAINED = (
    ("G05", "engram-compat-target", "20261008-cloud-g05-all-01"),
    ("G06", "engram-g06-target", "20261008-cloud-g06-all-03"),
)


@contextmanager
def retain_previous_datasets(values, directory):
    """Permit the enclosed G07 work only after both retained receipts match.

    Only snapshot reads and connection cleanup touch retained databases. Preserve
    the enclosed failure unless a retention failure requires its own diagnosis.
    """
    assert (values["GOOGLE_CLOUD_PROJECT"], values["SPANNER_INSTANCE_ID"]) == (
        "portiq-mvp",
        "engram-experiment",
    )
    output = directory / "g05-g06-protection.json"
    if output.exists():
        raise FileExistsError("Retention evidence already exists")
    evidence = dict(datasets={})
    for goal, name, run in RETAINED:
        receipt = ROOT / "docs/review/spanner-compatibility/runs" / run / "retained-dataset.json"
        retained = json.loads(receipt.read_text())
        evidence["datasets"][goal] = dict(
            database=name,
            receipt=str(receipt),
            expected=dict(fingerprints=retained["fingerprints"], owner=[retained["owner"]]),
        )
    client = spanner.Client(
        project=values["GOOGLE_CLOUD_PROJECT"],
        credentials=Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"]),
    )
    databases = {}
    try:
        for goal, name, _ in RETAINED:
            pool = BurstyPool()
            database = client.instance("engram-experiment").database(name, pool=pool)
            databases[goal] = database
            prepare_cleanup(database, client, pool)
            record = evidence["datasets"][goal]
            record["before"] = dict(fingerprints=fingerprint(database), owner=read_owner(database))
            assert record["before"] == record["expected"], goal + " baseline differs from receipt"
        yield
    finally:
        for goal, database in databases.items():
            record = evidence["datasets"][goal]
            try:
                record["after"] = dict(
                    fingerprints=fingerprint(database), owner=read_owner(database)
                )
                record["passed"] = record.get("before") == record["after"] == record["expected"]
            except BaseException as exc:
                record.update(passed=False, error=type(exc).__name__)
            try:
                close_database(database)
            except BaseException as exc:
                record.update(passed=False, close_error=type(exc).__name__)
        evidence["passed"] = all(
            record.get("passed", False) for record in evidence["datasets"].values()
        )
        directory.mkdir(parents=True, exist_ok=True)
        # Exclusive creation: an existing historical receipt can never be replaced.
        with output.open("x") as stream:
            json.dump(evidence, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        assert evidence["passed"], "G05/G06 retention guard failed; inspect g05-g06-protection.json"

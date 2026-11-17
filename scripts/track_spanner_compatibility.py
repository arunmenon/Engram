"""Append compatibility run records and reconcile scenario results (no cloud calls).

Start before execution; finish with a sanitized JSON file containing
{"scenarios": [{"scenario_id": "ING-01", "status": "passed|failed|blocked|not_run",
"evidence": "repo-relative evidence path", "issue_numbers": "4;5"}],
"summary": "...", "cleanup": "..."}.
This records evidence supplied by the executor; it does not infer test success.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/review/spanner-compatibility"
STATUSES = {"passed", "failed", "blocked", "not_run"}


def write_summary() -> None:
    """Keep subcheck execution evidence distinct from full scenario closure."""
    from collections import Counter

    checks = []
    for directory in sorted((RECORDS / "runs").iterdir()):
        observation = directory / "observations.json"
        if not (directory / "results.json").exists() or not observation.exists():
            continue
        for check in json.loads(observation.read_text()).get("checks", []):
            verdict = check.get("verdict")
            if verdict is None and "passed" in check:
                verdict = "passed" if check["passed"] else "failed"
            checks.append(
                {
                    "run_id": directory.name,
                    "check": check.get("name", "unnamed"),
                    "scenario_ids": ";".join(check.get("scenarios", [])),
                    "verdict": verdict or "unclassified",
                    "seconds": check.get("seconds", ""),
                    "error_type": check.get("error_type", ""),
                    "evidence": str(observation.relative_to(ROOT)),
                }
            )
    with (RECORDS / "subchecks.csv").open("w", newline="") as target:
        fields = ["run_id", "check", "scenario_ids", "verdict", "seconds", "error_type", "evidence"]
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(checks)
    with (RECORDS / "scenarios.csv").open() as source:
        scenarios = list(csv.DictReader(source))
    counts = Counter(row["status"] for row in scenarios)
    cloud = Counter(row["verdict"] for row in checks if "-cloud-" in row["run_id"])
    active = [
        p.name
        for p in (RECORDS / "runs").iterdir()
        if (p / "manifest.json").exists() and not (p / "results.json").exists()
    ]
    body = (
        "# Spanner compatibility execution status\n\n"
        f"Updated: {datetime.now(UTC).isoformat()}. No compatibility sign-off.\n\n"
        f"Full scenario matrix: {len(scenarios)} rows; "
        + ", ".join(f"{status}={counts[status]}" for status in sorted(STATUSES))
        + ". `not_run` includes partially executed rows whose full assertions remain open.\n\n"
        f"Recorded cloud subchecks across all attempts: {dict(cloud)}. "
        "These counts include retries, harness failures and blocked attempts; "
        "they are not unique scenario passes or a product failure count.\n\n"
        f"Active unfinished runs: {', '.join(sorted(active)) or 'none'}.\n\n"
        "See [subchecks.csv](subchecks.csv) for every recorded subcheck, "
        "[scenarios.csv](scenarios.csv) for closure, [findings.md](findings.md) for "
        "failure interpretation and issues, and [runs.jsonl](runs.jsonl) for the ledger.\n"
    )
    (RECORDS / "status.md").write_text(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "finish", "report"])
    parser.add_argument("--run-id")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    if args.action == "report":
        write_summary()
        return
    if args.run_id is None:
        parser.error("start/finish requires --run-id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", args.run_id):
        parser.error("run ID must be a safe directory name")
    directory = RECORDS / "runs" / args.run_id
    if args.action == "start":
        if args.manifest is None:
            parser.error("start requires --manifest (sanitized, no credentials)")
        data = json.loads(args.manifest.read_text())
        if not isinstance(data, dict):
            parser.error("manifest must be an object")
        if directory.exists():
            parser.error("run already exists; use a new run ID")
        data["run_id"] = args.run_id
        directory.mkdir()
        (directory / "manifest.json").write_text(json.dumps(data, indent=2) + "\n")
    else:
        if args.results is None or not (directory / "manifest.json").is_file():
            parser.error("finish requires --results and an existing started run")
        if (directory / "results.json").exists():
            parser.error("run already finished; use a new run for a recheck")
        data = json.loads(args.results.read_text())
        with (RECORDS / "scenarios.csv").open() as source:
            rows = list(csv.DictReader(source))
        by_id = {row["scenario_id"]: row for row in rows}
        seen: set[str] = set()
        for result in data.get("scenarios", []):
            sid = result.get("scenario_id")
            if sid not in by_id or sid in seen or result.get("status") not in STATUSES:
                parser.error("unknown/duplicate scenario or invalid status")
            seen.add(sid)
            if result["status"] != "not_run" and not result.get("evidence"):
                parser.error("executed or blocked scenario needs evidence")
            evidence = Path(result.get("evidence", "."))
            if evidence.is_absolute() or ".." in evidence.parts:
                parser.error("evidence must be repo-relative")
            if result.get("evidence") and not (ROOT / evidence).is_file():
                parser.error("evidence file does not exist")
            row = by_id[sid]
            row.update(
                status=result["status"], latest_run=args.run_id, evidence=result.get("evidence", "")
            )
            if "issue_numbers" in result:
                row["issue_numbers"] = result["issue_numbers"]
        with (RECORDS / "scenarios.csv").open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        (directory / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    record = {
        "event": args.action,
        "run_id": args.run_id,
        "at": datetime.now(UTC).isoformat(),
        "record": str(directory.relative_to(ROOT)),
    }
    with (RECORDS / "runs.jsonl").open("a") as ledger:
        ledger.write(json.dumps(record) + "\n")
    write_summary()
    print(json.dumps(record))


if __name__ == "__main__":
    main()

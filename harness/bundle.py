"""Finish a run bundle and publish its summary to the research bus.

  python3 bundle.py --run runs/<RUN id>/ --spec E-20260928-06-r2 --status complete \
      --manifest-extra extra.json [--no-upload]

1. Merges `bundle` fields into run_manifest.json: spec id, bus file id and sha256 of the spec,
   dataset manifest sha256, model pins, harness commit, start/end, calls, tokens, dollars
   (from --manifest-extra, a JSON object the caller computed).
2. Rewrites receipts.sha256 over every file in the run directory.
3. Writes runs/<RUN id>/bus_summary.md: envelope (schema_version 1, run_result, executor) plus
   RESULT.md plus the manifest, then `bus.py validate` and `bus.py put <file> runs`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BUS = [str(Path("/usr/bin/python3")), str(Path.home() / "MemoryRSI-Signals/bin/bus.py")]
MIRROR = Path.home() / "MemoryRSI-Signals/bus-mirror/experiments"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec_ref(spec_id: str) -> dict:
    file_id = None
    listing = subprocess.run(BUS + ["ls", "experiments"], capture_output=True, text=True).stdout
    for line in listing.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[3] == f"{spec_id}.md":
            file_id = parts[0]
    local = MIRROR / f"{spec_id}.md"
    return {"artifact_id": spec_id, "file_id": file_id or "unknown",
            "sha256": sha256_file(local) if local.exists() else "not-in-mirror"}


def write_receipts(run_dir: Path) -> None:
    lines = [f"{sha256_file(p)}  {p.relative_to(run_dir).as_posix()}" for p in sorted(run_dir.rglob("*"))
             if p.is_file() and p.name not in ("receipts.sha256", "bus_summary.md")]
    (run_dir / "receipts.sha256").write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--status", required=True, choices=["complete", "partial", "setup_only", "failed"])
    parser.add_argument("--manifest-extra", type=Path, default=None)
    parser.add_argument("--extra-refs", type=Path, default=None, help="JSON list of further input_refs")
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args(argv)

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ref = spec_ref(args.spec)
    manifest_path = args.run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    extra = json.loads(args.manifest_extra.read_text()) if args.manifest_extra else {}
    manifest["bundle"] = {"spec_id": args.spec, "spec_file_id": ref["file_id"], "spec_sha256": ref["sha256"],
                          "run_id": args.run.name, "status": args.status, "finalised_at": created, **extra}
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    write_receipts(args.run)

    input_refs = [ref] + (json.loads(args.extra_refs.read_text()) if args.extra_refs else [])
    refs_yaml = "\n".join(f"  - {{artifact_id: {r['artifact_id']}, file_id: {r.get('file_id', 'local')}, sha256: {r['sha256']}}}"
                          for r in input_refs)
    result = (args.run / "RESULT.md").read_text()
    summary = f"""---
schema_version: 1
artifact_id: RUN-{args.spec}-{stamp}
artifact_type: run_result
producer: executor
run_id: {args.run.name}
created_at: {created}
input_refs:
{refs_yaml}
supersedes: null
idempotency_key: run:{args.spec}:{stamp}
status: {args.status}
---
{result}

## Run manifest

```json
{json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False)}
```
"""
    out = args.run / "bus_summary.md"
    out.write_text(summary)
    upload_name = args.run.parent / f"RUN-{args.spec}-{stamp}.md"
    upload_name.write_text(summary)
    try:
        check = subprocess.run(BUS + ["validate", str(upload_name)], capture_output=True, text=True)
        print("validate:", check.stdout.strip() or check.stderr.strip())
        if check.returncode != 0:
            return 2
        if not args.no_upload:
            put = subprocess.run(BUS + ["put", str(upload_name), "runs"], capture_output=True, text=True)
            print("put:", (put.stdout or put.stderr).strip()[-600:])
            return put.returncode
    finally:
        upload_name.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())

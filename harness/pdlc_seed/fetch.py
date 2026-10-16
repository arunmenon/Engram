"""Fetch the raw PDLC-SEED-ASF slice from apache/opendal with `gh api`.

  python3 -m pdlc_seed.fetch --repo-dir <opendal checkout at the pin> --out <build dir>

For each selected RFC: the RFC document at the pinned commit, its RFC pull
request, its tracking issue with comments, the pull requests and issues that
cross-reference the tracking issue (created on or before the pinned date), and
CI check runs on each pull request's head commit. Every API response is cached
under <build dir>/cache so a re-run makes no new calls. Nothing is edited here;
pseudonymisation and typing happen in pdlc_seed.build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

REPO = "apache/opendal"
PIN_DATE = "2026-06-30T23:59:59Z"
PIN_COMMIT = "5af2bd77c325fa4cb4e0940f31c30705c16382d6"
RFC_DIR = "core/core/src/docs/rfcs"
SELECTED_RFCS = [
    "3898", "3911", "4382", "4638", "5314", "5444", "5479", "5485", "5495", "5556", "5871", "6189",
    "6209", "6213", "6297", "6370", "6678", "6707", "6817", "6828", "7130", "7182", "7519", "7660",
    "7740", "7744",
]
MAX_PRS_PER_RFC = 12
MAX_ISSUES_PER_RFC = 5
MAX_COMMENTS = 8


def gh(path: str, cache: Path, paginate: bool = False):
    key = hashlib.sha256(path.encode()).hexdigest()[:24]
    cached = cache / f"{key}.json"
    if cached.exists():
        return json.loads(cached.read_text())
    args = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        args.insert(2, "--paginate")
        args.insert(3, "--slurp")
    for attempt in range(4):
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode == 0:
            data = json.loads(proc.stdout) if proc.stdout.strip() else None
            if paginate and isinstance(data, list):
                data = [x for page in data for x in (page if isinstance(page, list) else [page])]
            cached.write_text(json.dumps({"path": path, "data": data}))
            return {"path": path, "data": data}
        if "Not Found" in proc.stderr or "HTTP 404" in proc.stderr:
            cached.write_text(json.dumps({"path": path, "data": None, "error": "404"}))
            return {"path": path, "data": None}
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"gh api failed: {path}: {proc.stderr[:300]}")


def before_pin(ts: str | None) -> bool:
    return bool(ts) and ts <= PIN_DATE


def rfc_header(text: str) -> dict:
    def grab(label):
        m = re.search(rf"^- {label}:\s*(.*)$", text, re.MULTILINE)
        return m.group(1).strip() if m else None
    num = lambda s: (re.search(r"#(\d+)", s or "") or [None, None])[1]
    return {"proposal_name": (grab("Proposal Name") or "").strip("`"), "start_date": grab("Start Date"),
            "rfc_pr": num(grab("RFC PR")), "tracking_issue": num(grab("Tracking Issue"))}


def fetch_pr(number: str, cache: Path) -> dict | None:
    pr = gh(f"repos/{REPO}/pulls/{number}", cache)["data"]
    if not pr or not before_pin(pr.get("created_at")):
        return None
    files = gh(f"repos/{REPO}/pulls/{number}/files?per_page=100", cache)["data"] or []
    checks = gh(f"repos/{REPO}/commits/{pr['head']['sha']}/check-runs?per_page=100", cache)["data"] or {}
    return {"pr": pr, "files": [{"filename": f["filename"], "status": f["status"], "additions": f["additions"],
                                 "deletions": f["deletions"]} for f in files],
            "check_runs": [{"id": c["id"], "name": c["name"], "status": c["status"], "conclusion": c["conclusion"],
                            "started_at": c["started_at"], "completed_at": c["completed_at"], "head_sha": c["head_sha"],
                            "app": (c.get("app") or {}).get("slug"), "output_title": (c.get("output") or {}).get("title"),
                            "output_summary": ((c.get("output") or {}).get("summary") or "")[:1500]}
                           for c in (checks.get("check_runs") or [])]}


def fetch_issue(number: str, cache: Path) -> dict | None:
    issue = gh(f"repos/{REPO}/issues/{number}", cache)["data"]
    if not issue or not before_pin(issue.get("created_at")):
        return None
    comments = gh(f"repos/{REPO}/issues/{number}/comments?per_page=100", cache)["data"] or []
    timeline = gh(f"repos/{REPO}/issues/{number}/timeline?per_page=100", cache, paginate=True)["data"] or []
    return {"issue": issue,
            "comments": [{"user": (c.get("user") or {}).get("login"), "created_at": c["created_at"], "body": c.get("body") or ""}
                         for c in comments if before_pin(c["created_at"])][:MAX_COMMENTS],
            "cross_refs": [{"number": str(e["source"]["issue"]["number"]), "is_pr": "pull_request" in e["source"]["issue"],
                            "created_at": e["source"]["issue"]["created_at"], "event_at": e.get("created_at")}
                           for e in timeline if e.get("event") == "cross-referenced" and (e.get("source") or {}).get("issue")
                           and e["source"]["issue"].get("repository_url", "").endswith(REPO)]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    cache = args.out / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    rfc_files = {p.name.split("_")[0]: p for p in (args.repo_dir / RFC_DIR).glob("[0-9]*.md")}
    bundle = {"repo": REPO, "pin_date": PIN_DATE, "pin_commit": PIN_COMMIT, "rfcs": []}
    for rfc_id in SELECTED_RFCS:
        path = rfc_files[rfc_id]
        text = path.read_text(encoding="utf-8")
        head = rfc_header(text)
        entry = {"rfc_id": rfc_id, "path": str(path.relative_to(args.repo_dir)), "text": text, **head,
                 "rfc_pr_data": None, "tracking": None, "prs": [], "issues": []}
        if head["rfc_pr"]:
            entry["rfc_pr_data"] = fetch_pr(head["rfc_pr"], cache)
        if head["tracking_issue"] and head["tracking_issue"] != "0000":
            entry["tracking"] = fetch_issue(head["tracking_issue"], cache)
        refs = (entry["tracking"] or {}).get("cross_refs", [])
        seen = {head["rfc_pr"], head["tracking_issue"]}
        pr_refs = [r for r in refs if r["is_pr"] and before_pin(r["created_at"]) and r["number"] not in seen]
        issue_refs = [r for r in refs if not r["is_pr"] and before_pin(r["created_at"]) and r["number"] not in seen]
        for r in sorted(pr_refs, key=lambda r: r["created_at"])[:MAX_PRS_PER_RFC]:
            pr = fetch_pr(r["number"], cache)
            if pr:
                entry["prs"].append(pr)
        for r in sorted(issue_refs, key=lambda r: r["created_at"])[:MAX_ISSUES_PER_RFC]:
            issue = fetch_issue(r["number"], cache)
            if issue:
                entry["issues"].append(issue)
        bundle["rfcs"].append(entry)
        print(rfc_id, "prs", len(entry["prs"]), "issues", len(entry["issues"]), flush=True)
    (args.out / "raw_bundle.json").write_text(json.dumps(bundle, ensure_ascii=False))


if __name__ == "__main__":
    main()

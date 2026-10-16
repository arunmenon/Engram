"""Type, pseudonymise and secret-scan the raw OpenDAL slice into PDLC-SEED-ASF records.

  python3 -m pdlc_seed.build --build <build dir> --out <build dir>/records.jsonl

Record types (the specs' PDLC ontology): Decision (an RFC design proposal page),
Ticket (tracking issues and bug reports), Requirement (feature-request issues),
PR, Test (CI check runs on a PR head commit: one aggregate CI record per PR plus
each failing job, at most 3 per PR) and DesignElement (the 40 code modules at the
pinned commit touched by the most PRs in the slice, at least 3 each). No Constraint records: the
sources carry no separate constraint documents and none are invented.

Pseudonymisation: GitHub logins (authors and @mentions), e-mail addresses and
Signed-off-by / Co-authored-by trailers are replaced by stable pseudonyms from an
HMAC keyed with <build dir>/pseudonym.key (created once, never frozen).
Secret scan: high-precision token patterns; any record with a hit is dropped.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import hmac
import json
import re
import secrets
import subprocess
from pathlib import Path

PIN_DATE = "2026-06-30T23:59:59Z"
PIN_COMMIT = "5af2bd77c325fa4cb4e0940f31c30705c16382d6"
BASE = "https://github.com/apache/opendal"
PREFIX = "opendal"
BOTS = {"dependabot[bot]", "github-actions[bot]", "github-actions", "dependabot", "codecov[bot]", "asfgit"}
MAX_FAILED_JOBS_PER_PR = 3
MIN_PRS_PER_MODULE = 3
MAX_MODULES = 40
REQUIREMENT_LABELS = {"enhancement", "feature", "feature request", "rfc", "proposal"}

SECRET_PATTERNS = {
    "aws_access_key": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b",
    "github_token": r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    "slack_token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "private_key": r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
    "openai_key": r"\bsk-(proj-)?[A-Za-z0-9_-]{32,}\b",
    "google_api_key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "stripe_key": r"\b(sk|rk)_live_[0-9A-Za-z]{20,}\b",
    "jwt": r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    "azure_conn_string": r"AccountKey=[A-Za-z0-9+/]{60,}={0,2}",
}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MENTION = re.compile(r"(?<![\w/`.])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))\b")
TRAILER = re.compile(r"^(Signed-off-by|Co-authored-by|Co-Authored-By|Reviewed-by):.*$", re.MULTILINE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _dictionary() -> set[str]:
    path = Path("/usr/share/dict/words")
    return {w.strip().lower() for w in path.read_text().split()} if path.exists() else set()


DICTIONARY_WORDS = _dictionary() | {"rust", "java", "python", "node", "github", "opendal", "apache", "admin", "test"}


class Pseudonymiser:
    def __init__(self, key: bytes):
        self.key = key
        self.logins: set[str] = set()
        self.counts = collections.Counter()

    def handle(self, login: str | None) -> str | None:
        if not login:
            return None
        if login in BOTS:
            return login
        self.logins.add(login.lower())
        self.counts["logins"] += 1
        return "contrib-" + hmac.new(self.key, login.lower().encode(), hashlib.sha256).hexdigest()[:8]

    def text(self, body: str | None) -> str:
        if not body:
            return ""
        body = HTML_COMMENT.sub("", body)
        body, n = TRAILER.subn(lambda m: f"{m.group(1)}: [pseudonymised]", body)
        self.counts["trailers"] += n

        def mail(m):
            self.counts["emails"] += 1
            return "user-" + hmac.new(self.key, m.group(0).lower().encode(), hashlib.sha256).hexdigest()[:8] + "@example.invalid"

        body = EMAIL.sub(mail, body)

        def mention(m):
            self.counts["mentions"] += 1
            return "@" + self.handle(m.group(1))

        body = MENTION.sub(mention, body)
        return re.sub(r"\n{3,}", "\n\n", body).strip()


def scrub_logins(text: str, pseudo: Pseudonymiser) -> str:
    """Replace any known login that still appears as a bare word (e.g. in URLs or branch names)."""
    for login in sorted(pseudo.logins, key=len, reverse=True):
        if len(login) < 4 or login in DICTIONARY_WORDS:
            continue
        text = re.sub(rf"(?i)(?<![A-Za-z0-9-]){re.escape(login)}(?![A-Za-z0-9-])", lambda m: pseudo.handle(m.group(0)), text)
    return text


def secret_hits(record: dict) -> list[str]:
    blob = json.dumps(record, ensure_ascii=False)
    return [name for name, pattern in SECRET_PATTERNS.items() if re.search(pattern, blob)]


def refs_in(text: str) -> list[str]:
    nums = set(re.findall(r"(?:apache/opendal)?#(\d{2,5})\b", text or ""))
    nums |= set(re.findall(r"github\.com/apache/opendal/(?:pull|issues)/(\d+)", text or ""))
    return sorted(nums, key=int)


def module_key(path: str) -> str | None:
    """Normalise a changed-file path (old or new repository layout) to a module key."""
    parts = path.split("/")
    if "services" in parts:
        i = parts.index("services")
        if i + 1 < len(parts):
            name = parts[i + 1].removesuffix(".rs")
            if name not in ("mod", "src"):
                return f"service:{name}"
    if parts[:2] == ["core", "layers"] and len(parts) > 2:
        return f"layer:{parts[2]}"
    if "layers" in parts:
        i = parts.index("layers")
        if i + 1 < len(parts) and parts[i + 1] not in ("mod.rs",):
            return f"layer:{parts[i + 1].removesuffix('.rs')}"
    if "src" in parts and parts[0] == "core":
        i = parts.index("src")
        rest = parts[i + 1 : i + 3]
        if rest and rest[0] in ("types", "raw", "blocking", "docs"):
            sub = rest[1].removesuffix(".rs") if len(rest) > 1 and not rest[1].endswith(".md") else None
            return f"core:{rest[0]}" + (f"/{sub}" if sub and sub != "mod" else "")
    if parts[0] == "bindings" and len(parts) > 1:
        return f"binding:{parts[1]}"
    return None


def module_path_at_pin(key: str, tree: set[str]) -> str | None:
    kind, name = key.split(":", 1)
    candidates = {
        "service": [f"core/services/{name}", f"core/core/src/services/{name}"],
        "layer": [f"core/layers/{name}", f"core/core/src/layers/{name}", f"core/core/src/layers/{name}.rs"],
        "core": [f"core/core/src/{name}", f"core/core/src/{name}.rs"],
        "binding": [f"bindings/{name}"],
    }[kind]
    for c in candidates:
        if c in tree:
            return c
    return None


def module_doc(repo: Path, path: str) -> str:
    for candidate in (f"{path}/src/lib.rs", f"{path}/mod.rs", f"{path}/README.md", path if path.endswith(".rs") else None):
        if not candidate:
            continue
        proc = subprocess.run(["git", "-C", str(repo), "show", f"{PIN_COMMIT}:{candidate}"], capture_output=True, text=True)
        if proc.returncode == 0:
            lines = [l[3:].strip() for l in proc.stdout.splitlines() if l.startswith("//!")]
            text = " ".join(lines) if lines else proc.stdout[:800]
            return text[:1200]
    return ""


def pr_record(entry: dict, pseudo: Pseudonymiser, role: str, rfc_id: str) -> dict:
    pr = entry["pr"]
    merged = pr.get("merged_at") if pr.get("merged_at") and pr["merged_at"] <= PIN_DATE else None
    closed = pr.get("closed_at") if pr.get("closed_at") and pr["closed_at"] <= PIN_DATE else None
    state = "merged" if merged else ("closed_unmerged" if closed else "open")
    body = pseudo.text(pr.get("body"))
    return {
        "record_id": f"{PREFIX}:pr:{pr['number']}", "record_type": "PR", "source_kind": role,
        "source_url": f"{BASE}/pull/{pr['number']}", "created_at": pr["created_at"],
        "author": pseudo.handle((pr.get("user") or {}).get("login")), "title": pr["title"], "body": body,
        "fields": {"number": pr["number"], "state_at_pin": state, "merged_at": merged, "closed_at": closed,
                   "branch": pr["head"]["ref"], "base": pr["base"]["ref"], "head_sha": pr["head"]["sha"],
                   "changed_files": [f["filename"] for f in entry["files"]], "changed_files_truncated": len(entry["files"]) >= 100,
                   "additions": sum(f["additions"] for f in entry["files"]), "deletions": sum(f["deletions"] for f in entry["files"]),
                   "labels": [l["name"] for l in pr.get("labels", [])]},
        "mentions": refs_in(pr["title"] + "\n" + (pr.get("body") or "")),
        "slice_rfc": rfc_id,
    }


def issue_record(entry: dict, pseudo: Pseudonymiser, role: str, rfc_id: str) -> dict:
    issue = entry["issue"]
    labels = [l["name"] for l in issue.get("labels", [])]
    closed = issue.get("closed_at") if issue.get("closed_at") and issue["closed_at"] <= PIN_DATE else None
    if role == "tracking_issue":
        rtype = "Ticket"
    elif {l.lower() for l in labels} & REQUIREMENT_LABELS or issue["title"].lower().startswith(("feat", "new feature", "proposal", "rfc")):
        rtype = "Requirement"
    else:
        rtype = "Ticket"
    comments = [{"author": pseudo.handle(c["user"]), "created_at": c["created_at"], "body": pseudo.text(c["body"])} for c in entry["comments"]]
    raw_text = issue["title"] + "\n" + (issue.get("body") or "") + "\n".join(c["body"] for c in entry["comments"])
    return {
        "record_id": f"{PREFIX}:issue:{issue['number']}", "record_type": rtype, "source_kind": role,
        "source_url": f"{BASE}/issues/{issue['number']}", "created_at": issue["created_at"],
        "author": pseudo.handle((issue.get("user") or {}).get("login")), "title": issue["title"], "body": pseudo.text(issue.get("body")),
        "fields": {"number": issue["number"], "state_at_pin": "closed" if closed else "open", "closed_at": closed,
                   "labels": labels, "comments": comments},
        "mentions": refs_in(raw_text), "slice_rfc": rfc_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    key_path = args.build / "pseudonym.key"
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
    pseudo = Pseudonymiser(key_path.read_bytes())
    bundle = json.loads((args.build / "raw_bundle.json").read_text())
    repo = args.build / "repo"
    tree = set(subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "-d", "--name-only", PIN_COMMIT], capture_output=True, text=True).stdout.split())
    tree |= set(subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", PIN_COMMIT], capture_output=True, text=True).stdout.split())

    records: dict[str, dict] = {}
    pr_entries: dict[str, tuple[dict, str]] = {}

    def add(rec: dict) -> None:
        if rec["record_id"] not in records:
            records[rec["record_id"]] = rec

    for rfc in bundle["rfcs"]:
        rid = rfc["rfc_id"]
        add({"record_id": f"{PREFIX}:rfc:{rid}", "record_type": "Decision", "source_kind": "design_proposal",
             "source_url": f"{BASE}/blob/{PIN_COMMIT}/{rfc['path']}", "created_at": (rfc["start_date"] or "") + "T00:00:00Z",
             "author": None, "title": f"RFC-{rid}: {rfc['proposal_name']}", "body": pseudo.text(rfc["text"]),
             "fields": {"rfc_number": rid, "proposal_name": rfc["proposal_name"], "start_date": rfc["start_date"],
                        "rfc_pr": rfc["rfc_pr"], "tracking_issue": rfc["tracking_issue"], "path": rfc["path"]},
             "mentions": refs_in(rfc["text"]), "slice_rfc": rid})
        if rfc["rfc_pr_data"]:
            add(pr_record(rfc["rfc_pr_data"], pseudo, "rfc_pr", rid))
            pr_entries[str(rfc["rfc_pr_data"]["pr"]["number"])] = (rfc["rfc_pr_data"], rid)
        if rfc["tracking"]:
            add(issue_record(rfc["tracking"], pseudo, "tracking_issue", rid))
        for entry in rfc["prs"]:
            add(pr_record(entry, pseudo, "pull_request", rid))
            pr_entries.setdefault(str(entry["pr"]["number"]), (entry, rid))
        for entry in rfc["issues"]:
            add(issue_record(entry, pseudo, "issue", rid))

    # Tests: CI on each PR head commit.
    for number, (entry, rid) in sorted(pr_entries.items(), key=lambda kv: int(kv[0])):
        runs = [c for c in entry["check_runs"] if c["started_at"] and c["started_at"] <= PIN_DATE]
        if not runs:
            continue
        concl = collections.Counter(c["conclusion"] for c in runs)
        failed = [c for c in runs if c["conclusion"] == "failure"]
        head = entry["pr"]["head"]["sha"]
        add({"record_id": f"{PREFIX}:ci:{number}:{head[:10]}", "record_type": "Test", "source_kind": "ci_run",
             "source_url": f"{BASE}/pull/{number}/checks", "created_at": min(c["started_at"] for c in runs), "author": "github-actions",
             "title": f"CI on PR #{number} head {head[:7]}: {concl.get('success', 0)} passed, {concl.get('failure', 0)} failed, {concl.get('skipped', 0)} skipped",
             "body": "Failed jobs: " + (", ".join(sorted(c["name"] for c in failed)) or "none"),
             "fields": {"pr": int(number), "head_sha": head, "conclusions": dict(concl), "jobs": sorted({c["name"] for c in runs})[:200]},
             "mentions": [number], "slice_rfc": rid})
        for c in sorted(failed, key=lambda c: c["name"])[:MAX_FAILED_JOBS_PER_PR]:
            add({"record_id": f"{PREFIX}:check:{c['id']}", "record_type": "Test", "source_kind": "ci_job",
                 "source_url": f"{BASE}/pull/{number}/checks", "created_at": c["started_at"], "author": c.get("app") or "github-actions",
                 "title": f"CI job '{c['name']}' {c['conclusion']} on PR #{number} head {head[:7]}",
                 "body": pseudo.text("\n".join(x for x in (c.get("output_title"), c.get("output_summary")) if x)),
                 "fields": {"pr": int(number), "head_sha": head, "job": c["name"], "conclusion": c["conclusion"],
                            "completed_at": c["completed_at"]},
                 "mentions": [number], "slice_rfc": rid})

    # DesignElements: modules at the pin touched by >= MIN_PRS_PER_MODULE PRs in the slice.
    touches: dict[str, set[str]] = collections.defaultdict(set)
    for number, (entry, _) in pr_entries.items():
        for f in entry["files"]:
            key = module_key(f["filename"])
            if key:
                touches[key].add(number)
    kept_modules = 0
    for key, prs in sorted(touches.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(prs) < MIN_PRS_PER_MODULE or kept_modules >= MAX_MODULES:
            continue
        path = module_path_at_pin(key, tree)
        if not path:
            continue
        files = sorted(p for p in tree if p.startswith(path + "/") and "." in p.rsplit("/", 1)[-1])[:60]
        add({"record_id": f"{PREFIX}:module:{key}", "record_type": "DesignElement", "source_kind": "code_module",
             "source_url": f"{BASE}/tree/{PIN_COMMIT}/{path}", "created_at": None, "author": None,
             "title": f"Module {key} ({path})", "body": pseudo.text(module_doc(repo, path)),
             "fields": {"module_key": key, "path_at_pin": path, "files_at_pin": files, "touched_by_prs": sorted(prs, key=int)},
             "mentions": [], "slice_rfc": None})
        kept_modules += 1

    # Second pass: scrub any known login still present as a bare word (branch names, URLs, text).
    dropped = []
    out_rows = []
    for rec in records.values():
        blob = json.dumps(rec, ensure_ascii=False)
        blob = scrub_logins(blob, pseudo)
        rec = json.loads(blob)
        hits = secret_hits(rec)
        if hits:
            dropped.append({"record_id": rec["record_id"], "patterns": hits})
            continue
        out_rows.append(rec)
    out_rows.sort(key=lambda r: (r["record_type"], r["record_id"]))
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    report = {"records": len(out_rows), "by_type": dict(collections.Counter(r["record_type"] for r in out_rows)),
              "secret_scan": {"patterns": sorted(SECRET_PATTERNS), "dropped": dropped},
              "pseudonymisation": {"distinct_logins": len(pseudo.logins), **dict(pseudo.counts)}}
    (args.out.parent / "build_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()

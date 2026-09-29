"""Fetch public issue threads and pull-request discussions for MEMDEC-ASF-6200.

  python -m memdec_build.fetch --projects memdec_build/projects.yaml --out <build dir> --per-repo 80

One session = one issue or pull request thread (opening post plus its comments),
created on or before the cutoff. Contributor handles and emails are replaced by
stable pseudonyms (keyed HMAC; the key stays in the build directory and is never
frozen). Bot accounts are dropped. Any thread with a secret-scan hit is dropped
and counted. Output: sessions.jsonl in the shape gate_eval.locomo_extract uses
(session_id, conversation_id, session_time, turns[{speaker, text, dia_id}]) plus
fetch_manifest.json.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import secrets
import subprocess
import time
from pathlib import Path

CUTOFF = "2026-06-30T23:59:59Z"
MAX_TURNS = 40
MAX_TURN_CHARS = 3000
BOT_LOGIN = re.compile(r"(\[bot\]$|^github-actions$|^codecov|^dependabot|^sonarcloud|^mergify|^asfgit$|^boring-cyborg|^stale$|^allcontributors)", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MENTION = re.compile(r"(?<![\w/])@([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))")
TRAILER = re.compile(r"^(Signed-off-by|Co-authored-by|Reviewed-by|Reported-by|Tested-by):.*$", re.I | re.M)
SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
    "slack_token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "private_key": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "openai_key": re.compile(r"\bsk-(proj-)?[A-Za-z0-9_-]{32,}\b"),
    "stripe_key": re.compile(r"\b(sk|rk)_live_[0-9a-zA-Z]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "password_assignment": re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?(?!\*+|<|\$\{|xxx|your|changeme|password|secret|example|test|123456|null|none)[A-Za-z0-9!#%^&*+/=_-]{12,}"),
}


def gh(path: str, retries: int = 5):
    for attempt in range(retries):
        proc = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        if "rate limit" in proc.stderr.lower():
            time.sleep(60)
        else:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"gh api failed: {path}: {proc.stderr[:300]}")


class Pseudonymiser:
    def __init__(self, key: bytes):
        self.key = key
        self.handles: set[str] = set()
        self.emails = 0

    def name(self, login: str) -> str:
        self.handles.add(login.lower())
        digest = hmac.new(self.key, login.lower().encode(), hashlib.sha256).hexdigest()[:8]
        return f"contributor-{digest}"

    def text(self, body: str) -> str:
        body = TRAILER.sub("[trailer removed]", body or "")

        def email_sub(m: re.Match) -> str:
            self.emails += 1
            digest = hmac.new(self.key, m.group(0).lower().encode(), hashlib.sha256).hexdigest()[:8]
            return f"email-{digest}@redacted.invalid"

        body = EMAIL.sub(email_sub, body)
        return MENTION.sub(lambda m: "@" + self.name(m.group(1)), body)


def secret_hits(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def fetch_repo(repo: str, per_repo: int, pseudo: Pseudonymiser) -> tuple[list[dict], dict]:
    threads, page = [], 1
    while len(threads) < per_repo * 2 and page <= 6:
        batch = gh(f"repos/{repo}/issues?state=all&sort=comments&direction=desc&per_page=100&page={page}")
        if not batch:
            break
        for t in batch:
            if t["created_at"] <= CUTOFF and t.get("comments", 0) >= 3 and not BOT_LOGIN.search(t["user"]["login"]):
                threads.append(t)
        page += 1
    threads = threads[:per_repo]
    sessions, stats = [], {"threads_listed": len(threads), "dropped_secret": 0, "secret_kinds": {}, "dropped_short": 0}
    for t in threads:
        comments = []
        cpage = 1
        while len(comments) < MAX_TURNS:
            batch = gh(f"repos/{repo}/issues/{t['number']}/comments?per_page=100&page={cpage}")
            comments.extend(c for c in batch if c["created_at"] <= CUTOFF)
            if len(batch) < 100:
                break
            cpage += 1
        raw_turns = [(t["user"]["login"], f"{t['title']}\n\n{t.get('body') or ''}", t["created_at"])]
        raw_turns += [(c["user"]["login"], c.get("body") or "", c["created_at"]) for c in comments
                      if not BOT_LOGIN.search(c["user"]["login"])]
        raw_turns = [r for r in raw_turns if r[1].strip()][:MAX_TURNS]
        if len(raw_turns) < 3:
            stats["dropped_short"] += 1
            continue
        joined = "\n".join(r[1] for r in raw_turns)
        hits = secret_hits(joined)
        if hits:
            stats["dropped_secret"] += 1
            for h in hits:
                stats["secret_kinds"][h] = stats["secret_kinds"].get(h, 0) + 1
            continue
        kind = "pr" if "pull_request" in t else "issue"
        session_id = f"{repo}#{kind}-{t['number']}"
        turns = []
        for i, (login, body, _) in enumerate(raw_turns):
            text = pseudo.text(body)
            if len(text) > MAX_TURN_CHARS:
                text = text[:MAX_TURN_CHARS] + " [truncated]"
            turns.append({"speaker": pseudo.name(login), "text": text, "dia_id": f"{session_id}:{i}"})
        sessions.append({"session_id": session_id, "conversation_id": repo, "repository_id": repo, "kind": kind,
                         "number": t["number"], "url": t["html_url"], "created_at": t["created_at"],
                         "session_time": None, "turns": turns})
    return sessions, stats


def load_projects(path: Path) -> list[str]:
    repos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-\s*repo:\s*(\S+)", line)
        if m:
            repos.append(m.group(1))
    return repos


def main() -> None:
    parser = argparse.ArgumentParser(prog="memdec_build.fetch")
    parser.add_argument("--projects", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--per-repo", type=int, default=80)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    key_path = args.out / "pseudonym.key"
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
    pseudo = Pseudonymiser(key_path.read_bytes())
    done_path = args.out / "fetched_repos.txt"
    done = set(done_path.read_text().split()) if done_path.exists() else set()
    stats_path = args.out / "fetch_stats.jsonl"
    for repo in load_projects(args.projects):
        if repo in done:
            continue
        sessions, stats = fetch_repo(repo, args.per_repo, pseudo)
        with open(args.out / "sessions.jsonl", "a", encoding="utf-8") as fh:
            for s in sessions:
                fh.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")
        with open(stats_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"repo": repo, "sessions": len(sessions), **stats, "emails_pseudonymised_cumulative": pseudo.emails}) + "\n")
        with open(done_path, "a") as fh:
            fh.write(repo + "\n")
        print(repo, len(sessions), stats, flush=True)
    rows = [json.loads(l) for l in stats_path.read_text().splitlines() if l.strip()]
    manifest = {"cutoff": CUTOFF, "max_turns": MAX_TURNS, "max_turn_chars": MAX_TURN_CHARS,
                "selection": "issues endpoint (issues and pull requests), sorted by comment count descending, created on or before cutoff, at least 3 comments, bot authors excluded; first --per-repo threads; comments on or before cutoff; bot comments dropped; threads with fewer than 3 non-empty turns dropped",
                "pseudonymisation": "GitHub logins and @mentions -> contributor-<hmac8>; emails -> email-<hmac8>@redacted.invalid; Signed-off-by/Co-authored-by style trailers removed; HMAC key kept outside the frozen dataset",
                "secret_scan": sorted(SECRET_PATTERNS), "per_repo": rows,
                "sessions_total": sum(r["sessions"] for r in rows), "dropped_secret_total": sum(r["dropped_secret"] for r in rows),
                "distinct_handles_pseudonymised": len(pseudo.handles)}
    (args.out / "fetch_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

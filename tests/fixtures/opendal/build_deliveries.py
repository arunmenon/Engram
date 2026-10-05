"""Rebuild GitHub webhook deliveries for Apache OpenDAL from its git history.

The PDLC evaluation set in this directory is about real data: Apache
OpenDAL (https://github.com/apache/opendal, Apache-2.0), a proxy until our
own GitHub and Jira are wired. GitHub's API was not reachable from the
session that built it, so the deliveries are rebuilt from git, in the shape
GitHub sends them:

- ``pull_request`` (``closed``, merged) for every first-parent commit on
  ``main`` since ``v0.58.0`` whose subject ends in ``(#N)`` (a squash merge):
  number and title from the subject, the commit body as the PR body (the
  PR description itself is on GitHub only), the commit as the merge commit,
  the commit time as ``merged_at``;
- ``release`` (``published``) for each release whose notes in
  ``CHANGELOG.md`` list its PRs (v0.58.1 to v0.59.1; later entries only link
  to GitHub), with those notes as the body and the tag's date.

The output, ``deliveries.json``, is what the test sends through the signed
webhook route, so the real GitHub adapter translates it.

Usage (from a clone of apache/opendal):
    python tests/fixtures/opendal/build_deliveries.py /path/to/opendal
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "apache/opendal"
SINCE = "v0.58.0"
RELEASES = ("v0.58.1", "v0.58.2", "v0.59.0", "v0.59.1")
SUBJECT = re.compile(r"^(?P<title>.*) \(#(?P<number>\d+)\)$")
OUT = Path(__file__).with_name("deliveries.json")


def git(clone: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(clone), *args], check=True, capture_output=True, text=True
    ).stdout


def pull_requests(clone: Path) -> list[dict]:
    log = git(
        clone,
        "log",
        "--first-parent",
        "--reverse",
        "--format=%H%x1f%cI%x1f%B%x1e",
        f"{SINCE}..HEAD",
    )
    deliveries = []
    for record in filter(None, (r.strip("\n") for r in log.split("\x1e"))):
        sha, merged_at, message = record.split("\x1f")
        subject, _, body = message.strip().partition("\n")
        match = SUBJECT.match(subject.strip())
        if match is None:
            continue
        number = int(match["number"])
        deliveries.append(
            {
                "event": "pull_request",
                "delivery": f"opendal-pr-{number}",
                "body": {
                    "action": "closed",
                    "number": number,
                    "pull_request": {
                        "number": number,
                        "title": match["title"],
                        "body": body.strip(),
                        "merged": True,
                        "merge_commit_sha": sha,
                        "merged_at": merged_at,
                        "closed_at": merged_at,
                    },
                    "repository": {"full_name": REPO, "name": "opendal"},
                },
            }
        )
    return deliveries


def release_notes(changelog: str, version: str) -> str:
    match = re.search(
        rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise SystemExit(f"{version} has no notes in CHANGELOG.md")
    return match.group(1).strip()


def releases(clone: Path) -> list[dict]:
    changelog = git(clone, "show", "HEAD:CHANGELOG.md")
    deliveries = []
    for version in RELEASES:
        published_at = git(clone, "log", "-1", "--format=%cI", version).strip()
        deliveries.append(
            {
                "event": "release",
                "delivery": f"opendal-release-{version}",
                "body": {
                    "action": "published",
                    "release": {
                        "tag_name": version,
                        "body": release_notes(changelog, version),
                        "published_at": published_at,
                    },
                    "repository": {"full_name": REPO, "name": "opendal"},
                },
            }
        )
    return deliveries


def main(clone: Path) -> None:
    deliveries = pull_requests(clone) + releases(clone)
    # In time order, as GitHub would have sent them
    deliveries.sort(
        key=lambda d: (
            d["body"].get("pull_request", d["body"].get("release", {})).get("merged_at")
            or d["body"]["release"]["published_at"]
        )
    )
    head = git(clone, "rev-parse", "HEAD").strip()
    OUT.write_text(
        json.dumps({"source": f"{REPO}@{head}", "since": SINCE, "deliveries": deliveries}, indent=1)
        + "\n"
    )
    print(f"{len(deliveries)} deliveries -> {OUT}")  # noqa: T201 - script output


if __name__ == "__main__":
    main(Path(sys.argv[1]))

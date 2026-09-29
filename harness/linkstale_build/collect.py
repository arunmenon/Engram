"""Collect the Engram repository history that LINK-STALE-200 is mined from.

  python3 -m linkstale_build.collect --repo ~/projects/Engram --commit 7748337 --out <build dir>

Writes, under <build dir>:
  snapshot/            the repository tree at the pinned commit (git archive): the "current state"
  versions/<slug>/     every committed version of each tracked document, as NN_<commit>_<date>.md
  units.json           mining units: a thread topic, its document versions and related files
  corpus.jsonl         the memory corpus neighbours are retrieved from: one paragraph chunk per
                       distinct paragraph across all document versions, plus commit subjects
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

DOC_GLOBS = ("docs/adr/", "docs/handoffs/", "docs/constitution/", "docs/review/", "docs/replication/",
             "docs/research/", "docs/architecture-review.md", "docs/platform-readiness-gap-analysis.md",
             "docs/retrieval-improvement-plan.md", "CLAUDE.md", "README.md")

# Mining units: each is one decision-thread family. Related files give the miner the
# later documents and code that may supersede or invalidate what the unit's documents say.
UNITS = [
    {"unit": "adr-0001", "docs": ["docs/adr/0001-traceability-first-context-graph.md"]},
    {"unit": "adr-0002", "docs": ["docs/adr/0002-service-stack-python-fastapi.md"]},
    {"unit": "adr-0003", "docs": ["docs/adr/0003-dual-store-postgres-neo4j.md", "docs/research/redis-event-store-feasibility.md"]},
    {"unit": "adr-0004", "docs": ["docs/adr/0004-event-ledger-and-idempotent-ingestion.md"]},
    {"unit": "adr-0005", "docs": ["docs/adr/0005-graph-projection-and-replay-worker.md"]},
    {"unit": "adr-0006", "docs": ["docs/adr/0006-context-query-and-lineage-api.md"]},
    {"unit": "adr-0007", "docs": ["docs/adr/0007-memory-tier-architecture.md"]},
    {"unit": "adr-0008", "docs": ["docs/adr/0008-memory-consolidation-and-decay.md"]},
    {"unit": "adr-0009", "docs": ["docs/adr/0009-multi-graph-schema-for-memory.md"]},
    {"unit": "adr-0010", "docs": ["docs/adr/0010-redis-event-store.md", "docs/research/redis-architecture-design.md"]},
    {"unit": "adr-0011", "docs": ["docs/adr/0011-ontological-foundation.md"]},
    {"unit": "adr-0012", "docs": ["docs/adr/0012-user-personalization-ontology.md", "docs/research/user-personalization-discovery.md"]},
    {"unit": "adr-0013", "docs": ["docs/adr/0013-knowledge-extraction-pipeline.md", "docs/research/extraction-production-pipelines.md"]},
    {"unit": "adr-0014", "docs": ["docs/adr/0014-archival-lifecycle-management.md"]},
    {"unit": "adr-0015", "docs": ["docs/adr/0015-sdk-and-integration-architecture.md"]},
    {"unit": "adr-0016-0017", "docs": ["docs/adr/0016-security-architecture.md", "docs/adr/0017-observability-architecture.md"]},
    {"unit": "handoffs-early", "docs": ["docs/handoffs/phase-0-redis.md", "docs/handoffs/phase-0-neo4j.md", "docs/handoffs/phase-1-complete.md", "docs/handoffs/phase-2-complete.md"]},
    {"unit": "handoffs-late", "docs": ["docs/handoffs/phase-3-complete.md", "docs/handoffs/phase-4-complete.md", "docs/handoffs/phase-5-complete.md", "docs/handoffs/frontend-backend-integration.md"]},
    {"unit": "constitution", "docs": ["docs/constitution/phase-plan.md", "docs/constitution/coding-standards.md", "docs/constitution/testing-strategy.md"]},
    {"unit": "coherence-reviews", "docs": ["docs/review/coherence-data-store.md", "docs/review/coherence-graph-schema.md", "docs/review/coherence-pipeline.md", "docs/review/coherence-ontology.md"]},
    {"unit": "staleness-review", "docs": ["docs/replication/2026-09-25/engram-staleness-review-2026-09-25.md", "docs/platform-readiness-gap-analysis.md"]},
    {"unit": "architecture-review", "docs": ["docs/architecture-review.md", "docs/retrieval-improvement-plan.md"]},
    {"unit": "project-guide", "docs": ["CLAUDE.md", "README.md"]},
    {"unit": "research-memory", "docs": ["docs/research/consolidated-research.md", "docs/research/cluster2-memory-architectures.md", "docs/research/cluster3-neuroscience-memory.md"]},
    {"unit": "research-extraction", "docs": ["docs/research/extraction-landscape.md", "docs/research/extraction-llm-techniques.md", "docs/research/user-behavior-graph-architecture.md"]},
]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def slug(path: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")


def versions_of(repo: Path, commit: str, path: str) -> list[dict]:
    log = git(repo, "log", "--follow", "--format=%H %ad", "--date=short", commit, "--", path).split("\n")
    out = []
    for line in reversed([l for l in log if l.strip()]):
        sha, date = line.split()
        names = git(repo, "show", "--name-only", "--format=", sha).split("\n")
        # --follow may report a renamed path; pick the name that exists at that commit
        candidates = [path] + [n for n in names if n.endswith(Path(path).name) or Path(n).stem[:4] == Path(path).stem[:4]]
        text = None
        for name in candidates:
            try:
                text = git(repo, "show", f"{sha}:{name}")
                path_at = name
                break
            except subprocess.CalledProcessError:
                continue
        if text is None:
            continue
        if out and out[-1]["sha256"] == hashlib.sha256(text.encode()).hexdigest():
            continue
        out.append({"commit": sha, "date": date, "path_at_commit": path_at, "text": text,
                    "sha256": hashlib.sha256(text.encode()).hexdigest()})
    return out


def paragraphs(text: str) -> list[str]:
    chunks, in_code = [], False
    for block in re.split(r"\n\s*\n", text):
        if block.strip().startswith("```"):
            in_code = not in_code if block.count("```") % 2 == 1 else in_code
            continue
        if in_code:
            continue
        clean = " ".join(block.split())
        if len(clean.split()) < 8 or clean.startswith("|---") or re.fullmatch(r"[#*\-| ]+", clean):
            continue
        words = clean.split()
        for i in range(0, len(words), 80):
            chunks.append(" ".join(words[i : i + 80]))
    return chunks


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    commit = git(a.repo, "rev-parse", a.commit).strip()
    a.out.mkdir(parents=True, exist_ok=True)
    snap = a.out / "snapshot"
    if not snap.exists():
        data = subprocess.run(["git", "-C", str(a.repo), "archive", commit], check=True, capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(snap, members=[m for m in tf.getmembers() if not (m.issym() or m.islnk())], filter="data")
    tracked = [f for f in git(a.repo, "ls-tree", "-r", "--name-only", commit).split("\n")
               if f.endswith(".md") and not f.endswith("llm-extraction-techniques.md") and any(f == g or f.startswith(g) for g in DOC_GLOBS)]
    corpus, seen = [], set()
    version_index = {}
    for path in tracked:
        vs = versions_of(a.repo, commit, path)
        version_index[path] = [{k: v[k] for k in ("commit", "date", "path_at_commit", "sha256")} for v in vs]
        vdir = a.out / "versions" / slug(path)
        vdir.mkdir(parents=True, exist_ok=True)
        for n, v in enumerate(vs, 1):
            (vdir / f"{n:02d}_{v['commit'][:7]}_{v['date']}.md").write_text(v["text"], encoding="utf-8")
            for chunk in paragraphs(v["text"]):
                key = hashlib.sha256(chunk.lower().encode()).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                corpus.append({"chunk_id": f"doc:{key[:16]}", "text": chunk, "source": f"{path}@{v['commit'][:7]}",
                               "recorded_at": v["date"], "originating_event_type": "import"})
    for line in git(a.repo, "log", "--format=%H\t%ad\t%s%n%b%x00", "--date=short", commit).split("\x00"):
        line = line.strip()
        if not line:
            continue
        sha, date, msg = line.split("\t", 2)
        msg = " ".join(msg.split())
        if len(msg.split()) < 5:
            continue
        corpus.append({"chunk_id": f"commit:{sha[:10]}", "text": " ".join(msg.split()[:80]), "source": f"commit {sha[:7]}",
                       "recorded_at": date, "originating_event_type": "user.message"})
    with open(a.out / "corpus.jsonl", "w", encoding="utf-8") as fh:
        for row in corpus:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    units = []
    for u in UNITS:
        units.append({**u, "versions": {d: version_index.get(d, []) for d in u["docs"]}, "slugs": {d: slug(d) for d in u["docs"]}})
    (a.out / "units.json").write_text(json.dumps({"repo": "https://github.com/arunmenon/Engram", "commit": commit, "units": units,
                                                   "version_index": version_index}, indent=1), encoding="utf-8")
    print(f"commit {commit}; {len(tracked)} docs; {sum(len(v) for v in version_index.values())} versions; corpus {len(corpus)}")


if __name__ == "__main__":
    main()

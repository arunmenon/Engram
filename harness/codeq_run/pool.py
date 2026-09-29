"""E-20260928-19-r2 frozen candidate pool P (one per question).

  python -m codeq_run.pool --repo <opendal checkout> --dataset <frozen CODEQ-ASF-80> \
      --secret-scan <gitleaks json> --out <run dir>

Per question: ripgrep matches for the blind keywords (fixed string, case-insensitive),
40-line windows around each match (a match already inside a window of the same file
opens no new window), plus one-hop definition windows found with universal-ctags for
identifiers seen in matched windows, deduplicated, ordered by IDF score, capped at
200 windows. Secret-flagged files are excluded from P, and questions whose gold spans
sit in a flagged file are excluded from the run (spec execution packet (3)).

IDF follows genigrep's recall (idf = ln(1 + N / (1 + df)), N = files searched);
a window's lexical score is the sum of IDF over the distinct keywords it contains.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from gate_eval.common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl

WINDOW_LINES = 40
HALF_WINDOW = WINDOW_LINES // 2
POOL_CAP = 200
DEFINITION_SEED_WINDOWS = 40      # matched windows whose identifiers are followed one hop
IDENTIFIERS_PER_WINDOW = 4        # rarest identifiers per seed window that have a ctags definition
EXCLUDE_GLOBS = [
    "!**/node_modules/**", "!**/dist/**", "!**/build/**", "!**/target/**", "!**/vendor/**", "!**/.git/**",
    "!*.lock", "!**/package-lock.json", "!**/pnpm-lock.yaml", "!**/yarn.lock", "!*.min.js", "!*.min.css",
    "!*.map", "!*.snap", "!**/*.gen.*", "!**/*.generated.*", "!**/gen/**", "!**/*_pb.*",
    "!*.{svg,png,jpg,jpeg,gif,ico,webp,woff,woff2,ttf,otf,eot,wasm,pdf,zip,gz,tgz,mp4,mp3,mov}",
]
IDENTIFIER = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{5,}\b")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def idf_of(document_frequency: int, total_files: int) -> float:
    return math.log(1 + total_files / (1 + document_frequency))


def rg_files(repo: Path, flagged: set[str]) -> list[str]:
    args = ["rg", "--files", "--hidden"] + [a for g in EXCLUDE_GLOBS for a in ("-g", g)]
    out = subprocess.run(args, cwd=repo, capture_output=True, text=True, check=True).stdout
    return sorted(p for p in out.splitlines() if p and p not in flagged)


def rg_keyword(repo: Path, keyword: str, flagged: set[str]) -> dict[str, list[int]]:
    args = ["rg", "-n", "-i", "-F", "--no-heading", "--hidden", "-e", keyword] + \
           [a for g in EXCLUDE_GLOBS for a in ("-g", g)]
    proc = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    hits: dict[str, list[int]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3 or not parts[1].isdigit() or parts[0] in flagged:
            continue
        hits[parts[0]].append(int(parts[1]))
    return hits


def ctags_definitions(repo: Path, files: list[str]) -> dict[str, list[tuple[str, int]]]:
    """name -> [(path, line)] from universal-ctags over the searched files."""
    proc = subprocess.run(["/opt/homebrew/bin/ctags", "--output-format=json", "--fields=+n", "-L", "-", "-f", "-"],
                          cwd=repo, input="\n".join(files), capture_output=True, text=True)
    definitions: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        try:
            tag = json.loads(line)
        except json.JSONDecodeError:
            continue
        if tag.get("_type") == "tag" and "line" in tag:
            definitions[tag["name"]].append((tag["path"], int(tag["line"])))
    return definitions


class FileCache:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self._lines: dict[str, list[str]] = {}

    def lines(self, path: str) -> list[str]:
        if path not in self._lines:
            try:
                self._lines[path] = (self.repo / path).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                self._lines[path] = []
        return self._lines[path]


def window_text(cache: FileCache, path: str, start: int, end: int) -> str:
    lines = cache.lines(path)[start - 1:end]
    return "\n".join(EMAIL.sub("<email>", line) for line in lines)


def build_pool(question: dict, repo: Path, files: list[str], flagged: set[str], cache: FileCache,
               definitions: dict[str, list[tuple[str, int]]]) -> tuple[list[dict], dict]:
    keywords = question["keywords"]
    total_files = len(files)
    hits_by_keyword = {kw: rg_keyword(repo, kw, flagged) for kw in keywords}
    idf = {kw: idf_of(len(h), total_files) for kw, h in hits_by_keyword.items()}
    lowered_keywords = [(kw, kw.lower()) for kw in keywords]

    def lexical_score(text: str) -> tuple[float, list[str]]:
        low = text.lower()
        present = [kw for kw, lk in lowered_keywords if lk in low]
        return sum(idf[kw] for kw in present), present

    file_hits: dict[str, set[int]] = defaultdict(set)
    for kw, per_file in hits_by_keyword.items():
        for path, lines in per_file.items():
            file_hits[path].update(lines)

    windows: dict[tuple[str, int], dict] = {}
    for path, lines in file_hits.items():
        n_lines = len(cache.lines(path))
        covered: list[tuple[int, int]] = []
        for hit in sorted(lines):
            if any(a <= hit <= b for a, b in covered):
                continue
            start = max(1, hit - HALF_WINDOW)
            end = min(n_lines, start + WINDOW_LINES - 1)
            covered.append((start, end))
            windows[(path, start)] = {"path": path, "start": start, "end": end, "origin": "keyword_match"}

    def score_windows(ws):
        for w in ws:
            text = window_text(cache, w["path"], w["start"], w["end"])
            score, present = lexical_score(text)
            w.update({"text": text, "lex": score, "keywords_present": present})

    score_windows(windows.values())
    seeds = sorted(windows.values(), key=lambda w: (-w["lex"], w["path"], w["start"]))[:DEFINITION_SEED_WINDOWS]
    added_definitions = 0
    for seed in seeds:
        seen_names = sorted(set(IDENTIFIER.findall(seed["text"])),
                            key=lambda name: (len(definitions.get(name, [])) or 10**9, name))
        taken = 0
        for name in seen_names:
            locations = definitions.get(name)
            if not locations or len(locations) > 3 or taken >= IDENTIFIERS_PER_WINDOW:
                continue
            path, line = locations[0]
            if path in flagged:
                continue
            if any(w["path"] == path and w["start"] <= line <= w["end"] for w in windows.values()):
                taken += 1
                continue
            n_lines = len(cache.lines(path))
            start = max(1, line - 5)
            end = min(n_lines, start + WINDOW_LINES - 1)
            if (path, start) not in windows:
                windows[(path, start)] = {"path": path, "start": start, "end": end, "origin": f"ctags_definition:{name}"}
                added_definitions += 1
            taken += 1
    score_windows([w for w in windows.values() if "text" not in w])

    ordered = sorted(windows.values(), key=lambda w: (-w["lex"], w["path"], w["start"]))[:POOL_CAP]
    pool = []
    for rank, w in enumerate(ordered):
        pool.append({"question_id": question["question_id"], "window_id": f"w{rank:03d}", "rank_idf": rank,
                     "path": w["path"], "start": w["start"], "end": w["end"], "origin": w["origin"],
                     "lex": round(w["lex"], 6), "keywords_present": w["keywords_present"],
                     "hit_lines": sorted(h for h in file_hits.get(w["path"], ()) if w["start"] <= h <= w["end"]),
                     "text": w["text"]})
    stats = {"question_id": question["question_id"], "windows_before_cap": len(windows), "pool_size": len(pool),
             "definition_windows_added": added_definitions, "idf": idf,
             "files_with_hits": len(file_hits)}
    return pool, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeq_run.pool")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--secret-scan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.repo, text=True).strip()
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    if commit != manifest["commit"]:
        print(f"REFUSED: repository at {commit}, dataset pinned {manifest['commit']}", file=sys.stderr)
        return 2
    findings = json.loads(args.secret_scan.read_text())
    flagged = {f["File"] for f in findings}
    all_tracked = subprocess.check_output(["git", "ls-files"], cwd=args.repo, text=True).splitlines()
    questions = read_jsonl(args.dataset / "questions.jsonl")
    gold = {r["question_id"]: r for r in read_jsonl(args.dataset / "gold.jsonl")}
    excluded_questions = sorted(q for q, r in gold.items() if any(s["path"] in flagged for s in r["spans"]))

    files = rg_files(args.repo, flagged)
    cache = FileCache(args.repo)
    definitions = ctags_definitions(args.repo, files)
    pool_rows, stats_rows = [], []
    for question in questions:
        if question["question_id"] in excluded_questions:
            continue
        pool, stats = build_pool(question, args.repo, files, flagged, cache, definitions)
        pool_rows.extend(pool)
        stats_rows.append(stats)
    args.out.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out / "pool.jsonl", pool_rows)
    secret_scan = {"tool": "gitleaks 8.30.1 (dir mode, redacted)", "files_tracked": len(all_tracked),
                   "files_flagged": sorted(flagged), "flagged_share": len(flagged) / len(all_tracked),
                   "valid_share_rule": "flagged share <= 0.01", "questions_excluded": excluded_questions,
                   "report_sha256": sha256_file(args.secret_scan)}
    write_json(args.out / "secret_scan.json", secret_scan)
    write_jsonl(args.out / "pool_stats.jsonl", stats_rows)
    write_json(args.out / "pool_manifest.json", {
        "built_at": utc_now(), "repo_commit": commit, "files_searched": len(files),
        "ctags": "Universal Ctags 6.2.1", "ripgrep": subprocess.check_output(["rg", "--version"], text=True).splitlines()[0],
        "window_lines": WINDOW_LINES, "pool_cap": POOL_CAP, "definition_seed_windows": DEFINITION_SEED_WINDOWS,
        "identifiers_per_window": IDENTIFIERS_PER_WINDOW, "n_questions": len(stats_rows),
        "pool_sha256": sha256_file(args.out / "pool.jsonl"),
        "mean_pool_size": sum(s["pool_size"] for s in stats_rows) / max(1, len(stats_rows)),
    })
    print(f"pool: {len(stats_rows)} questions, {len(pool_rows)} windows, excluded {excluded_questions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

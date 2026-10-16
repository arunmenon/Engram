"""Deterministic trace-link candidate pairs and the stratified test/dev draw (E-20260928-18).

  python3 -m pdlc_seed.pairs --records records.jsonl --out <dir>

Candidate generators (no model):
- explicit_ref: a PR or issue whose title, body or branch names another record's
  issue/PR number or RFC number (implements / refines candidates);
- ci_head: a CI record and the PR whose head commit it ran on, and the tickets that
  PR references (verifies candidates);
- module_touch: a PR, or a CI record of a PR, and a code module the PR changed
  (satisfies / verifies candidates via the spec's "test touching a PR's changed module");
- dependency_phrase: "blocked by", "depends on", "waiting for", "after #N" near a
  reference (blocks candidates);
- lexical: highest TF-IDF cosine pairs with no explicit reference (near misses,
  so recall is measurable).
The generator's guess is kept in pairs_meta.jsonl and never shown to labellers.
Draw: strata = generator, 400 pairs with a fixed seed, first 100 of each stratum's
share to dev (by sha256 order), rest to test; exactly 300 test and 100 dev.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
from pathlib import Path

SEED = "pdlc-seed-asf-links-v1"
N_TEST, N_DEV = 300, 100
STRATA_SHARE = {"explicit_ref": 0.30, "ci_head": 0.15, "module_touch": 0.15, "dependency_phrase": 0.10, "lexical": 0.30}
DEP = re.compile(r"(blocked by|depends on|depend on|waiting for|wait for|after|requires|prerequisite)\W{1,5}(?:[^#\n]{0,40})#(\d{2,5})", re.I)
TOKEN = re.compile(r"[a-z][a-z0-9_]{2,}")
STOP = set("the and for with this that from into are was were will have has not but you your our its can should would could when then than also use used using add adds added support supports fix fixes fixed make makes pr rfc issue opendal core feat chore docs refactor test tests".split())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def number_index(records: list[dict]) -> dict[str, str]:
    idx = {}
    for r in records:
        f = r.get("fields", {})
        if r["record_type"] in ("PR", "Ticket", "Requirement") and f.get("number"):
            idx[str(f["number"])] = r["record_id"]
    return idx


def text_of(r: dict) -> str:
    comments = " ".join(c["body"] for c in (r.get("fields", {}).get("comments") or []))
    return f"{r['title']} {r.get('fields', {}).get('branch', '')} {r.get('body') or ''} {comments}"


def tfidf(records: list[dict]) -> dict[str, dict[str, float]]:
    docs = {r["record_id"]: collections.Counter(t for t in TOKEN.findall(text_of(r)[:6000].lower()) if t not in STOP) for r in records}
    df = collections.Counter(t for c in docs.values() for t in c)
    n = len(docs)
    vecs = {}
    for rid, c in docs.items():
        v = {t: (1 + math.log(k)) * math.log(n / df[t]) for t, k in c.items() if df[t] < n * 0.3}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs[rid] = {t: x / norm for t, x in v.items()}
    return vecs


def cos(a: dict, b: dict) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def build_candidates(records: list[dict]) -> list[dict]:
    by_id = {r["record_id"]: r for r in records}
    num = number_index(records)
    rfc_by_num = {r["fields"]["rfc_number"]: r["record_id"] for r in records if r["record_type"] == "Decision"}
    rfc_by_pr = {r["fields"]["rfc_pr"]: r["record_id"] for r in records if r["record_type"] == "Decision" and r["fields"].get("rfc_pr")}
    rfc_by_track = {r["fields"]["tracking_issue"]: r["record_id"] for r in records if r["record_type"] == "Decision" and r["fields"].get("tracking_issue")}
    module_by_key = {r["fields"]["module_key"]: r["record_id"] for r in records if r["record_type"] == "DesignElement"}
    cands: dict[tuple[str, str], dict] = {}

    def add(src: str, dst: str, gen: str, guess: str) -> None:
        if src == dst or src not in by_id or dst not in by_id:
            return
        key = (src, dst)
        if key not in cands and (dst, src) not in cands:
            cands[key] = {"source_id": src, "target_id": dst, "generator": gen, "generator_guess": guess}

    from .build import module_key  # same normalisation as the fixture
    for r in records:
        rid, rtype = r["record_id"], r["record_type"]
        if rtype in ("PR", "Ticket", "Requirement", "Decision"):
            for n in r.get("mentions", []):
                target = num.get(n) or rfc_by_pr.get(n) or rfc_by_track.get(n)
                if not target:
                    continue
                ttype = by_id[target]["record_type"]
                guess = "implements" if rtype == "PR" and ttype in ("Ticket", "Requirement", "Decision") else "refines"
                add(rid, target, "explicit_ref", guess)
                if n in rfc_by_track and rfc_by_track[n] != target:
                    add(rid, rfc_by_track[n], "explicit_ref", guess)
            for m in re.finditer(r"\brfcs?[-_ /#]*(\d{4})\b", text_of(r), re.I):
                if m.group(1) in rfc_by_num:
                    add(rid, rfc_by_num[m.group(1)], "explicit_ref", "implements" if rtype == "PR" else "refines")
            for m in DEP.finditer(text_of(r)):
                target = num.get(m.group(2))
                if target:
                    add(rid, target, "dependency_phrase", "blocks")
        if rtype == "Test":
            pr = num.get(str(r["fields"]["pr"]))
            if pr:
                add(rid, pr, "ci_head", "verifies")
                for n in by_id[pr].get("mentions", []):
                    if num.get(n) and by_id[num[n]]["record_type"] in ("Ticket", "Requirement"):
                        add(rid, num[n], "ci_head", "verifies")
                for f in by_id[pr]["fields"].get("changed_files", []):
                    k = module_key(f)
                    if k in module_by_key:
                        add(rid, module_by_key[k], "module_touch", "verifies")
        if rtype == "PR":
            for f in r["fields"].get("changed_files", []):
                k = module_key(f)
                if k in module_by_key:
                    add(rid, module_by_key[k], "module_touch", "satisfies")
    explicit = set(cands) | {(b, a) for a, b in cands}
    vecs = tfidf(records)
    ids = sorted(vecs)
    scored = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if (a, b) in explicit or by_id[a]["record_type"] == by_id[b]["record_type"] == "DesignElement":
                continue
            s = cos(vecs[a], vecs[b])
            if s > 0.15:
                scored.append((s, a, b))
    scored.sort(reverse=True)
    for s, a, b in scored[:600]:
        src, dst = (a, b) if (by_id[a].get("created_at") or "") >= (by_id[b].get("created_at") or "") else (b, a)
        add(src, dst, "lexical", "none")
        cands.get((src, dst), {}).setdefault("lexical_score", round(s, 4))
    for c in cands.values():
        sa, sb = by_id[c["source_id"]].get("created_at") or "", by_id[c["target_id"]].get("created_at") or ""
        c["write_record_id"] = c["source_id"] if sa >= sb else c["target_id"]
    return list(cands.values())


def draw(cands: list[dict]) -> tuple[list[dict], list[dict]]:
    h = lambda c: hashlib.sha256(f"{SEED}|{c['source_id']}|{c['target_id']}".encode()).hexdigest()
    strata = collections.defaultdict(list)
    for c in cands:
        strata[c["generator"]].append(c)
    for s in strata.values():
        s.sort(key=h)
    total = N_TEST + N_DEV
    quota = {g: min(len(strata[g]), round(total * STRATA_SHARE[g])) for g in STRATA_SHARE}
    short = total - sum(quota.values())
    while short > 0:  # hand spare quota to strata with room, largest first
        room = [g for g in STRATA_SHARE if len(strata[g]) > quota[g]]
        if not room:
            break
        for g in sorted(room, key=lambda g: -(len(strata[g]) - quota[g])):
            if short == 0:
                break
            quota[g] += 1
            short -= 1
    while sum(quota.values()) > total:
        g = max(quota, key=quota.get)
        quota[g] -= 1
    test, dev = [], []
    for g, q in quota.items():
        chosen = strata[g][:q]
        n_dev = round(q * N_DEV / total)
        dev += chosen[:n_dev]
        test += chosen[n_dev:]
    # exact sizes: move by sha order between splits if rounding drifted
    while len(dev) > N_DEV:
        test.append(dev.pop())
    while len(dev) < N_DEV:
        dev.append(test.pop())
    return test, dev


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = read_jsonl(args.records)
    cands = build_candidates(records)
    test, dev = draw(cands)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows, split in (("pairs_test.jsonl", test, "test"), ("pairs_dev.jsonl", dev, "dev")):
        with open(args.out / name, "w", encoding="utf-8") as fh:
            for n, c in enumerate(sorted(rows, key=lambda c: (c["source_id"], c["target_id"]))):
                c["pair_id"] = f"link-{split}-{n:03d}"
                c["split"] = split
                fh.write(json.dumps({k: c[k] for k in ("pair_id", "split", "source_id", "target_id", "write_record_id")}, sort_keys=True) + "\n")
    with open(args.out / "pairs_meta.jsonl", "w", encoding="utf-8") as fh:
        for c in test + dev:
            fh.write(json.dumps(c, sort_keys=True) + "\n")
    report = {"candidates": len(cands), "by_generator": dict(collections.Counter(c["generator"] for c in cands)),
              "test": dict(collections.Counter(c["generator"] for c in test)), "dev": dict(collections.Counter(c["generator"] for c in dev)),
              "seed": SEED}
    (args.out / "pairs_report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()

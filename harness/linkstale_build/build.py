"""Draw the 200 LINK-STALE items, retrieve their neighbours, write the blind labelling sheet.

  ~/projects/Engram/.venv/bin/python -m linkstale_build.build --build <build dir>

Draw rule (no hand-picking): candidates sorted by sha256(cand_id); per decision type take up to 50
per miner hint (supersedes/compatible, stale/valid), at most 3 items per thread and no repeated
memory text, topping up from the other hint if one runs short, to 100 per type.
Neighbours: BM25 (k1 1.5, b 0.75) over corpus.jsonl, query = target memory texts, top 5 after
excluding chunks that contain, are contained in, or share >= 0.8 token Jaccard with any target
text. This stands in for the /v1/context serving path, which is not running on this host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import tiktoken

from .state import STATE_TEMPLATE

STOPWORDS = set("""a an the and or of to in on for with by is are was were be been it its this that these those as at from
not no but if then than so such can will would should must may might do does did has have had we our you your they their
there here which who whom what when where how all any each more most other some into over under about also only via per""".split())
RETRIEVAL = {"method": "BM25", "k1": 1.5, "b": 0.75, "top_k": 5, "tokenizer": r"[a-z0-9_]+ lowercased, stopwords removed, len>=2",
             "query": "target memory texts (memory_1, plus memory_2 for supersession)",
             "exclusion": "chunk contains or is contained in a target text, or token Jaccard >= 0.8 with a target",
             "corpus": "every distinct paragraph (80-word chunks) of every committed version of the repository's docs, plus commit messages",
             "serving_path_note": "deterministic stand-in: the Engram /v1/context serving path was not running on the build host"}
TOKENIZER = "tiktoken o200k_base"


def toks(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in STOPWORDS and len(t) >= 2]


def norm(text: str) -> str:
    return " ".join(text.lower().split())


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(len(d) for d in docs) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in docs]
        self.index = defaultdict(list)
        for i, d in enumerate(docs):
            for t in set(d):
                self.index[t].append(i)

    def scores(self, query: list[str]) -> dict[int, float]:
        out: dict[int, float] = defaultdict(float)
        for t in set(query):
            for i in self.index.get(t, []):
                f = self.tf[i][t]
                dl = len(self.docs[i])
                out[i] += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
        return out


def excluded(chunk: str, targets: list[str]) -> bool:
    c = norm(chunk)
    ct = set(toks(chunk))
    for t in targets:
        tn = norm(t)
        if tn in c or c in tn:
            return True
        tt = set(toks(t))
        if tt and ct and len(tt & ct) / len(tt | ct) >= 0.8:
            return True
    return False


def draw(cands: list[dict]) -> list[dict]:
    chosen = []
    for dtype, hints in (("supersession", ("supersedes", "compatible")), ("staleness", ("stale", "valid"))):
        pool = sorted([c for c in cands if c["decision_type"] == dtype], key=lambda c: hashlib.sha256(c["cand_id"].encode()).hexdigest())
        per_thread, texts, picked = Counter(), set(), []

        def ok(c):
            key = norm(c["memory_1"]["text"])
            return per_thread[c["thread"]] < 3 and key not in texts

        def take(c):
            per_thread[c["thread"]] += 1
            texts.add(norm(c["memory_1"]["text"]))
            picked.append(c)

        for h in hints:
            n = 0
            for c in pool:
                if n >= 50:
                    break
                if c["hint"] == h and c not in picked and ok(c):
                    take(c); n += 1
        for c in pool:
            if len(picked) >= 100:
                break
            if c not in picked and ok(c):
                take(c)
        chosen.extend(picked[:100])
    return chosen


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--build", type=Path, required=True)
    a = p.parse_args()
    cands = [json.loads(l) for l in (a.build / "candidates.jsonl").read_text().splitlines() if l.strip()]
    units = json.loads((a.build / "units.json").read_text())
    slug_to_path = {re.sub(r"[^a-zA-Z0-9]+", "_", pth).strip("_"): pth for pth in units["version_index"]}
    corpus = [json.loads(l) for l in (a.build / "corpus.jsonl").read_text().splitlines() if l.strip()]
    bm = BM25([toks(c["text"]) for c in corpus])
    enc = tiktoken.get_encoding("o200k_base")
    chosen = draw(cands)
    items, sheet = [], []
    for n, c in enumerate(sorted(chosen, key=lambda c: (c["decision_type"], hashlib.sha256(c["cand_id"].encode()).hexdigest())), 1):
        targets = []
        for role in ("memory_1", "memory_2"):
            if role in c:
                src = c[role]["source"]
                s, _, commit = src.partition("@")
                src = f"{slug_to_path.get(s, s)}@{commit}"
                targets.append({"memory_id": role, "text": c[role]["text"], "recorded_at": c[role]["recorded_at"], "source": src})
        target_texts = [t["text"] for t in targets]
        scores = bm.scores(toks(" ".join(target_texts)))
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], corpus[kv[0]]["chunk_id"]))
        nbrs, seen = [], set()
        for idx, sc in ranked:
            ch = corpus[idx]
            if excluded(ch["text"], target_texts) or norm(ch["text"]) in seen:
                continue
            if c["decision_type"] == "staleness" and excluded(ch["text"], [c["snapshot"]["text"]]):
                continue
            seen.add(norm(ch["text"]))
            nbrs.append({"rank": len(nbrs) + 1, "chunk_id": ch["chunk_id"], "text": ch["text"], "source": ch["source"],
                         "recorded_at": ch["recorded_at"], "originating_event_type": ch["originating_event_type"], "bm25": round(sc, 4)})
            if len(nbrs) == 5:
                break
        item = {"item_id": f"LS-{n:03d}", "decision_type": c["decision_type"], "thread_id": c["thread"], "targets": targets,
                "neighbours": nbrs, "nbr_tokens": len(enc.encode("\n\n".join(x["text"] for x in nbrs))), "nbr_tokenizer": TOKENIZER,
                "source_candidate": c["cand_id"]}
        if c["decision_type"] == "staleness":
            item["snapshot_excerpt"] = {"text": c["snapshot"]["text"], "source": c["snapshot"]["source"], "as_of": c["snapshot"]["as_of"]}
        items.append(item)
        tpl = STATE_TEMPLATE
        row = {"id": item["item_id"], "decision_type": item["decision_type"], "question": tpl["question_by_type"][item["decision_type"]],
               "option_A": tpl["rubrics"][item["decision_type"]]["A"], "option_B": tpl["rubrics"][item["decision_type"]]["B"],
               "targets": targets}
        if "snapshot_excerpt" in item:
            row["snapshot_excerpt"] = item["snapshot_excerpt"]
        sheet.append(row)
    for name, rows in (("items_draft.jsonl", items), ("sheet.jsonl", sheet), ("drawn_candidates.jsonl", chosen)):
        with open(a.build / name, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    (a.build / "retrieval_config.json").write_text(json.dumps(RETRIEVAL | {"nbr_tokenizer": TOKENIZER}, indent=1) + "\n")
    print(Counter((c["decision_type"], c["hint"]) for c in chosen), "threads", len({c["thread"] for c in chosen}))


if __name__ == "__main__":
    main()

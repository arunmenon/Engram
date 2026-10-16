"""E-20260928-20-r2 (first cut): answer LoCoMo questions from each extractor build's memory.

  python -m seatswap.answer sample --locomo <locomo10.json> --qa-index <qa_index.jsonl> \
      --sessions <sessions_ok.txt> --out <run>/questions.jsonl [--per-category 120] [--seed 20261026]
  python -m seatswap.answer answer --locomo … --questions <run>/questions.jsonl --build <extracted.jsonl> \
      --label A1 --out <run>/answers/A1.jsonl [--reader deepseek-ai/DeepSeek-V3.2]
  python -m seatswap.answer judge --questions … --answers <run>/answers/A1.jsonl --out <run>/judged/A1.jsonl \
      [--judge Qwen/Qwen3-235B-A22B-Instruct-2507]
  python -m seatswap.answer score --run <run> --baseline A1 --builds A1,B1,B2

Memory served to the reader: only the extracted items of the build (preferences, skills,
interests), each rendered with its session date and the speaker found by matching its quote
to the transcript turn (same deterministic rendering for every build). Retrieval: BM25 over the
conversation's items with the question as query, items taken in rank order until 3,000 tokens
(o200k_base). This stands in for Engram's hybrid retrieval, which needs the Redis and Neo4j
stack; it is identical across arms. Reader and judge are hosted through the Hugging Face router
(HF token from the local cache, never written anywhere).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gate_eval.common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl  # noqa: E402
from gate_eval.stats import cluster_bootstrap, mean  # noqa: E402

ROUTER = "https://router.huggingface.co/v1/chat/completions"
SERVED_TOKENS = 3000
TOKEN = re.compile(r"[a-z0-9]+")
SESSION_OF = re.compile(r"^D(\d+):")

READER_PROMPT = """You answer questions about a long conversation between two people, using only the memory records below.
Each record was extracted from the conversation and shows the session date and, when known, who said it.
Answer briefly (a few words or one short sentence). For questions about time, give the date or period.
If the records do not contain the answer, reply exactly: Not mentioned.

Memory records:
{memory}

Question: {question}
Answer:"""

JUDGE_PROMPT = """You grade an answer to a question about a conversation.

Question: {question}
Reference: {reference}
Answer given: {answer}

Scoring: 1 if the answer is correct and matches the reference in substance (wording, format and extra detail do not matter; a date or period that matches the reference counts); 0.5 if it is partly correct (some but not all required parts, or the right answer mixed with a wrong one); 0 if it is wrong, or says the information is not available when the reference gives an answer.
{adversarial_note}
Reply with JSON only: {{"score": 1 | 0.5 | 0, "reason": "<one short sentence>"}}"""

ADVERSARIAL_NOTE = ("This question is adversarial: its premise is not supported by the conversation, so the correct answer is "
                    "that the information is not mentioned or not known. Score 1 if the answer says so; score 0 if it gives a "
                    "substantive answer (the misleading reference below the question is what a wrong answer would say).")


def hf_token() -> str:
    return (Path.home() / ".cache/huggingface/token").read_text().strip()


def chat(model: str, prompt: str, max_tokens: int = 300) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    last = None
    for attempt in range(6):
        request = urllib.request.Request(ROUTER, data=body, method="POST",
                                         headers={"Authorization": f"Bearer {hf_token()}", "Content-Type": "application/json"})
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                payload = json.loads(response.read())
            return {"text": (payload["choices"][0]["message"]["content"] or "").strip(), "model_reported": payload.get("model"),
                    "usage": payload.get("usage"), "latency_s": round(time.time() - started, 2), "attempts": attempt + 1}
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError) as exc:
            last = exc
            time.sleep(min(60, 2 ** attempt))
    return {"text": None, "error": str(last), "attempts": 6}


# ----------------------------------------------------------------------------- memory rendering and retrieval

def conversation_index(locomo: list[dict]) -> dict:
    """sample_id -> {session_no: (date, [(speaker, text)])}"""
    out = {}
    for conv in locomo:
        sessions = {}
        for key, turns in conv["conversation"].items():
            m = re.fullmatch(r"session_(\d+)", key)
            if m:
                sessions[int(m.group(1))] = (conv["conversation"].get(f"session_{m.group(1)}_date_time", ""),
                                             [(t["speaker"], t["text"]) for t in turns])
        out[conv["sample_id"]] = sessions
    return out


def normalise(text: str) -> str:
    return " ".join(TOKEN.findall(text.lower()))


def render_item(item: dict, sessions: dict) -> tuple[str, str]:
    sample_id, session_key = item["session_id"].split(":")
    session_no = int(session_key.split("_")[1])
    date, turns = sessions[sample_id][session_no]
    quote = normalise(item.get("source_quote") or "")
    speaker = ""
    if quote:
        for who, text in turns:
            if quote in normalise(text):
                speaker = who
                break
    fields = {k: v for k, v in item["fields"].items() if k not in ("confidence", "source_turn_index", "source_quote") and v not in (None, "")}
    body = "; ".join(f"{k}: {v}" for k, v in fields.items())
    header = f"[{date}{', ' + speaker if speaker else ''}] {item['item_kind']}"
    quote_part = f' (quote: "{item["source_quote"]}")' if item.get("source_quote") else ""
    return sample_id, f"{header}: {body}{quote_part}"


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.2, b: float = 0.75) -> None:
        self.tokens = [TOKEN.findall(d.lower()) for d in docs]
        self.avg = mean([len(t) for t in self.tokens]) if docs else 0.0
        df = Counter(w for t in self.tokens for w in set(t))
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(t) for t in self.tokens]
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        q = TOKEN.findall(query.lower())
        out = []
        for tf, toks in zip(self.tf, self.tokens):
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(toks) / (self.avg or 1)))
            out.append(s)
        return out


# ----------------------------------------------------------------------------- commands

def cmd_sample(args) -> int:
    locomo = json.loads(args.locomo.read_text())
    ok_sessions = {line.strip() for line in args.sessions.read_text().splitlines() if line.strip()}
    qa_index = read_jsonl(args.qa_index)
    by_id = {c["sample_id"]: c for c in locomo}
    eligible = []
    for row in qa_index:
        qa = by_id[row["sample_id"]]["qa"][row["qa_index"]]
        sessions_needed = {int(m.group(1)) for e in qa.get("evidence", []) for m in [SESSION_OF.match(e.strip())] if m}
        if sessions_needed and all(f"{row['sample_id']}:session_{s}" in ok_sessions for s in sessions_needed):
            eligible.append({"qa_id": row["qa_id"], "sample_id": row["sample_id"], "category": qa["category"],
                             "question": qa["question"], "answer": qa.get("answer"), "adversarial_answer": qa.get("adversarial_answer"),
                             "evidence": qa.get("evidence")})
    rng = random.Random(args.seed)
    chosen = []
    for category in sorted({q["category"] for q in eligible}):
        pool = sorted([q for q in eligible if q["category"] == category], key=lambda q: q["qa_id"])
        rng.shuffle(pool)
        chosen.extend(pool[: args.per_category])
    chosen.sort(key=lambda q: q["qa_id"])
    write_jsonl(args.out, chosen)
    print(json.dumps({"eligible": len(eligible), "chosen": len(chosen),
                      "by_category": Counter(q["category"] for q in chosen), "sha256": sha256_file(args.out)}, default=str))
    return 0


def cmd_answer(args) -> int:
    import tiktoken
    encoding = tiktoken.get_encoding("o200k_base")
    locomo = json.loads(args.locomo.read_text())
    sessions = conversation_index(locomo)
    memory: dict[str, list[str]] = defaultdict(list)
    for item in read_jsonl(args.build):
        sample_id, text = render_item(item, sessions)
        memory[sample_id].append(text)
    indexes = {sid: BM25(texts) for sid, texts in memory.items()}
    questions = read_jsonl(args.questions)

    def one(q: dict) -> dict:
        texts = memory.get(q["sample_id"], [])
        served, used = [], 0
        if texts:
            scores = indexes[q["sample_id"]].scores(q["question"])
            ranked = sorted(range(len(texts)), key=lambda i: (-scores[i], i))
            for i in ranked:
                cost = len(encoding.encode(texts[i])) + 1
                if used + cost > SERVED_TOKENS:
                    continue
                served.append(texts[i])
                used += cost
        reply = chat(args.reader, READER_PROMPT.format(memory="\n".join(served) or "(none)", question=q["question"]), 200)
        return {"qa_id": q["qa_id"], "build": args.label, "served_items": len(served), "served_tokens": used,
                "memory_items_in_conversation": len(texts), "answer": reply.get("text"), "reader": args.reader,
                "reader_reported": reply.get("model_reported"), "usage": reply.get("usage"), "error": reply.get("error"),
                "latency_s": reply.get("latency_s")}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(one, questions))
    write_jsonl(args.out, rows)
    print(f"answered {len(rows)} ({sum(1 for r in rows if r['answer'] is None)} failed) -> {args.out}")
    return 0


def parse_score(text: str | None) -> float | None:
    if not text:
        return None
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        value = float(json.loads(text[start:end])["score"])
        return value if value in (0.0, 0.5, 1.0) else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def cmd_judge(args) -> int:
    questions = {q["qa_id"]: q for q in read_jsonl(args.questions)}
    answers = read_jsonl(args.answers)

    def one(a: dict) -> dict:
        q = questions[a["qa_id"]]
        adversarial = q["category"] == 5
        reference = ("Not mentioned in the conversation. (Misleading answer: " + str(q.get("adversarial_answer")) + ")") if adversarial else str(q["answer"])
        prompt = JUDGE_PROMPT.format(question=q["question"], reference=reference, answer=a["answer"] or "(no answer)",
                                     adversarial_note=ADVERSARIAL_NOTE if adversarial else "")
        score = None
        reply = {}
        for _ in range(3):
            reply = chat(args.judge, prompt, 150)
            score = parse_score(reply.get("text"))
            if score is not None:
                break
        return {**a, "category": q["category"], "sample_id": q["sample_id"], "score": score, "judge": args.judge,
                "judge_reported": reply.get("model_reported"), "judge_text": reply.get("text"), "judge_usage": reply.get("usage")}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(one, answers))
    write_jsonl(args.out, rows)
    print(f"judged {len(rows)} ({sum(1 for r in rows if r['score'] is None)} unparsed) -> {args.out}")
    return 0


def cmd_score(args) -> int:
    builds = args.builds.split(",")
    judged = {b: {r["qa_id"]: r for r in read_jsonl(args.run / "judged" / f"{b}.jsonl")} for b in builds}
    baseline = args.baseline
    rows_csv, summary = [], {}
    for b in builds:
        vals = [r["score"] for r in judged[b].values() if r["score"] is not None]
        answerable = [r["score"] for r in judged[b].values() if r["score"] is not None and r["category"] != 5]
        adversarial = [r["score"] for r in judged[b].values() if r["score"] is not None and r["category"] == 5]
        per_cat = {c: mean([r["score"] for r in judged[b].values() if r["score"] is not None and r["category"] == c]) for c in range(1, 6)}
        summary[b] = {"n": len(vals), "accuracy": mean(vals), "answerable_cat1_4": mean(answerable),
                      "adversarial_cat5_abstention": mean(adversarial), "by_category": per_cat,
                      "mean_served_tokens": mean([r["served_tokens"] for r in judged[b].values()]),
                      "mean_memory_items": mean([r["memory_items_in_conversation"] for r in judged[b].values()])}
        rows_csv.append({"build": b, **{k: v for k, v in summary[b].items() if k != "by_category"},
                         **{f"cat{c}": v for c, v in per_cat.items()}})

    def paired(x: list[str], y: list[str], cluster: str) -> dict:
        common = sorted(set.intersection(*[set(k for k, r in judged[b].items() if r["score"] is not None) for b in x + y]))
        diffs = [{"qa_id": q, "conv": judged[x[0]][q]["sample_id"],
                  "d": mean([judged[b][q]["score"] for b in x]) - mean([judged[b][q]["score"] for b in y])} for q in common]
        key = "qa_id" if cluster == "question" else "conv"
        boot = cluster_bootstrap(diffs, key, lambda xs: mean([d["d"] for d in xs]), args.resamples, args.seed)
        return {k: boot[k] for k in ("point", "ci95_two_sided", "lb95", "ub95", "G")} | {"n": len(diffs)}

    b_builds = [b for b in builds if b.startswith("B")]
    a_builds = [b for b in builds if b.startswith("A")]
    contrasts = {
        "B_minus_A_question": paired(b_builds, a_builds, "question"),
        "B_minus_A_conversation": paired(b_builds, a_builds, "conversation"),
    }
    if len(b_builds) >= 2:
        contrasts["B1_minus_B2_question"] = paired([b_builds[0]], [b_builds[1]], "question")
    if len(a_builds) >= 2:
        contrasts["A1_minus_A2_question"] = paired([a_builds[0]], [a_builds[1]], "question")
    q = contrasts["B_minus_A_question"]
    noise_ok = all(abs(summary[a]["accuracy"] - summary[b]["accuracy"]) <= 0.03 for a, b in [(b_builds[0], b_builds[1])] if len(b_builds) >= 2)
    if q["point"] < -0.02 and q["ci95_two_sided"][1] < 0:
        outcome = "negative"
    elif q["ci95_two_sided"][0] > -0.02:
        outcome = "noninferior"
    else:
        outcome = "inconclusive"
    verdict = {"rule": "LoCoMo non-inferiority: lower end of the two-sided 95% question-level interval of (B minus A) above -0.02; "
                       "negative if the point is below -0.02 and the interval lies wholly below zero",
               "outcome": outcome, "conversation_robust": contrasts["B_minus_A_conversation"]["ci95_two_sided"][0] > -0.02,
               "build_noise_B_within_3pts": noise_ok, "A_builds": a_builds, "B_builds": b_builds,
               "pdlc_screen": "not run (first cut is LoCoMo only)", "contrasts": contrasts, "summary": summary}
    write_json(args.run / "verdict.json", verdict)
    with open(args.run / "metrics.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows_csv[0].keys()))
        writer.writeheader()
        writer.writerows(rows_csv)
    print(json.dumps({"outcome": outcome, "contrasts": contrasts, "summary": {b: {k: v for k, v in s.items() if k != "by_category"} for b, s in summary.items()}}, indent=1, default=str))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seatswap.answer")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--locomo", type=Path, required=True)
    s.add_argument("--qa-index", type=Path, required=True)
    s.add_argument("--sessions", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--per-category", type=int, default=120)
    s.add_argument("--seed", type=int, default=20261026)
    a = sub.add_parser("answer")
    a.add_argument("--locomo", type=Path, required=True)
    a.add_argument("--questions", type=Path, required=True)
    a.add_argument("--build", type=Path, required=True)
    a.add_argument("--label", required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--reader", default="deepseek-ai/DeepSeek-V3.2")
    a.add_argument("--workers", type=int, default=12)
    j = sub.add_parser("judge")
    j.add_argument("--questions", type=Path, required=True)
    j.add_argument("--answers", type=Path, required=True)
    j.add_argument("--out", type=Path, required=True)
    j.add_argument("--judge", default="Qwen/Qwen3-235B-A22B-Instruct-2507")
    j.add_argument("--workers", type=int, default=12)
    sc = sub.add_parser("score")
    sc.add_argument("--run", type=Path, required=True)
    sc.add_argument("--baseline", default="A1")
    sc.add_argument("--builds", required=True)
    sc.add_argument("--resamples", type=int, default=10_000)
    sc.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args(argv)
    return {"sample": cmd_sample, "answer": cmd_answer, "judge": cmd_judge, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())

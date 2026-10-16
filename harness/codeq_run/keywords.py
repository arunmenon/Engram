"""Blind keyword set for E-20260928-19-r2 (the spec's pinned-LLM keyword set).

  python -m codeq_run.keywords --repo <checkout> --dataset <frozen CODEQ-ASF-80> --out <keywords_blind.jsonl> \
      [--model gpt-5.6-terra]

The model sees only the question text, the repository README and its top-level directory
tree (two levels of directories), never gold spans or the frozen keywords. It returns 6 to
15 search keywords per question. The output is frozen with its sha256 before any pool is
built from it. OPENAI_API_KEY comes from the environment and is never written anywhere.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gate_eval.common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl

README_CHARS = 12_000
PROMPT = """You help a developer search a code repository with ripgrep (fixed-string, case-insensitive).
You have not seen the code. You see the repository README and its directory tree below.

Write 6 to 15 search keywords for the question: identifiers, type or function names, config keys,
file or module names, or short phrases that are likely to appear verbatim in the code or docs that
answer it. Prefer specific terms over generic words. Return JSON: {"keywords": ["...", ...]}.

Question: {question}

Directory tree (directories only, two levels):
{tree}

README:
{readme}
"""


def directory_tree(repo: Path) -> str:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=repo, text=True).splitlines()
    dirs = sorted({"/".join(p.split("/")[:depth]) for p in tracked for depth in (1, 2) if p.count("/") >= depth})
    return "\n".join(dirs)


def ask(model: str, prompt: str) -> dict:
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "response_format": {"type": "json_object"}}).encode()
    request = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                                              "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read())
            return {"keywords": json.loads(payload["choices"][0]["message"]["content"])["keywords"],
                    "model_reported": payload.get("model"), "usage": payload.get("usage")}
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"keyword call failed: {last}")


def ask_claude(model: str, prompt: str) -> dict:
    """Headless Claude call (no tools). Used when the OpenAI key has no credits."""
    last = None
    for attempt in range(4):
        proc = subprocess.run(["claude", "-p", "--model", model, "--output-format", "json", "--tools", ""],
                              input=prompt, capture_output=True, text=True, timeout=600,
                              cwd=os.environ.get("KEYWORD_CWD", "/tmp"))
        try:
            envelope = json.loads(proc.stdout)
            text = envelope["result"]
            start, end = text.index("{"), text.rindex("}") + 1
            return {"keywords": json.loads(text[start:end])["keywords"], "model_reported": model,
                    "usage": envelope.get("usage")}
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            last = f"{exc}: {proc.stderr[:300]}"
            time.sleep(2 ** attempt)
    raise RuntimeError(f"claude keyword call failed: {last}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codeq_run.keywords")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-terra")
    parser.add_argument("--backend", choices=["openai", "claude"], default="openai")
    args = parser.parse_args(argv)

    readme = (args.repo / "README.md").read_text(encoding="utf-8")[:README_CHARS]
    tree = directory_tree(args.repo)
    questions = read_jsonl(args.dataset / "questions.jsonl")

    def one(question: dict) -> dict:
        result = (ask_claude if args.backend == "claude" else ask)(args.model, PROMPT.replace("{question}", question["question"]).replace("{tree}", tree).replace("{readme}", readme))
        keywords = [k.strip() for k in result["keywords"] if isinstance(k, str) and k.strip()][:15]
        return {**{k: v for k, v in question.items() if k != "keywords"}, "keywords": keywords,
                "keyword_source": f"{args.model} blind (question, README, directory tree)",
                "model_reported": result["model_reported"], "usage": result["usage"]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(one, questions))
    write_jsonl(args.out, rows)
    write_json(args.out.with_suffix(".manifest.json"), {
        "created_at": utc_now(), "model": args.model, "models_reported": sorted({r["model_reported"] for r in rows}),
        "inputs": "question text, README.md (first 12,000 chars), directory tree (two levels)",
        "sha256": sha256_file(args.out), "n": len(rows),
        "backend": args.backend, "usage": [r["usage"] for r in rows],
    })
    print(f"wrote {len(rows)} keyword rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

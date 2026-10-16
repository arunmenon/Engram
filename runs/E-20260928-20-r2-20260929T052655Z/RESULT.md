# E-20260928-20-r2: an open model (gemma-4-31b) in the extractor seat (first cut, blocked)

We set out to test whether Google's open gemma-4-31b model could replace our hosted extractor (gpt-5.6-terra) on the LoCoMo chat benchmark without losing more than 2 points of answer accuracy. We could not run it. This Mac has 16 GB of memory, too little for a 31-billion-parameter model. The one hosted route that served gemma-4-31b (Hugging Face's inference router) ran out of monthly credits after 4 of 231 sessions. The OpenAI key, needed for the gpt-5.6-terra comparison builds, also has no credits left. Nothing here says anything yet about gemma's quality. What does exist: the pipeline is built and tested end to end on real calls, the 559 benchmark questions are drawn and frozen, and one full terra build already exists from the labelling session. Recommended next step: top up Hugging Face (or OpenAI) credits, or name a GPU host with at least 24 GB. After that the first cut is about an hour of unattended work with the commands below.

## What was done

- Harness: `seatswap.answer` (question sampling, memory rendering, BM25 retrieval to 3,000 served tokens, hosted reader, judge from a different model family, paired bootstrap scorer with the spec's non-inferiority rule), and a `--sessions-file` option on `gate_eval.locomo_extract` so every build extracts exactly the same sessions.
- Gemma via Engram's own extractor: `LLMExtractionClient` with `CG_LLM_MODEL_ID=huggingface/google/gemma-4-31B-it` worked: 2 test sessions and 4 build sessions extracted (about 9 items per session against about 20 for terra), 15,475 prompt and 3,964 completion tokens in the partial build. Then 7 sessions failed with `You have depleted your monthly included credits` (Hugging Face Inference Providers).
- Questions: `questions.jsonl`, 559 LoCoMo questions drawn with seed 20261026, up to 120 per category (category 3 has only 79 eligible), restricted to questions whose evidence sessions the existing terra build extracted (231 of 272 sessions: 8 whole conversations plus 14 of conv-49's 25 sessions; conv-50 has none). sha256 dafd4fd8b2e25c4d8dce7a6d152b53a5c68f8751e2c3d6158e964320f0af46c9.
- Reader and judge chosen and probed: reader deepseek-ai/DeepSeek-V3.2, judge Qwen/Qwen3-235B-A22B-Instruct-2507 (neither is a Gemma, GPT or Claude model), both through the same router, so both are now blocked too.

## Blockers

1. OpenAI API: `credit_balance_exhausted` (04:37Z). Blocks the second terra build (A2) and any hosted reader on OpenAI.
2. Hugging Face Inference Providers: monthly included credits depleted (05:28Z). Blocks the gemma builds, the reader and the judge.
3. Local: M1 Pro with 16 GB; gemma-4-31b needs about 18 GB even at 4-bit, so it does not fit. No vLLM GPU host is configured.

## To resume

From `harness/`, once credits exist: run `seatswap/gemma_builds.sh` equivalent (two builds B1 and B2 of `gate_eval.locomo_extract` with `--sessions-file builds/sessions_A1_ok.txt`), then `python -m seatswap.answer answer` for A1 (the labelling session's terra build at `work/labelling-engram/harness/data/raw/locomo/terra/extracted.jsonl`), B1 and B2, then `judge`, then `score --builds A1,B1,B2`. A2 needs OpenAI credits.

## Weaker than the spec wanted (for when it runs)

Only one terra build exists (the spec asks for two); retrieval is BM25 over extracted items, standing in for Engram's hybrid retrieval, which needs the Redis and Neo4j stack; no human-checked judge subsample; the PDLC harm screen is not part of the first cut.

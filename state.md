# Executor state (fast-track queue)

| # | Item | Spec | Dataset | Status | Notes |
|---|---|---|---|---|---|
| 1 | Jev write gate + naming audit | E-20260928-06-r2 | H5-labelled-90 frozen | **done** (first cut = full design) | runs/E-20260928-06-r2-20260929T041426Z; 4,320 Jev calls; spec rule positive (neutral names), H5 killed (Jev worse than extractor confidence, ECE 0.31); bus RUN-E-20260928-06-r2-20260929T045459Z. Laya arm not run (licence). |
| 2 | Jev reranking filter | E-20260928-19-r2 | CODEQ-ASF-80 frozen | **done** (full spec arms A, B, B-noguard, C, D, 20 repeats) | runs/E-20260928-19-r2-20260929T043953Z; blind keywords (claude-sonnet-5-5) primary: rule positive (B-C +17.7 [12.7, 26.5], B-A +7.8, D-B -9.3); dataset keywords invalid (written by the gold annotator; lexical floor 96.8%). |
| 3 | Jev links at write time | E-20260928-18-r2 | LINK-ASF-LOCOMO frozen | **first cut done (partial)** | runs/E-20260928-18-r2-20260929T053158Z; LoCoMo only: Jev links add nothing over deterministic links on answers (-0.3 pts [-3.1, +2.6]); deterministic links +3.8 over none. PDLC trace-link part also done: runs/E-20260928-18-r2-20260929T055849Z-pdlc (1,200 Jev calls; trace-link precision Jev 0.76 vs rules 0.62, +13.6 [7.5, 19.8]; macro-F1 +2.9 [-4.9, +10.3]; fixed 0.60 beats dev refit). Still missing: arm B (needs OpenAI credits), labels for Jev-proposed out-of-pool pairs, the 120 PDLC answer questions. |
| 4 | Stray opinion sways Jev | E-20260928-07-r2 | LINK-STALE-200 frozen | **done** (full design) | runs/E-20260928-07-r2-20260929T052017Z; 2,260 Jev calls; harness bugs fixed first (commit 3039c31); rule negative (d1 pass), d2 also pass (C2 cuts capture 32% to 23%); bus RUN-E-20260928-07-r2. Ran while item 2's local cross-encoder scoring was still going (no hosted calls overlapped item 2's Jev calls). |
| 5 | Open model as extractor | E-20260928-20-r2 | SEATSWAP-LOCOMO-PDLC frozen | **blocked** (failed bundle on bus) | runs/E-20260928-20-r2-20260929T052655Z; OpenAI and HF credits exhausted, 16 GB Mac cannot hold gemma-4-31b. Pipeline built (seatswap.answer), 559 questions frozen, 4 gemma sessions extracted. Resume steps in RESULT.md. Retried 06:27Z: a tiny HF probe passed but real extraction calls still failed (7 ok, 34 failed); retry dir removed. |
| 6 | Small model for what to remember | E-20260928-12-r2 | MEMDEC building | **blocked on dataset** | DATASETS.md row 6 still `building` at 06:27Z; its extraction also runs on gpt-5.6-terra, so it waits on OpenAI credits too. Nothing started. |

## Environment notes (2026-09-29)
- OpenAI API key has no credits (`credit_balance_exhausted`, 04:37Z). Blocks gpt-5.6-terra extraction (items 3, 5, and MEMDEC). Claude (`claude -p`) and Jev work.
- Tools installed with brew: ripgrep, gitleaks 8.30.1, universal-ctags 6.2.1. Reranker venv: ~/MemoryRSI-Signals/work/ext/venv-rerank (torch, sentence-transformers, tiktoken); bge-reranker-v2-m3 @953dc6f6 in the HF cache.
- Checkouts: ~/MemoryRSI-Signals/work/ext/genigrep @da10c5e, ~/MemoryRSI-Signals/work/ext/opendal @5af2bd77.
- Branch merged label/fast-track (labelling harness scripts) into exec/fast-track.
- A git hook rejects commit messages with a Co-Authored-By Claude line; commits carry no attribution line.

## Next run: where to pick up (06:30Z)
1. Probe credits first (OpenAI chat call with gpt-5.6-terra; HF router with a real extraction-size prompt, not a one-word probe).
2. If HF works: item 5 first cut per runs/E-20260928-20-r2-20260929T052655Z/RESULT.md (gemma builds B1, B2 with --sessions-file; answer A1/B1/B2 with seatswap.answer; judge; score). New run id.
3. If OpenAI works: item 3 arm B (LLM linker over the frozen candidates in runs/E-20260928-18-r2-20260929T053158Z and the PDLC pairs), a second terra build A2 for item 5, and check whether MEMDEC (item 6) gets frozen.
4. Items 1, 2, 4 are complete; no follow-up queued for them beyond what their RESULT.md files recommend.

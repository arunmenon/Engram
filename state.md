# Executor state (fast-track queue)

| # | Item | Spec | Dataset | Status | Notes |
|---|---|---|---|---|---|
| 1 | Jev write gate + naming audit | E-20260928-06-r2 | H5-labelled-90 frozen | **done** (first cut = full design) | runs/E-20260928-06-r2-20260929T041426Z; 4,320 Jev calls; spec rule positive (neutral names), H5 killed (Jev worse than extractor confidence, ECE 0.31); bus RUN-E-20260928-06-r2-20260929T045459Z. Laya arm not run (licence). |
| 2 | Jev reranking filter | E-20260928-19 | CODEQ-ASF-80 frozen | not started | |
| 3 | Jev links at write time | E-20260928-18 | LINK-ASF-LOCOMO frozen | not started | |
| 4 | Stray opinion sways Jev | E-20260928-07-r2 | LINK-STALE-200 frozen | not started | bytes_present + nbr_tokens bugs to fix first |
| 5 | Open model as extractor | E-20260928-20 | SEATSWAP-LOCOMO-PDLC frozen | not started | |
| 6 | Small model for what to remember | E-20260928-12-r2 | MEMDEC building | blocked on dataset | |

## Environment notes (2026-09-29)
- OpenAI API key has no credits (`credit_balance_exhausted`, 04:37Z). Blocks gpt-5.6-terra extraction (items 3, 5, and MEMDEC). Claude (`claude -p`) and Jev work.
- Tools installed with brew: ripgrep, gitleaks 8.30.1, universal-ctags 6.2.1. Reranker venv: ~/MemoryRSI-Signals/work/ext/venv-rerank (torch, sentence-transformers, tiktoken); bge-reranker-v2-m3 @953dc6f6 in the HF cache.
- Checkouts: ~/MemoryRSI-Signals/work/ext/genigrep @da10c5e, ~/MemoryRSI-Signals/work/ext/opendal @5af2bd77.
- Branch merged label/fast-track (labelling harness scripts) into exec/fast-track.
- A git hook rejects commit messages with a Co-Authored-By Claude line; commits carry no attribution line.

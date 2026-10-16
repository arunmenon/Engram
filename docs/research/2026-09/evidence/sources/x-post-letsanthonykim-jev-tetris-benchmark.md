---
schema_version: 1
artifact_id: N-20261004-03
artifact_type: note
producer: triage
run_id: triage-20261004T014502Z-25fb
created_at: 2026-10-04T01:52:17Z
input_refs: [{"artifact_id": "post:2104073613829910629", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:x:2104073613829910629
claim_cluster: x:2104073613829910629
feeds: ["decision"]
primary_source: https://x.com/letsanthonykim/status/2104073613829910629
source_commit: n/a
strength: builder-report
pillar_primary: R9
pillar_secondary: ["R4"]
memory_stage: reranking
priority: 1
tags: {"mechanism": ["code-shortlist-then-decision-model-pick", "confidence-gated-reask", "calibration-buckets"], "workload": ["game-agent", "Tetris"], "lifecycle_stage": ["reranking"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "medium: first-hand thread with counts, no logs or code", "control": "medium: paired by seed against a code-only bot, 5 to 10 seeds per comparison, 50-piece games", "independence": "high: independent builder", "reproducibility": "low: demo app published, benchmark code and seeds not", "applicability": "medium: the shortlist-then-pick and confidence re-ask patterns map to memory reranking, the game domain does not"}
beliefs_affected: {"supports": ["B12", "B10"], "contradicts": ["B14"], "would_create": ["Within a code-built shortlist, a System One pick matches a hand-coded policy on outcome and follows natural-language preferences the code cannot express"]}
claim_correction: none (author frames it as "direction, not proof"; the Tetris 9 vs 3 trend is stated as not significant)
---

# Jev playing Tetris: shortlist from code, pick from Jev, calibrated confidence (Anthony Kim, TypeSafe Jev)

- **URL:** https://x.com/letsanthonykim/status/2104073613829910629 (demo: https://jev-tetris-battle.vercel.app)
- **Type:** X post (13-part builder thread, delivered as one long post)
- **Author / org:** Anthony Kim (@letsanthonykim)
- **Date:** 2026-09-27
- **Retrieved:** 2026-10-04 via the fxtwitter mirror API (full thread text); demo app not executed; version n/a
- **Cited by evidence:** @letsanthonykim 2104073613829910629
- **Relevance to a memory stack:** medium, a clean small test of the "code shortlists, decision model picks" split and of confidence-bucket reliability

## TL;DR
- Jev alone, given the raw grid, failed: candidates looked identical, "confidence fell to ~0.1, and it topped out at piece 38" (thread).
- Jev picking from code-written move descriptions, solo: 4.4 avoidable holes per game vs 1.2 for the code bot over 10 games.
- Jev+ (code shortlists 5 safe moves, Jev picks): "no difference in lines, score, or holes" over 10 games; 7 T-spins vs 0; 9 Tetrises vs 3 with a code-enforced empty column ("Too few games to call it significant").
- Confidence buckets: moves at 0.2 to 0.4 confidence made an avoidable hole 20% of the time, at 0.8+ only 2%; re-asking when unsure cut the low bucket to 8%.
- 4,300+ calls, "zero broken answers"; 0.2 to 0.3 s per call; about $0.0025 per 50-piece game (Jev+).

## What it claims / describes
Setup verbatim: "me, Jev, and a code-only bot play the same piece sequence side by side ... 50-piece games, 5-10 seeds, paired by seed." Code enumerates every legal placement; Jev receives the options and "returns a probability for each, plus a confidence score". v1 sent the raw grid and rough move descriptions; v2 had code describe each move in words ("creates a hole", "lands lowest"). Jev+ adds a code shortlist of 5 safe moves. Strategy is set by natural-language instructions (including Korean), mapped by Jev to settings; off-topic input ("what's for lunch?") was rejected.

Multi-move plans fail: "Keep the right column empty and go for Tetrises" as a per-move priority gave "0 Tetrises in 6 games", because "Each move is a separate call, so the plan never carried over. Code had to enforce the empty column." Vague wording scores 0.50: "stack high and blow it up big" scored "exactly 0.50 on 'does this ask for a Tetris?'".

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Avoidable holes per game, solo Jev | "4.4" | code bot "1.2" | same 10 games | paired by seed |
| Jev+ vs bot | "no difference in lines, score, or holes" | code bot | 10 games | no test statistic |
| T-spins | Jev+ "7" | bot "none" | 10 games | |
| Tetrises with empty-column rule | Jev+ "9 Tetrises in 10 games" | bot "3" | same rule enforced by code | "Too few games to call it significant" |
| Avoidable hole rate by confidence | "0.2-0.4 confidence ... 20%"; "0.8+, only 2%" | | per move | bucket sizes not stated |
| Re-ask when unsure | low bucket "cut ... to 8%" | 20% | | |
| Per-plan instruction | "0 Tetrises in 6 games" | | per-move priority only | |
| Calls and format errors | "4,300+ calls, zero broken answers" | | | |
| Latency | "0.2-0.3 s per call" | bot "~0.01 s per move" | | |
| Cost | "~$0.0025 per 50-piece game with Jev+, $0.007-0.012 solo" | | | |

## Mechanism details you could implement
- Shortlist with deterministic code (safe candidates), then let the decision model pick by the human's stated preference: the same split as retrieval-then-rerank.
- Describe candidates in words the model can compare; raw structure (the grid) collapsed confidence to ~0.1.
- Gate on confidence: below a cutoff, re-ask or hand off to code; reported low-bucket error fell 20% to 8%.
- Keep plans in code or state, not in the per-call prompt; a stateless per-call decision forgets plans.

## Limitations, caveats, counter-evidence
- 5 to 10 seeds, 10-game comparisons; bucket counts not given; author: "Small experiment, so read it as direction, not proof."
- Game domain; transfer to memory ranking is an inference.
- Calibration evidence is the author's bucket analysis, not a reliability diagram.

## Takeaways for tuning a memory stack
- For reranking, let code or retrieval produce a safe shortlist and use the System One pick only to apply the request's intent.
- Verbalise candidates (titles, one-line summaries) rather than passing raw structured blobs (inference).
- A confidence re-ask loop is cheap and may cut low-confidence errors substantially; worth an arm in any rerank test.

## Open questions
- How many moves fell in each confidence bucket?
- Does re-asking change the answer or only the confidence?

## Grading and labels
- Directness: medium. Control: medium. Independence: high. Reproducibility: low. Applicability: medium.
- Pillars: R9 primary, R4 secondary. Stage: reranking. Priority 1. Product: Jev (TypeSafe).
- Beliefs: supports B12 (a typed decision model alone fails open-loop planning; inside a code-built structure it holds up); supports B10 (a single choice call over a shortlist works); contradicts B14 in part.
- Contradiction: B14 says vendor calibration is "claimed, not shown". This independent builder shows monotone error by confidence bucket (20% at 0.2 to 0.4, 2% at 0.8+). Weak evidence (bucket sizes unknown, game domain), but it is a third-party showing, not a vendor claim. Open row: does Jev confidence order errors on our data?

## Origin chain
Thread 2104073613829910629 (all numbers in text), then demo app jev-tetris-battle.vercel.app (not a source of numbers). Independence: one builder, one game, one model.

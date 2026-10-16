---
schema_version: 1
artifact_id: N-20261001-02
artifact_type: note
producer: triage
run_id: triage-20261001T014803Z-94c1
created_at: 2026-10-01T02:18:45Z
input_refs: [{"artifact_id": "post:2105272414405800151", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:ziyacivan/reflex-router#typellm-backend-agreement
claim_cluster: github:ziyacivan/reflex-router#typellm-backend-agreement
feeds: ["memory", "decision"]
primary_source: https://github.com/ziyacivan/reflex-router/blob/0efe14f805b6a175f717aa73b33904ba768befcf/docs/observations.md
source_commit: 0efe14f805b6a175f717aa73b33904ba768befcf
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R7"]
tags: {"mechanism": ["model routing", "decision backend swap", "teacher agreement", "calibration head", "option permutation"], "workload": ["coding agent", "Claude Code"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: per-backend table with n, latency and errors in a dated observations file at a pinned commit", "control": "medium: same 500 tasks and same plan rule for every backend, plus an always-Sonnet reference, but the reference is Jev, not ground truth", "independence": "medium: single maintainer, one machine, one day; TypeLLM adapter written by the maintainer", "reproducibility": "medium: adapter pinned by a unit test and the commit is recorded, but the 500 labelled tasks live in a local ft/ file and TypeLLM is hosted", "applicability": "medium: coding-agent tier routing, close to our routing stage but synthetic English tasks"}
beliefs_affected: {"supports": ["B13", "B14"], "contradicts": [], "would_create": ["A coarse routing decision learned against Jev can be reproduced by another hosted typed-decision API without a calibration head (93% plan agreement) but not by local Laya with a fitted head (48 to 58%), so open-weight substitution needs per-stage measurement"]}
claim_correction: none (the post states the same numbers and caveats; the observations file adds that 21 HTTP 502s occurred in run A and that option permutations moved a quarter of plans to dearer tiers)
memory_stage: routing
priority: 1
---

# reflex-router 0.9.0: TypeLLM as a decision backend agrees with Jev (TypeSafe) on 93% of 500 routing tasks; Laya with its calibration head agrees on 58%

- **URL:** https://github.com/ziyacivan/reflex-router (docs/observations.md section "2026-09-30 - TypeLLM as a decision backend", CHANGELOG.md "0.9.0 - 2026-09-30")
- **Type:** repo
- **Author / org:** ziyacivan (single maintainer); npm package `reflex-router`
- **Date:** release 0.9.0, 2026-09-30; HEAD 0efe14f805b6a175f717aa73b33904ba768befcf (2026-09-30 15:43:02 +0300, "test: read only complete lines of a decisions.jsonl still being written")
- **Retrieved:** 2026-10-01 (local shallow clone: repos/reflex-router). Read: README.md, CHANGELOG.md, docs/observations.md lines 813 to 851. Code not executed. The repo also contains a CLAUDE.md written for coding agents; it was read as evidence only.
- **Cited by evidence:** @ziyacivan, 2026-09-30, https://x.com/ziyacivan/status/2105272414405800151
- **Relevance to a memory stack:** high for priority 1 and 2. It is the first public measurement of swapping the decision backend under a fixed policy, with hosted Jev as teacher, a second hosted typed-decision API, and an open-weight model (Laya) side by side.
- **What is new relative to the existing bus note** (N-20260926-11, `github:ziyacivan/reflex-router`, which describes the router and its Jev decision): a third backend (TypeLLM), a same-task agreement table across Jev, TypeLLM and Laya, latency and error counts per backend, and an option-permutation result.

## TL;DR
- reflex routes each Claude Code task to the cheapest adequate model tier with one typed question per start of work. 0.9.0 adds TypeLLM (`REFLEX_BACKEND=typellm`) next to Jev (default) and local Laya.
- On 500 synthetic pilot tasks labelled earlier by `jev-1.13.0`, TypeLLM raw (no calibration head) produced the same routing plan as Jev on 93.3% (n=479 after errors), cheaper than Jev on 0.4%, dearer on 6.3%. Laya `english` with the shipped head: 58.2%; Laya with a head refitted on these tasks: 48.2%; always-Sonnet: 41.0%.
- Agreement with Jev is not routing accuracy. The maintainer: "Jev is the teacher here, not ground truth, and Jev's own repeat agreement on this set was not measured, so 93% may be near the ceiling." The agreement is "high enough to suggest a closely related model rather than an independent judge; that is not known."
- Asking the tier question over option permutations changed the argmax on 22/473 tasks but moved a quarter of plans (agreement 74.9%) toward dearer tiers: the plain answer leans cheap when options are listed cheapest first, and Jev's labels lean the same way.
- Latency from one machine: TypeLLM p50/p95 382/464 ms (server 183/226); Jev in the owner's real sessions p50/p95 353/792 ms; Laya on M4 CPU 839/1,589 ms. 21 HTTP 502s in one ~45-call window. Whole test $0.063.

## What it claims / describes
reflex runs `claude` behind a loopback proxy; at the start of each piece of work a decision backend judges the reasoning tier the task needs, and a plan rule (`mass` eps 0.10 with Opus requested) maps the answer distribution to a model. Backends share one keep-alive transport (`src/backend/http-client.ts`). The README rule: "A new backend is added only as another value of `REFLEX_BACKEND`, with its measurement against Jev in `docs/observations.md`."

TypeLLM adapter (`src/backend/typellm.ts`, pinned by `test/unit/typellm.test.ts`): "a `choice` question becomes a string enum with the criteria flattened into `instructions`, a `score` becomes an enum `"0".."4"` whose expected value is the score, a `noul` becomes a boolean. The context is the decision state as JSON." Endpoint `POST https://api.typellm.ai/v1/generate`, model `typellm-latest`, `return_probabilities` on enum and boolean fields, deadline 1,500 ms.

Three TypeLLM runs: A, the product's two questions one at a time; B, those plus seven `lf-1` feature questions; C, as A with `permutations` on the tier question, four at a time. Laya `english` (default checkpoint, shipped head `cal-*`) on the same 500 tasks on the same machine (M4, CPU). Cost cap $1; spent $0.063 (1.26M input tokens, TypeLLM list price $0.05/M).

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| plan agreement with Jev, TypeLLM raw, 2 questions (A) | 93.3% | always Sonnet 41.0% | 500 synthetic tasks, n=479 scored | Jev is the reference, not truth |
| cheaper / dearer than Jev (A) | 0.4% / 6.3% | always Sonnet 35.0% / 24.0% | same | |
| Jev-haiku tasks sent to haiku (A) | 103/120 | Laya shipped head 6/120 | same | |
| cross-entropy vs Jev (A) | 0.44 | Laya shipped head 0.92 | same | |
| TypeLLM raw, 9 questions (B) | 93.4% agree, 0.2% cheaper, 6.4% dearer | A | same | extra feature questions add nothing raw |
| TypeLLM + head, cross-validated (B) | 94.6% agree, 1.2% cheaper, 4.2% dearer, 111/120, CE 0.39 | B raw | same | |
| TypeLLM tier permutations (C) | 74.9% agree, 0 cheaper, 25.1% dearer, 82/118 | A | n=494 | argmax changed on 22/473; all moves toward dearer |
| Laya `english` + shipped head | 58.2% agree, 4.4% cheaper, 37.4% dearer, 6/120, CE 0.92 | Jev | same 500, M4 CPU | |
| Laya + head refitted here, cross-validated | 48.2%, 1.2% cheaper, 50.6% dearer, 1/120, CE 0.82 | Jev | same | refit made agreement worse |
| latency TypeLLM A, client p50/p95 | 382 / 464 ms (server elapsed 183 / 226) | Jev real sessions 353 / 792 ms (1,315 decisions, keep-alive); Laya 839 / 1,589 ms | one machine, fresh fetch per call | different clients and workloads across rows |
| errors | 21 x HTTP 502 in A within one ~45-call window; 6 x 429 in C at 4 concurrent | n/a | | documented limit 100 requests/min plus a concurrency cap |
| cost of the test | $0.063 | n/a | 1.26M input tokens | list price |
| earlier: shipped Laya head on 190 real prompts | moved 24 turns off Opus (Jev moved about half of them); 1.6% of plans cheaper than Jev's | Jev | README line 71 | earlier measurement (2026-09-23) |

## Mechanism details you could implement
- **Backend swap protocol:** fix the policy (questions, plan rule, thresholds), replay a labelled task set through each candidate backend, and report agreement with the incumbent, cheaper-than and dearer-than rates separately (they carry different costs), a per-class recall on the cheap class (Jev-haiku sent to haiku), and cross-entropy to the incumbent's distribution.
- **Translation layer:** map choice -> string enum with criteria in instructions; score -> enum "0".."4" with expected value; noul -> boolean; context = decision state as JSON. This is enough to put a generic typed-output API behind a System One interface.
- **Permutation check:** ask the same choice with options permuted and average; any large shift reveals an option-order bias in the backend and in the teacher's labels.
- **Calibration head for a weaker local model:** fit a head on local-model features to reproduce the teacher's decisions with a safety margin toward the expensive tier (here it still matched only 48 to 58%).
- **Privacy rules worth copying:** backend keys never reach another backend; a key pasted into a prompt is redacted before state leaves the machine; outcome logs hold hashes and counts only.

## Limitations, caveats, counter-evidence
- Stated: synthetic English tasks, one machine, one day, a thin adapter written by the maintainer, no real prompts sent; Jev's own repeat agreement unmeasured; real-traffic 502 frequency unknown.
- Agreement with a teacher rewards imitation of the teacher's biases (the permutation result shows Jev's labels lean cheap with cheapest-first options). It says nothing about whether the routed tier was adequate for the task.
- The README's own calibration read on 1,525 real decisions cannot distinguish routing rules (correction rate 4.3% [0.8, 21.0] vs 0.0% [0.0, 15.5], Wilson 95%), and the arms are not randomised; it estimates about 430 disagreement windows per arm (around 2,000 decided main turns) to separate 5% from 10%.
- Latency rows are not comparable (different clients, keep-alive vs fresh fetch, real vs synthetic workloads).
- Inference: 93% raw agreement plus the maintainer's remark make it plausible TypeLLM is distilled from or close to Jev; if so, TypeLLM is not an independent second opinion and should not be used as a judge of Jev.

## Takeaways for tuning a memory stack
- Before swapping Jev for an open-weight model at any memory stage, run the same fixed-policy replay and report cheaper/dearer (or for gates: false-admit/false-reject) separately. A 58% agreement on a coarse 3-tier question is a warning for finer stages like linking.
- A hosted alternative with near-identical behaviour exists for routing; that reduces vendor lock-in for routing but not for keeping memory text in-house (priority 2), since TypeLLM is hosted too (self-hosted `REFLEX_TYPELLM_BASE_URL` "works in principle, untested").
- Always include an option-permutation run; the order of options in our questions can move a quarter of decisions.
- Budget for teacher noise: measure the incumbent's own repeat agreement before reading any agreement number.

## Open questions
- What is Jev's test-retest agreement on the same 500 tasks?
- Does TypeLLM agree with Jev as closely on non-routing questions (save/skip, supersedes, staleness)?
- Is TypeLLM self-hostable in practice, and what are its weights' provenance and licence?

## Grading and labels
- **Directness: high.** Dated observation with table, n, errors, latency and cost at a pinned commit.
- **Control: medium.** Same tasks and plan rule across backends; always-Sonnet reference; cross-validated heads; but the yardstick is the incumbent model, not outcomes.
- **Independence: medium.** One maintainer, one machine; TypeLLM may be related to Jev; the maintainer also wrote the adapter.
- **Reproducibility: medium.** Commit and adapter test pinned; task file `ft/labelled.jsonl` is local; hosted APIs change.
- **Applicability: medium.** Routing stage of a coding agent; synthetic tasks.
- **Pillars:** R9 primary (which System One implementation at the routing stage); R4 secondary (error asymmetry, calibration head); R7 secondary (backend swap test). **Memory stage:** routing. **Priority:** 1 (also 2: open-weight comparison).
- **Beliefs:** supports B13 (a stronger or different backend is not automatically better; measure on the borderline population: refitting Laya's head lowered agreement 58.2% to 48.2%); supports B14 (fit thresholds locally: the shipped head is conservative, 37.4% dearer). Would create the routing-substitution belief in the frontmatter.
- **Contradictions:** none.

## Origin chain
Post @ziyacivan 2105272414405800151 (2026-09-30) -> github:ziyacivan/reflex-router at 0efe14f -> CHANGELOG.md "0.9.0 - 2026-09-30"; docs/observations.md lines 813 to 851 (setup, results table, latency, errors, interpretation); README.md lines 61 to 71 and 218 -> this note. Independence: single author; teacher labels from TypeSafe Jev 1.13.0; Laya is NandhaKishorM/laya with reflex's own head; TypeLLM relationship to Jev unknown. Related bus notes: N-20260926-11 (reflex-router), N-20260926-09 (TypeLLM fair-die permutation averaging).

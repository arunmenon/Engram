---
schema_version: 1
artifact_id: N-20261008-01
artifact_type: note
producer: triage
run_id: triage-20261008T014615Z-49b5
created_at: 2026-10-08T01:54:13Z
input_refs: [{"artifact_id": "post:2105225030544093522", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:tomerglick57/Jevstiller
claim_cluster: github:tomerglick57/Jevstiller
feeds: ["memory", "decision"]
primary_source: https://github.com/tomerglick57/Jevstiller
source_commit: f5f52e79fb7938d3a45ac035099722f82db4a3b3
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R4", "R6"]
memory_stage: routing
priority: 2
tags: {"mechanism": ["distillation", "cascade", "conformal-style threshold", "clopper-pearson bound", "knn ood gate", "audit channel"], "workload": ["repeated classification", "intent routing"], "lifecycle_stage": ["routing"], "cross_cutting": ["cost", "self-host"]}
evidence_grade: {"directness": "high: tables and a deterministic replay script in the repo", "control": "high: four threshold rules on identical 20 splits per task, plus oracle-teacher upper bound", "independence": "low: single author, public classification datasets, no third-party replication", "reproducibility": "high: pinned commit, Jev answers for Banking77 shipped, seeded split, reproduce.sh", "applicability": "medium: intent and topic tasks, not memory decisions over long structured state"}
beliefs_affected: {"supports": ["B14", "B13"], "contradicts": [], "would_create": ["A local student distilled from Jev answers about 70% of a repeated many-class decision within a 2% disagreement budget, but only about a quarter of noisy tasks; coverage tracks Jev's own consistency"]}
claim_correction: Post calls it a guarantee broken once per 100 splits; the repo states a 95%-confidence Clopper-Pearson bound, so rare exceedance (1/100) is within design, and it is the point-estimate rule that fails (6 to 12 of 20 splits per task).
---

# Jevstiller: distilling a repeated Jev (TypeSafe) decision into a local model under an agreement budget

- **URL:** https://github.com/tomerglick57/Jevstiller
- **Type:** repo
- **Author / org:** tomerglick57 (GitHub); not stated whether affiliated with TypeSafe
- **Date:** HEAD commit f5f52e79fb7938d3a45ac035099722f82db4a3b3, 2026-10-05 15:35:06 +0300, "Docs: coverage of Jev's API, item by item; current rate limits (#23)"
- **Retrieved:** 2026-10-08 (shallow clone at repos/Jevstiller). Read: README.md, experiments/README.md, docs/benchmarks.md. Not executed.
- **Cited by evidence:** @abeauvois, https://x.com/abeauvois/status/2105225030544093522 (2026-09-30, commentary, names no repo; repo located by GitHub search on the name)
- **Relevance to a memory stack:** high. Any memory stage that asks Jev the same typed question at volume (write gate, recall gate, routing) could be served locally under a measurable agreement contract, keeping memory text in-house (priority 2).

## TL;DR
- A proxy in front of a repeated Jev classification call: it trains a frozen-encoder plus logistic head on Jev's full probability distributions, adds a kNN out-of-distribution gate, and answers locally only when a threshold chosen with an exact finite-sample (Clopper-Pearson) bound keeps "answered locally and different from Jev" under the budget (target 98% agreement means 2% of all requests) at 95% confidence. A permanent 2% audit slice keeps going to Jev; if the audit shows the contract broken, everything falls back to Jev.
- Five public tasks, bge-small on CPU, target 98%: held-out coverage 71.9% (Banking77), 69.0% (CLINC150), 80.2% (AG News), 22.2% (TweetEval sentiment), 24.1% (TweetEval offensive), agreement with Jev 98.70% to 99.65%, system accuracy equal to Jev's within 0.4 points (README results table).
- Controlled comparison: the bound rule exceeded the 2% budget on 1 of 100 splits; the usual point-estimate rule exceeded it on 6 to 12 of 20 splits per task, at four to eight points more coverage (docs/benchmarks.md "Threshold rules on the same data").
- Claim correction vs the post: the post frames 1/100 exceedance as an imperfect guarantee; the bound is stated at 95% confidence, so that rate is within design (inference), and the post omits the point-estimate comparison that is the repo's actual finding.
- Agreement with Jev is not accuracy: the repo says so next to every number.

## What it claims / describes
Flow (README): services call Jevstiller instead of Jev. At first every request goes to Jev; Jev's answer and full distribution become a training row. A candidate student is trained "in seconds", shadowed on live traffic, and promoted if it stays within the budget. Confident, in-distribution input is answered locally (~15 ms CPU p50, "about 20x faster than Jev"); uncertain, novel (kNN OOD) or audited input goes to Jev. Motivation quoted: Jev is "~300 ms away, per answer, at every load we tried (16 to 64 concurrent callers, up to 190 requests/s, p50 300 ms)", hosted, under rate limits "80 requests and 100,000 tokens a second as of October 2026".

Contract (README "The contract"): "The routing threshold is chosen on a held-out, IID calibration set so that, with 95% confidence, the share of requests the local model answers *and* gets different from Jev stays within the budget. It uses an exact finite-sample bound (Clopper-Pearson), testing candidate thresholds strictest-first." A `confidence_floor` option extends the bound to callers that act on Jev's confidence.

## Numbers

| Metric | Value | Baseline | Setup (n) | Caveat |
|---|---|---|---|---|
| Held-out answered locally, Banking77 | 71.9% at 99.50% agreement | Jev alone, accuracy 78.5% vs system 78.5% | bge-small CPU, target 98%, 2,000 held-out rows, 11,083 streamed (README table) | replay of Jev answers recorded 2026-09-24 (jev-1.13.0) |
| Live run, Banking77 | 70.7% at 99.45% | same | live Jev, 2026-09-25 (README) | one run |
| CLINC150 | 69.0% at 99.65%, acc 90.1%/90.1% | Jev | 12k sample, rare_classes defer | |
| AG News | 80.2% at 99.40%, acc 88.7%/88.7% | Jev | 20k sample | |
| TweetEval sentiment | 22.2% at 98.70%, acc 64.2%/64.5% | Jev | | Jev agrees with labels only 64% |
| TweetEval offensive | 24.1% at 98.80%, acc 73.8%/74.2% | Jev | | |
| Budget violations, bound rule | 1/100 splits (TweetEval sentiment, 2.10%) | point estimate: 9/20, 12/20, 11/20, 8/20, 6/20 (soft labels) | 20 random splits per task (docs/benchmarks.md) | coverage cost 4 to 8 points |
| Banking77, bound vs point estimate | 74.9% coverage, mean disagreement 1.15%, 0/20 violations | point estimate 79.8%, 1.90%, worst 2.70%, 9/20 | docs/benchmarks.md lines 28 to 30 | |
| Target curve, Banking77 | 54% @ 99%, 72% @ 98%, 84% @ 95%, 93% @ 90% | | target_curve.py | system accuracy 78.5% to 78.8% across targets |
| Target curve, TweetEval sentiment | 8% @ 99%, 18% @ 98%, 32% @ 95%, 48% @ 90% | | | |
| Confidence floor | without floor caller outcome broke budget 20/25 splits at 0.6, 25/25 at 0.8; with floor 0/50 | | confidence_floor.py, 5 splits per task | |
| Oracle teacher upper bound, Banking77 | base encoder 70.9% coverage at 99.55% | small 56.2%, large 59.8% | experiments/README.md | dry run, labels as teacher |
| Live session audit | 97.5% on 161 audited, 95% CI [94.4%, 99.1%] vs 98% target | | 15,000 requests, four student versions (docs/benchmarks.md line 174) | "Inconclusive, not broken" |
| Soak | 3.6 million requests, 0.012% errors, silent Jev change at hour 12 recovered | | README | details in docs |

## Mechanism details you could implement
- Student: frozen sentence encoder (bge-small/base/large or hash) plus logistic head trained on Jev's probability vector (soft labels; soft buys "two to three points of coverage on the many-class tasks").
- OOD gate: kNN against a reference set (`--ood-max-ref`, default 5,000).
- Threshold: Clopper-Pearson upper bound on joint "answered and disagree" rate over all requests at 95% confidence, fixed-sequence testing strictest-first; refit with headroom on a fixed grid.
- Audit: random 2% of traffic always to Jev; auto-fallback when the audit breaks the contract. Status line format: "Agreement with teacher (audit, n=415): 99.40% [98.46%, 99.84%] target 98% OK".
- Dial: `jevstiller admin target <task> 0.95` moves along the coverage curve.

## Limitations, caveats, counter-evidence
- Agreement with Jev, not accuracy: if Jev is wrong the student is wrong the same way (README, DESIGN.md section 2).
- Tasks are short-text classification; nothing on long structured state, multi-question Jev calls (nouls plus choice) or memory decisions (inference: our write gate sends multi-turn state and several questions).
- Single author, own harness; no independent replication. The X post author (@abeauvois) is a commentator, not the repo author.
- Coverage depends on split by "a few points" (66.8% to 70.7% on four earlier replays).
- The late live audit (97.5%, interval straddling 98%) shows the contract can sit near the edge in production.

## Takeaways for tuning a memory stack
- If a memory stage asks Jev one repeated typed question, a local student could answer most of it under a stated agreement budget; measure coverage on our own decisions before assuming savings.
- Use a finite-sample bound, not a point estimate, when picking any local threshold; the point estimate broke a 2% budget on roughly half of splits here.
- If downstream code thresholds Jev's confidence, the bound must include that (confidence floor), or the caller's outcome drifts even when labels agree.

## Open questions
- Coverage on multi-question, long-state memory decisions (write gate, linking)?
- Does agreement survive Jev version upgrades without a full retrain (soak suggests recovery, mechanism not read)?

## Grading and labels
- Directness high (tables, replay script); control high (four rules on identical splits); independence low (single author); reproducibility high (pinned commit, shipped answers, seeded); applicability medium (classification, not memory state).
- Pillar R9 primary (open-weight / self-hosted stand-in for Jev), R4 and R6 secondary. Memory stage: routing. Priority 2.
- B14 supports: vendor confidence is not used as is; thresholds are fitted locally with a bound. B13 supports (weakly): escalation only on the uncertain population, evaluated against a budget. Would create: the coverage-versus-consistency belief in frontmatter.
- No contradiction rows.

## Origin chain
post x:2105225030544093522 (@abeauvois, no link) -> GitHub search "jevstiller" (one result) -> github.com/tomerglick57/Jevstiller at f5f52e7 -> README results table, docs/benchmarks.md threshold-rule table and target curve -> this note. Independence: datasets are public (Banking77, CLINC150, AG News, TweetEval); teacher is Jev 1.13.0; the repo compares itself with stuntd (bladedevoff/stuntd), not read. The repo match to the post is by name and described mechanism (inference, strong).

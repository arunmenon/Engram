---
schema_version: 1
artifact_id: N-20260930-01
artifact_type: note
producer: triage
run_id: triage-20260930T014506Z-8351
created_at: 2026-09-30T01:57:27Z
input_refs: [{"artifact_id": "post:2105089993865904638", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:gazelle93/decision-models-under-pressure
claim_cluster: github:gazelle93/decision-models-under-pressure
feeds: ["decision"]
primary_source: https://github.com/gazelle93/decision-models-under-pressure
source_commit: 21820dc8b455e37aebaf5a83122233b6e564c109
strength: repo-pinned
pillar_primary: R9
pillar_secondary: ["R1", "R4", "R6"]
tags: {"mechanism": ["listwise choice over candidates", "order sensitivity", "repeat-call nondeterminism", "calibration vs list size"], "workload": ["intent routing", "topic and emotion classification"], "lifecycle_stage": ["reranking", "routing", "linking"], "cross_cutting": ["cost"]}
memory_stage: reranking
priority: 2
evidence_grade: {"directness": "high: the repo measures the decision call itself on 1,000 items with published aggregates", "control": "high: preregistered plan, paired near/far distractor tiers, fixed-order determinism control, text-blind leakage gates", "independence": "high: independent author, no vendor affiliation stated, public datasets", "reproducibility": "high: pinned commit, frozen dataset with SHA-256 per item, harness code readable (no licence), Jev arm cost $1.04", "applicability": "medium: short classification texts, not engineering artifacts; the order and repeat effects transfer to any choice-over-candidates stage (inference)"}
beliefs_affected: {"supports": ["B14", "B13"], "contradicts": [], "would_create": ["Jev choice answers over candidate lists change with option order (14.6% at K=64) and between identical calls (4.3%), so replay of a Jev rerank or link decision needs the stored answer, not a re-call"]}
claim_correction: The post says Jev held up best and flips on 1 decision in 7 under shuffling; the repo adds that 4.3 of those 14.6 points are Jev disagreeing with itself at fixed order, that Jev calibration could not be measured (2-decimal rounding), and that the Jev arm was not preregistered.
---

# Decision Models Under Pressure: Jev (TypeSafe) vs Laya and five open scorers as lists grow, options reorder and distractors get plausible (gazelle93)

- **URL:** https://github.com/gazelle93/decision-models-under-pressure
- **Type:** repo (evaluation harness, frozen dataset, published aggregates)
- **Author / org:** gazelle93 (individual; no organisation stated). Dataset CC BY-SA 4.0; code has no licence ("you may read it but not reuse it").
- **Date:** commit read `21820dc8b455e37aebaf5a83122233b6e564c109` (2026-09-25 10:44:54 -0400, "Add the determinism control: 10 of Jev's 14.6 flip points are the order"). PLAN.md written 2026-09-23.
- **Retrieved:** 2026-09-30 (local copy: repos/decision-models-under-pressure, shallow clone). Read: README.md, PLAN.md (first 80 lines). Code not executed.
- **Cited by evidence:** decision feed 2026-09-30, @waynerad (https://x.com/waynerad/status/2105089993865904638), quoting the README's opening paragraph.
- **Relevance to a memory stack:** high. Any stage where a System One model picks one item from a candidate list (rerank, link target, route) inherits these three failure axes: list length, near-miss options, and order plus repeat-call instability.

## TL;DR
- Seven systems (TypeSafe Jev, Laya, gliclass-large-v3.0, deberta-v3-base/large zeroshot, bge-large-en-v1.5, gte-large) take text + question + candidate list and return a distribution. n = 200 items per domain, 1,000 items, 5 domains, preregistered pass/fail rules.
- Jev degrades least: 60% at 128 candidates vs Laya 39% and best open 41%; -0.043 accuracy per doubling (shallowest of seven); near-miss distractors at K=64 cost Jev 96.8% to 86.3% vs Laya 90.5% to 56.0%.
- But Jev is neither order-invariant nor deterministic: reordering alone changes 14.6% of answers at K=64; with order held fixed it still changes 4.3% across five identical calls (gap +10.2 points, 95% CI [+8.6, +11.9]). Laya is exactly reproducible (0.0% fixed order) but flips 49.4% under reordering.
- Jev calibration is unmeasurable from outside: the API rounds probabilities to two decimals; "98% of its responses contain at least one option at exactly 0.00". Laya is best calibrated at K=2 (ECE 0.032) and worst at K=256 (0.573).
- Claim correction: the post's "1 in 7" is mostly order (about 10 of 14.6 points); the other 4.3 points no canonical ordering can remove. The Jev arm and the determinism control were both added after the preregistration (disclosed).

## What it claims / describes
**Job measured.** Text + a question + K candidate labels in, a probability over the candidates out. Three production stressors, one research question each (PLAN.md):
- RQ1 cardinality x text length: domains clinc, mtop, goemotions, dbpedia; K in {2,4,8,16,32,64,128,256}; Jev capped at 128 because "Jev's API refuses more than 255 options".
- RQ2 order sensitivity: domains clinc, goemotions, fintopic, mtop; near and far tiers; K in {16, 64}; 5 permutations per item. Criterion C1: claim "residual order tax under 5%" only if the 95% bootstrap CI upper bound on flip rate is below 0.05. Amendment 2026-09-25 (post hoc, disclosed): determinism control at K=64, same item/order, five calls.
- RQ3 distractor hardness: clinc and mtop, paired near/far tiers, K in {2..64}. Near tier = the gold label's nearest neighbours ("create alarm" vs "delete alarm", "snooze alarm"), surface shape matched to far tier.

**How each reads candidates** (README table): Jev "undisclosed, but its answers depend on the order, so not one at a time"; Laya and gliclass read all candidates as a set in one pass; deberta cross-encoders score one candidate at a time; bge/gte embed the text once and compare to cached candidate vectors. The author's summary: a model that reads candidates as a set can notice two similar candidates but gets order sensitivity with it.

**Dataset checks.** Eight assertions run before any model: no option string in the prompt wording; surface features must not separate near from far distractors; a text-blind classifier must stay under twice chance; gold position depends on the item; near tier measurably nearer; every item usable in both tiers at every K; no adjudicated ambiguous pair together; well-formed option sets. Seven of eight pass. The text-blind gate fails on some cells: "0.260 on DBpedia against a chance rate of 0.0625 and a 0.125 gate", which "inflates the level of the curves without changing their shape". Two preregistered rules fired against the author (a voided family comparison, and two of four order-invariant models not scoring exactly zero, traced to ties).

## Numbers
| metric | value | baseline / comparison | setup (n) | caveat |
|---|---|---|---|---|
| accuracy at 128 candidates | Jev **60%** | Laya 39%, best open 41%; chance 0.8% | RQ1, 200 items/domain | DBpedia level inflated by label-format leakage (0.260 text-blind) |
| accuracy lost per doubling of list | Jev **-0.043** | gte -0.048, bge -0.051, gliclass -0.064, deberta-large -0.070, deberta-base -0.070, Laya -0.073 | K=2 to 128 | README table "accuracy lost per doubling" |
| near-miss distractors, K=64 | Jev 96.8% to 86.3% | Laya 90.5% to 56.0%; gliclass 87.0% to 51.2% | RQ3, clinc + mtop | two domains only, both plausibly seen in training |
| accuracy lost when distractors get hard | Jev **-0.105** | Laya -0.351, best open -0.256 | summary table | |
| answers changed by reordering, K=64 | Jev 14.6% | Laya 49.4%; bge-large and deberta-large 0.0000 over 1,600 decisions each; deberta-base 0.2%; gte-large 2.0% (exact ties) | RQ2, 5 permutations | K=16 flip rates still include unmeasured noise |
| answers changed with order fixed, K=64 | Jev **4.3%** | Laya 0.0% (3,200 items, 16,000 calls) | n=1600, 8,000 calls, `results/published/rq2_determinism.json` | post hoc amendment |
| order effect on Jev (gap) | +10.2 points | 95% CI [+8.6, +11.9] | K=64 | of 248 items flipping under either arm: 179 only shuffled, 15 only fixed, 54 both |
| Jev flips by domain (unrelated / near distractors) | clinc 1.5% / 9.0%; mtop 3.0% / 12.5%; fintopic 5.0% / 22.0%; goemotions 30.5% / 33.0% | | RQ2 | "Intent routing with plausible competing options ... runs four to six times worse" |
| calibration error K=2 / K=256 | Laya 0.032 / **0.573**; gliclass 0.150 / 0.327; gte 0.048 / 0.299; bge 0.099 / 0.197; deberta-base 0.066 / 0.075; deberta-large 0.064 / 0.070 | Jev not measurable | | Jev probabilities rounded to 0.01 |
| Jev arm cost | $1.04 for 29,600 calls | | via OpenRouter | |

## Mechanism details you could implement
- **Canonical option order.** Present candidates in a fixed canonical order (for example sorted by id). On Jev this removes about 10 of 14.6 flip points at K=64; on Laya it buys exact reproducibility.
- **Permutation majority vote.** Ask under several orderings and take the majority; "costs several calls per decision and is the only one of the two that helps with a model that will not repeat itself".
- **Measure two properties separately:** order sensitivity (fixed by sorting) and repeat-call determinism (not fixed by sorting). Laya is reproducible and order sensitive; Jev is the reverse.
- **Evaluate at your real K and with near-miss candidates**, not a single accuracy at one list size: at K=2 Laya trails Jev by two points, at K=128 by twenty-two.
- **Gate the dataset before the model:** a text-blind classifier baseline (must stay under 2x chance), surface-matched near/far tiers, gold position independent of label.
- Jev request limits observed: at most 255 options per choice question.

## Limitations, caveats, counter-evidence
- Jev's training data is undisclosed; "trained better" and "has seen these before" cannot be separated. Jev is steadiest on intent-style domains a decision product would plausibly be trained on.
- Jev comparison and the determinism control were not in the preregistration (disclosed in README and PLAN.md).
- n = 200 per domain: enough for the large effects, "not enough for anything subtle". Near-distractor comparison rests on two domains.
- Short texts (clinc/mtop about 34 to 38 chars); DBpedia supplies length. Nothing resembling design docs, PRs or tickets (inference: applicability to PDLC artifacts is untested).
- Calibration table excludes Jev; this note cannot say whether Jev is calibrated.
- Counter-evidence in our catalogue: `github-djev-deterministic-jev-server.md` (bus N-20260929) targets exactly the repeat-call gap with a self-hosted deterministic server; `blog-typellm-fair-die-permutation-averaging.md` already proposes permutation averaging.

## Takeaways for tuning a memory stack
- If a Jev choice call picks the rerank winner or the link target, store the returned answer and the option order in the receipt; do not rely on re-calling Jev to reproduce the decision (4.3% of answers change at fixed order, K=64).
- Sort candidates canonically before every choice call; it is free and removes most of the order effect.
- Keep candidate lists short where possible and include near-miss distractors in your own evaluation set; accuracy falls about 4 points per doubling even for the best model.
- Do not transfer a confidence threshold fitted at small K to large K for open models: Laya's calibration error rises from 0.032 to 0.573.

## Open questions
- What are Jev's order and repeat-call rates on long engineering texts (tickets, design sections) and at the K we use for linking (tens of candidates)?
- Does the 4.3% repeat-call rate vary with Jev version or with the OpenRouter path vs the direct TypeSafe API? Not stated.
- Does a 3-permutation majority close the gap to single-call accuracy at acceptable cost? Not measured here.

## Grading and labels
- Directness high: the stage we care about (choice over candidates) is the thing measured. Control high: preregistered rules, paired tiers, determinism control. Independence high: independent author and public datasets. Reproducibility high: pinned commit, frozen data with per-item hashes. Applicability medium: classification texts, not engineering artifacts.
- Pillars: R9 primary (which System One model at which stage), R1 (replay), R4 (calibration and abstention thresholds), R6 (evaluation protocol). Memory stage: reranking (also routing, linking). Priority 2 (Jev vs open-weight Laya on quality and stability).
- Beliefs: supports B14 (vendor calibration claimed, not shown: the API's two-decimal rounding makes calibration unmeasurable from outside). Supports B13 in spirit (evaluate on the borderline population: near-miss distractors change rankings sharply). Would create: repeat-call and order instability of Jev choice answers means replay needs the stored answer.
- Contradiction rows: none against a held belief. Relation to B10 (single listwise choice beat per-item yes/no in Hindsight): not contradicted, but B10's listwise design inherits the 14.6% order effect measured here (inference).

## Origin chain
@waynerad post (2105089993865904638) -> github.com/gazelle93/decision-models-under-pressure at 21820dc -> README.md tables ("at 64 to 128 candidates", "accuracy lost per doubling", determinism table, calibration table) and PLAN.md RQ2 amendment -> this note. Independence: no shared authors with TypeSafe or Laya; uses public CLINC-150, MTOP, GoEmotions, DBpedia, Twitter Financial News datasets, the same public sources vendors may train on.

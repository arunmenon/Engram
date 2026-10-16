---
schema_version: 1
artifact_id: N-20260927-02
artifact_type: note
producer: triage
run_id: triage-20260927T022129Z-c62e
created_at: 2026-09-27T02:34:39Z
input_refs: [{"artifact_id": "post:2103837615896293826", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.29144
claim_cluster: arxiv:2609.29144
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.29144
source_commit: n/a
strength: paper-ablated
pillar_primary: R2
pillar_secondary: ["R5", "R6"]
tags: {"mechanism": ["write gate", "family-scoped memory slots", "multi-channel verification gate (ORC)", "persistent skill policy edits"], "workload": ["code repair", "ProcStream-RSI"], "lifecycle_stage": ["write", "promotion", "read"], "cross_cutting": ["cost"]}
evidence_grade: {"directness": "high: same proposals and same gate decisions, only the scope of the accepted memory differs", "control": "high: paired design, 8 main streams plus 27-stream extension, bootstrap 95% intervals, Holm-corrected sign-flip tests", "independence": "medium: independent researchers, Northwestern and Pinterest; benchmark built by the authors", "reproducibility": "medium: temperature 0, pinned seed per stream, endpoint named, total spend $6.9965; code link not seen in the text read", "applicability": "high: persistent learned rules for a coding agent, the same shape as lessons or procedural memory in our stack"}
beliefs_affected: {"supports": ["B16", "B25"], "contradicts": [], "would_create": ["A held-out execution gate on memory writes is necessary but not sufficient: an unscoped (global) accepted rule harmed later task families in 6 of 8 streams; scoping each rule to its origin task family removed the harm (0 of 8)"]}
claim_correction: none (post numbers 0.713 vs 0.816 and 6/8 vs 0 match Table 4; post omits that the static no-update baseline scored 0.775, above the global gated policy)
---

# Scope Before You Persist: Preventing Cross-Family Interference in Agent Memory (arXiv 2609.29144)

- **URL:** https://arxiv.org/abs/2609.29144 (full text read at https://arxiv.org/html/2609.29144)
- **Type:** paper
- **Author / org:** Yezhou Cheng, Runjia Du, Zeming Liu, Qibai Chen, Hang Lyu, Yilan Wei, Yankai Zeng, Bojun Lin; independent researchers, Northwestern University, Pinterest, Inc.
- **Date:** arXiv v1, 24 Sep 2026
- **Retrieved:** 2026-09-27, arXiv HTML v1
- **Cited by evidence:** @arkyyang https://x.com/arkyyang/status/2103837615896293826
- **Relevance to a memory stack:** high. It isolates the one variable every "lesson memory" design gets wrong silently: where an accepted rule applies. Same edits, same gate; only the retrieval scope changes, and harmful accepted updates go from 6 of 8 to 0 of 8.

## TL;DR
- Setup: a frozen coding model (Qwen3-Coder-Next) keeps a persistent 360-character natural-language skill policy; an editor proposes edits; a strict three-channel gate (ORC) decides deployment. 12 rounds, nine code-repair contract families.
- Global memory (one shared rule for all families) with the gate: mean trajectory utility 0.713, 6 of 8 accepted updates harmful. Family-scoped slots with the same proposals and gate: 0.816, 0 harmful. Static (no updates): 0.775, so the gated global memory did worse than never learning.
- 27-stream extension: scoped 0.848 [0.825, 0.871] vs global 0.785 [0.757, 0.812]; scoped accepted 63 updates with 0 harmful, global accepted 12 with 6 harmful.
- The authors prove (Proposition 1) and show empirically that an AND-of-channels gate cannot protect an unscoped edit from families it has not yet seen.
- Total experiment spend: $6.9965.

## What it claims / describes
- **Benchmark (ProcStream-RSI):** 12 rounds; each round has four discovery tasks and four probe tasks; nine task families listed as "boundary, rotation, ordering, normalization, boundary, rotation, nested, missing, prefix, chunk, tie-breaking, ordering" (verbatim; the list repeats names). 123 tasks per 12-round stream including checkpoint and final banks.
- **Memory:** a persistent 360-character natural-language skill policy used by the actor. The same model acts as editor proposing modifications.
- **ORC gate (Orthogonal Regression Control), Section 4, eqs 4 to 5:** deploy a candidate only if, on current-family probe tasks, the public-channel lower bound is >= -0.02, the private-channel (exact-output tests absent from the prompt) lower bound is > 0, the metamorphic-channel (answer-free property checks) lower bound is >= -0.02, AND every historical-family channel is >= -0.02 with no unsafe programs.
- **Variants:** Global-ORC deploys one shared skill affecting all families. Scoped-ORC stores accepted updates in family slots; retrieval (eq 3) is `K_t(f) = K_t^(f)` if the slot exists, else the initial skill `K_0`.
- **Model and decoding:** Qwen3-Coder-Next via OpenRouter Parasail BF16 endpoint, temperature 0, 700 actor tokens, 500 editor tokens, pinned seed per stream.
- **Metric:** mean trajectory utility MTU = (1/(T+1)) sum U_t over 13 deployment rounds on fixed checkpoint and final banks. Harmful acceptance = accepted update that reduces next checkpoint utility.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| mean trajectory utility, Scoped-ORC | 0.816 | Global-ORC 0.713; Static 0.775 | Table 4, 8 main streams, identical proposals and gate decisions | one model, nine families |
| harmful accepted updates | 0 of 8 (scoped) | 6 of 8 (global) | Table 4 | "harmful" = next checkpoint utility drops |
| MTU, 27-stream extension | 0.848 [0.825, 0.871] | global 0.785 [0.757, 0.812] | Table 6, bootstrap 95% CI | randomized-entry streams |
| accepted updates (27 streams) | 63, 0 harmful | global 12, 6 harmful | Table 6 | global accepts far fewer because the historical-family channels block more |
| streams with multiple acceptances | 19/27 scoped | 2/27 global | Table 6 | global memory stalls |
| external HumanEval+ / sealed banks (GPT-OSS-120B) | scoped 0.960 pass | Static 0.941 | 32-task HumanEval+ sample; 18-task sealed banks | small external check |
| total spend | $6.9965 | | Appendix F | main + external + extension |

## Mechanism details you could implement
- Tag every learned rule or lesson with the task family (or workload class) that produced it; at read time, serve a family's own accepted rule, otherwise fall back to the initial/base policy. Eq 3: `K_t(f) = K_t^(f) if slot exists, else K_0`.
- Gate with independent evidence channels, each with a lower-bound threshold: public examples (>= -0.02), private exact-output tests hidden from the prompt (> 0), metamorphic/property checks (>= -0.02), plus a regression check on every historical family (>= -0.02) and an unsafe-program check.
- Log "harmful acceptance" explicitly: after each accepted update, measure the next checkpoint; count accepted-then-harmful updates as a first-class metric.
- (inference) For our write-gate design, add a scope field to any durable lesson and make "global" promotion a separate, stricter decision.

## Limitations, caveats, counter-evidence
- Section 8: "The study covers inspectable scaffold edits with one frozen model and nine code-contract families. A cumulative one-shot control for compounding, open-world and wrong-slot routing, additional editor/search backbones, and automatically learned invariants remain future work."
- Family labels are given, not inferred; wrong-slot routing (assigning a new task to the wrong family) is untested, and in our workload family boundaries are fuzzy (inference).
- Actor and editor are the same model.
- Memory is a single 360-character policy per slot, much smaller than a real lesson store.
- Benchmark and gate designed by the same authors.

## Takeaways for tuning a memory stack
- A strict held-out gate on memory writes is not enough if accepted memories apply globally. Scope first, then gate.
- Measure a baseline that never updates; here the gated global memory lost to it (0.713 vs 0.775).
- Count harmful acceptances, not just acceptance rate.
- Expect scoped memory to accept far more updates safely (63 vs 12) because each update only has to be safe for its own family.

## Open questions
- How does scoping behave when the family of a new task must be predicted (wrong-slot routing)?
- Does a "promote to global only after N families pass" rule recover cross-family transfer without harm?
- Does the result hold with larger, multi-rule memories and different editor models?

## Grading and labels
- Directness high; control high (paired, same proposals and gate; CIs; corrected tests); independence medium; reproducibility medium; applicability high.
- Pillars: R2 primary (write/promotion semantics and scope of durable state); R5 secondary (learning from outcomes, harmful reinforcement); R6 secondary (gate as evaluation, harmful-acceptance metric).
- B16 supports (induced procedures are a hypothesis; here unscoped induced rules hurt).
- B25 supports weakly (a passed gate does not authorise global use).
- Would create: gate necessary but not sufficient; scope accepted memory to origin family.
- Contradiction (synthesis, not a held belief): synthesis section 1 recommends "Treat every memory or skill write as a proposal. It persists only if it beats the current best configuration on a held-out split" (EvoSkill row). This paper shows a held-out, multi-channel gate still let 6 of 8 harmful global updates through; the synthesis rule needs a scope condition. Open row: "Contradiction: synthesis section 1 gate-as-sufficient vs arXiv 2609.29144 Table 4".

## Origin chain
post 2103837615896293826 (@arkyyang, plain-language summary) -> arXiv 2609.29144 v1 HTML -> Section 3.1 Proposition 1, Section 4 eqs 3 to 5, Table 4 (8 streams), Table 6 (27 streams), Appendix F (cost), Section 8 (limitations) -> this note. Independence: no shared authors with EvoSkill or RRSI; the benchmark (ProcStream-RSI) is the authors' own.

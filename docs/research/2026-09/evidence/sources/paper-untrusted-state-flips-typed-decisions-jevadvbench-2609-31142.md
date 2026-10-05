---
schema_version: 1
artifact_id: N-SURVEY-20260928-09
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:10:00Z
idempotency_key: note:survey:arxiv:2609.31142
input_refs: []
pillar_primary: R9
pillar_secondary: [R8, R4]
memory_stage: linking
priority: 1
beliefs_affected:
  supports: [B14]
  contradicts: []
evidence:
  directness: 4
  control: 4
  independence: 4
  reproducibility: 4
  applicability: 4
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2609.31142
secondary_sources:
  - https://arxiv.org/abs/2609.30243
  - https://arxiv.org/abs/2609.28613
found_via: survey
claim_cluster: untrusted-state-text-flips-system-one-decisions
---

# JevAdvBench (with JevOut and Decision Hijacking): text inside the state flips System One decisions

- **URL:** https://arxiv.org/abs/2609.31142 (HTML read at https://arxiv.org/html/2609.31142). Cluster companions read in full: JevOut https://arxiv.org/abs/2609.30243 (code https://github.com/xzx34/JevOut), Decision Hijacking https://arxiv.org/abs/2609.28613
- **Type:** paper (three independent papers, one claim cluster)
- **Author / org:** not stated in the extracted text for JevAdvBench (project site https://JevAdvBench.github.io/JevAdvBench/); JevOut: xzx34 group; Decision Hijacking: not stated
- **Date:** 2026-09-25 (JevAdvBench), 2026-09-24 (JevOut), 2026-09-23 (Decision Hijacking)
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R9 question 3 (failure modes at memory stages)
- **Relevance to a memory stack:** high. Every memory-stage decision (link, supersede, still-true, recall) puts stored memory text into the `state`. These papers measure how much ordinary text in the state moves the decision.

## TL;DR
- JevAdvBench: on jev-1.13.0, "one unverified opinion appended to the state flips 12.1% of decisions" (excess over re-run floor "+11.1 pp [7.8, 14.4]"), statistically tied with the strongest injected command (10.1%). Rewording the question moves decisions only "+0.0 to +0.5 pp".
- The same opinion edit pushes "38.0% [31.1, 44.0]" of confident answers (>= 0.8) below 0.8, versus "0.5% under the re-run". A 0.8 confidence gate that routes to human review is therefore easy to move by ordinary text.
- JevOut: optimised, fluent context additions (median 31 added words) redirect Jev on 312 of 508 initially correct decisions (61.4%); open-weight systems are at least as fragile: OpenSourceJev (Qwen3-1.7B Q8) 72.6%, Von 1.0 (395M) 73.2%, plain Qwen scorer 64.9%.
- Decision Hijacking: classic prompt-injection strings rarely hijack a Jev action choice (1.8% of 510 InjecAgent cases; 3.5% with adaptive feedback). "Ignore all previous instructions" lowered the attacker probability. The threat is persuasive state content, not command-style injection.
- None of the three papers tests a defence.

## What it claims / describes
JevAdvBench scores each attacked decision against the model's own clean decision (not against labels) and reads it against the change caused by an identical re-run. 812 typed questions (314 Noul, 337 Choice, 161 Score) over 66 scenarios; 9,744 single-edit variants, each editing one part of the request: question text (rewording, paraphrase, unrelated sentences), state (appended opinions, analogies, unrelated notes), instruction or criteria fields (injected commands, authority impersonation), and structure controls (out-of-schema fields). Billed input tokens confirm the edit reached the model. "Fields outside the schema never reach the model."

JevOut fixes one wrong target option per initially correct item and lets a proposer (Gemma 4 12B) refine fluent context additions using the target model's option probabilities, with the source, question, choices and gold answer unchanged. Budget: 64 accepted target evaluations per decision. Seven datasets: MMLU-Pro, SuperGPQA, MuSR, ToMBench, LAR-ECHR, SATA-Bench, BFCL V4.

Decision Hijacking rebuilds 510 InjecAgent direct-harm cases for Jev 1.13.0 with state fields `user_request`, `actions_taken`, `latest_tool_result`; only the tool result is attacker-controlled. Action space of three choices (task completion, source tool, attacker target), plus an eight-option variant.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| Re-run flip floor | 1.0% [0.3, 1.9] | n/a | JevAdvBench, jev-1.13.0 | |
| Unverified observer opinion appended to state | +11.1 pp [7.8, 14.4] over floor (12.1% flips) | re-run floor | 812 questions | 82.4% of labels are model-derived |
| Authority-impersonation command | +9.1 pp [7.4, 11.1] (strongest command 10.1%) | re-run floor | same | |
| Opinion via analogy | +5.9 pp [3.8, 7.7] | re-run floor | same | |
| Unrelated sentences | +3.6 pp [2.3, 4.9] | re-run floor | same | |
| Rewording / paraphrase | +0.0 to +0.5 pp | re-run floor | same | |
| Confident (>= 0.8) answers pushed below 0.8 by opinion | 38.0% [31.1, 44.0] | 0.5% under re-run | same | |
| Total run cost | "about $0.41" for 11,368 requests | | | |
| JevOut targeted flip, Jev | 61.4% (312/508); per dataset 40.0% (LAR-ECHR) to 85.7% (BFCL V4) | untargeted neutral context 2.2%; single non-iterative proposal 16.9% | 64 target evaluations per item | optimisation, not natural occurrence |
| JevOut high-confidence flips (p >= 0.7 on wrong option) | 229 cases; 45.1% of successes | | | |
| JevOut, open-weight systems | OpenSourceJev 72.6% (238/328), Von 1.0 73.2% (240/328), Qwen scorer 64.9% (185/285) | | | |
| JevOut cross-model transfer of frozen contexts | 21.1% to 47.8% | | strongest between shared backbones | |
| JevOut compute | 60,685 accepted target evaluations, 74,323,719 target input tokens over 1,449 model-item pairs | | | |
| Decision Hijacking, original attacks | 1.8% (9/510) choose attacker target | | Jev 1.13.0 | |
| Decision Hijacking, adaptive (24 extra queries) | 3.5% on fresh validation calls | 1.8% | | |
| Override marker effect | -0.032 attacker probability [-0.060, -0.014] | | | opposite of generative agents |
| Large-margin cases | 1/468 hijacked | | | |

## Mechanism details you could implement
- Scoring against the model's own clean decision plus a re-run floor is a label-free way to measure robustness on our own memory decisions; it needs no gold labels and cost JevAdvBench about $0.41.
- Treat the `state` as untrusted, argued input (JevAdvBench's recommendation, quoted: "Applications built on RLCD models should therefore treat the state as untrusted, argued input").
- Decision margin predicts susceptibility (Decision Hijacking): log the gap between the top two option probabilities and treat small-margin decisions as the ones to escalate, not only low-confidence ones.
- Out-of-schema fields do not reach the model, so moving provenance and opinions into separate typed fields rather than free state text is a candidate mitigation (inference; untested in all three papers).

## Limitations, caveats, counter-evidence
- JevAdvBench tests only jev-1.13.0; 82.4% of labels are model-derived; a single LLM annotator validated only 40 variants; Score questions have a 7.0 pp minimum detectable effect.
- JevOut is an optimisation attack (about 42 evaluations per success); natural memory text will rarely be optimised against us. The unoptimised single-shot rate (16.9%) and JevAdvBench's unoptimised opinion (12.1%) are the more realistic figures for accidental contamination.
- No defences evaluated anywhere in the cluster.
- None of the tasks are memory-stage tasks; transfer to link or staleness decisions is inference.

## Takeaways for tuning a memory stack
- Stored memories often contain opinions ("this approach seems wrong", "X said Y is deprecated"). Placing them verbatim in the state of a linking, supersession or staleness decision can move roughly one decision in eight, and can move confident decisions under a 0.8 review threshold. Confidence alone is not a safe gate for memory-derived state.
- Open-weight System One models are not more robust than Jev here; self-hosting does not buy robustness.
- Command-style injection filters address the smaller risk for typed decisions; persuasive unverified claims are the larger one.

## Open questions
- Does separating memory content by provenance (`source_class` from discovery plan P5) into distinct fields reduce the flip rate?
- What is the flip rate on our own link and staleness decisions when the state includes neighbouring memories, compared with the re-run floor?

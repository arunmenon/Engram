---
schema_version: 1
artifact_id: N-SURVEY-20261009-02
artifact_type: note
producer: triage
run_id: survey-20261009T054505Z-36b1
created_at: 2026-10-09T05:51:28Z
idempotency_key: note:survey:arxiv:2609.04875
input_refs: []
pillar_primary: R2
pillar_secondary: [R8]
memory_stage: lifecycle (erasure)
beliefs_affected:
  supports: []
  contradicts: []
evidence: {directness: 5, control: 4, independence: 3, reproducibility: 1, applicability: 3}
source_url: https://arxiv.org/abs/2609.04875
found_via: survey
---

# Forgetting Without Restarting: Execution-State Unlearning for Stateful LLM Agents

- **URL:** https://arxiv.org/abs/2609.04875 (HTML v1 read)
- **Type:** paper
- **Author / org:** Chao Yao, Yangbo Wei, Zhen Huang, Junhong Qian, Chenle Chen, Shaoqiang Lu, Chen Wu, Lei He (Arizona State University; Eastern Institute of Technology, Ningbo)
- **Date:** 2026-09-04
- **Retrieved:** 2026-10-09 (local copy: out/log/raw/2609.04875.html)
- **Cited by evidence:** top-down survey, R2 erasure question
- **Relevance to a memory stack:** high. Deleting a memory record left leakage exactly unchanged; only replay from a provenance-located checkpoint matched a full reset.

## TL;DR
- "Forget" that deletes the plaintext memory record (B1) leaks exactly as much as not forgetting at all (B0): Any-Leak 0.94 average for both.
- Telling the model to forget collapses under elicitation probes (Leak@probes 1.00). Redacting the source still acts on a revoked preference in 80% of episodes.
- Selective replay from the injection point, guided by a provenance graph, reaches 0.00 leakage and matches a full reset, with 133 vs 1,235 recomputed tokens (about 9x fewer).
- Small open models only (Llama-3.1-8B primary), n=80 to 100 per suite, no code link found.

## What it claims / describes
Models the agent runtime (transcript, compressed summaries, plaintext memory, pending tool plans, KV cache) as a deterministic transition system. After a forget request the agent must behave as if it never saw the target. Proves the pre-target prefix is shared with the counterfactual for free, the post-target suffix is tainted without token-level attribution, and exact unlearning needs at least T - tau + 1 recomputed transitions (tau = injection step). Provenance-Guided Selective Replay attains the bound.

## Numbers
Table 1, Any-Leak (LongMemEval n=100 / ToolSandbox n=100 / AgentDojo n=80 / average):

| Arm | Values |
|---|---|
| B0 no forget | 0.86 / 1.00 / 0.97 / 0.94 |
| B1 memory delete | 0.86 / 1.00 / 0.97 / 0.94 |
| B2 forget instruction | 0.38 / 0.72 / 0.00 (query does not solicit target) / 0.37 |
| B3 source redaction | 0.84 / 0.94 / 0.39 / 0.72 |
| B4 sanitize, no replay | 0.00 all |
| B5 full reset (reference) | 0.00 all |
| B7 selective replay | 0.00 all |

| Other result | Value |
|---|---|
| Leak@probes (6 probes, n=30/suite) | B0 and B2 1.00 everywhere; B3 0.73 / 0.80 / 0.97; B5, B7 0.00 |
| Behavioural: acts on revoked preference | B0, B1, B2 and sanitized rebuild 1.00; B3 0.80; B5, B7 0.32 (floor) |
| Recomputed tokens | full reset 1,235; reset with prefix cache 202; selective replay 133 |
| Latency p50 | selective replay 2.9 to 3.7 s vs reset with prefix cache 11.5 to 12.7 s |
| Stochastic decoding (T=0.7, 5 samples) | no detectable divergence from full reset (Wilcoxon p > 0.5); matched seeds reproduce reset token for token in 450 of 450 draws |
| Invalidation-boundary ablation | excising only the target span: Any-leak 0.13 to 0.93; span plus descendants: 0.00 |

Models: Llama-3.1-8B-Instruct (RTX 4090), replicated on Qwen2.5-7B-Instruct and Mistral-7B-Instruct-v0.3. LLM judge excluded because its false-positive floor was 0.34; audits are string and behaviour based.

## Mechanism details you could implement
- Provenance record per artifact: id, type, parents, source_ids, token_span, turn, committed flag; edges memory field to prompt block to turn to plan to tool call to observation to summary.
- Taint closure = reachability from the revoked source; everything downstream is regenerated, not just the source span.
- Metadata-only checkpoints at turn boundaries and before tool or compaction steps.

## Limitations, caveats, counter-evidence
- Covers reconstructible runtime state, not weights; cannot undo committed external side effects.
- Utility on non-target facts not quantified in the tables read.
- Small 7 to 8B models; frontier APIs do not expose the KV-cache control the method assumes (inference).

## Takeaways for tuning a memory stack
- For Engram, an erasure request that deletes a node but leaves Summary nodes, merged nodes and cached context bundles derived from it is the B1 arm: expect zero reduction in influence. Erasure must walk derivation edges (P5 provenance fields make this possible).
- "Suppress" and "erase" need distinct semantics (R2 thesis): suppression can be a read-time flag; erasure needs a taint closure and regeneration of derived artifacts.

## Open questions
- What fraction of Engram's derived nodes carry enough provenance today to compute a taint closure?

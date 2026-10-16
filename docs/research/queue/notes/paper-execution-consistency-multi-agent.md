---
schema_version: 1
artifact_id: N-SURVEY-20261007-06
artifact_type: note
producer: triage
run_id: survey-20261007T054506Z-c08e
created_at: 2026-10-07T06:21:00Z
idempotency_key: note:survey:arxiv:2610.08101
input_refs: []
pillar_primary: R7
pillar_secondary: [R1, R8]
memory_stage: none
beliefs_affected:
  supports: [B22]
  contradicts: []
evidence: {directness: 3, control: 4, independence: 3, reproducibility: 2, applicability: 3}
source_url: https://arxiv.org/abs/2610.08101
found_via: survey
---

# Beyond Corrected Memory: Execution Consistency in Multi-Agent Systems (arXiv 2610.08101)

- **URL:** https://arxiv.org/abs/2610.08101 (HTML v1 read)
- **Type:** paper
- **Author / org:** not stated in extract
- **Date:** 2026-10-06
- **Retrieved:** 2026-10-07 (local copy: out/log/raw/2610.08101.html)
- **Cited by evidence:** survey
- **Relevance to a memory stack:** medium-high; shows that correct shared memory records are not enough to tell a compliant multi-agent run from a violating one unless receipts, dependencies, authorization and version eligibility are recorded.

## TL;DR
- "identical retained records can correspond to compliant and violating executions under the same task rule."
- "Among the 398 opposite-N/V pairs, 328 have identical retained inputs after removal (82.4%), compared with 4 (1.0%) before removal. Restoration makes 321 of those 328 input pairs distinguishable (97.9%)."
- Removal merges by relation (reader summary): receipt 69/80, dependency 65/79, authorization 68/81, version eligibility 57/76, repair validity 69/82.
- Checker cost $0.0017 per execution vs $0.0031 for an LLM contract checker; +24.6 % tokens and 5.0 s per task (reader summary).

## What it claims / describes
Execution record tuple (receipt, precedence, causal dependency, visibility, supersession, permissions, capture, history) and finding tuple; deterministic verdict rules over records extracted by DeepSeek-V4-Flash. Benchmarks: AgentWebBench, MARBLE, MECoBench, CoffeeBench, AppWorld, LongCLI; 720 diagnosis cases, 450 paired evaluations, 360 natural-log annotations. Recovery gain 9.1 pp [4.8, 13.4] (reader summary).

## Limitations
Extractor model is also a system under test. Accuracy 66.1 % when L2 evidence is missing. Recovery assumes uncommitted writes. Research benchmarks only; no commit pin.

## Takeaways for tuning a memory stack
- A handoff contract between agents should carry receipts, dependency and version-eligibility fields; without them, audit of what an agent was allowed to act on is impossible (supports P0 step 3, "never silently substitute").

---
schema_version: 1
artifact_id: N-SURVEY-20261002-06
artifact_type: note
producer: triage
run_id: survey-20261002T054505Z-3d1e
created_at: 2026-10-02T06:30:00Z
idempotency_key: note:survey:arxiv:2608.10502
input_refs: []
pillar_primary: R8
pillar_secondary: [R2]
memory_stage: maintenance
beliefs_affected:
  supports: [B25]
  contradicts: []
evidence:
  directness: high (directly measures undoing downstream effects of poisoned, stale, wrong-user and summary-drift memories)
  control: medium (6 baselines incl. full reset and delete-retrieved, 3 ablations; but single run at temperature 0, oracle-diagnosed faults)
  independence: low (authors built the 150-case benchmark, fault injection and the method; transfer set is adapted by authors from LongMemEval-V2)
  reproducibility: medium (schemas and prompt contracts in appendix; code availability not stated; GPT-4o seed 42)
  applicability: medium (requires an instrumented runtime emitting memory-to-step provenance; domains are shopping, travel, customer support, not coding)
source_url: https://arxiv.org/abs/2608.10502
found_via: survey
---
# From Faulty Memories to Corrected Actions: Dependency-Guided Rollback Repair for Memory-Augmented Agents

- **URL:** https://arxiv.org/abs/2608.10502 (HTML https://arxiv.org/html/2608.10502)
- **Type:** paper
- **Author / org:** Caili Yu, Yiqi Wang, Jiaqi Zhang, Yiqun Duan, Mingkai Zheng, Zhangkai Wu, Kaize Shi, Taotao Cai (affiliations not stated on page)
- **Date:** not stated on page (arXiv id implies Aug 2026)
- **Retrieved:** 2026-10-02 (local copy: /Users/arunmenon/MemoryRSI-Signals/work/survey/survey-20261002T054505Z-3d1e/out/log/src/2608.10502.html)
- **Cited by evidence:** survey R8
- **Relevance to a memory stack:** high, it is the clearest measured answer to "after a bad memory is found, can its downstream effects be undone without wiping good state".

## TL;DR
- Given a failed trace and diagnosed faulty memories, build a typed memory-to-action provenance graph, trace explicit dependents, keep nodes with independent trusted support, delete faults, quarantine unsupported derived memories, and replay only answer-relevant steps.
- Controlled benchmark (n=150, GPT-4o): recovery 0.853 vs 0.773 LLM-judge repair and 0.407 full memory reset; faulty removal 1.000; benign preservation 1.000 (full reset 0.000).
- Cost: replay ratio 0.123 and 5.70 LLM calls vs LLM-judge 0.217 and 9.80; full reset 0.061 and 4.03.
- Weak spots: recurrence 0.266 is worse than LLM-judge (0.121) and full reset (0.197); claim invalidation F1 0.566 is below LLM-judge (0.946).
- Transfer (n=50, multi-fault poisoned, adapted LongMemEval-V2): recovery 0.680 vs 0.540 AgentTrace-style; authors call controlled results "an upper bound rather than a deployment estimate".

## What it claims / describes
Formulates post-failure memory recovery. Edges (initiate, cite, support, produce, delete, update, consolidate, supersede, derive) are instantiated deterministically from runtime provenance; pure temporal chain edges are excluded because "occurring later is not evidence of contamination". Independent support: admissible sources are current-turn instruction, non-faulty active memory, successful tool observation, or unaffected validated claim, and a source counts only if outside the faulty set and the affected set; "preserved candidates are not recursively reused to validate others". Rollback "cannot undo an irreversible external side effect"; re-executing side-effecting tools needs resettable, idempotent or compensating interfaces.

## Numbers
| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Recovery | 0.853 | LLM-judge 0.773; AgentTrace-style 0.607; full reset 0.407; delete retrieved 0.340; MemAudit-style 0.320; no repair 0.000 | 150 controlled cases, 3 domains, 4 fault types, GPT-4o | single run, temp 0; faults pre-diagnosed |
| Recurrence (lower better) | 0.266 | LLM-judge 0.121; full reset 0.197; AgentTrace 0.341; delete retrieved 0.431 | same | computed only over recovered cases |
| Faulty removal / benign preservation | 1.000 / 1.000 | full reset 1.000 / 0.000; delete retrieved 0.881 / 0.789; MemAudit 0.311 / 0.980 | same | |
| Claim-inv. F1 | 0.566 | LLM-judge 0.946; AgentTrace 0.853 | same | method under-identifies claim-level contamination |
| Replay ratio / LLM calls | 0.123 / 5.70 | LLM-judge 0.217 / 9.80; full reset 0.061 / 4.03 | same | text: 43.3% fewer replays and 41.8% fewer calls than LLM-judge (consistent with table) |
| Ablation w/o selective replay | recovery 0.840, recurrence 0.071, replay 0.755, calls 24.01 | full method 0.853, 0.266, 0.123, 5.70 | Table 3 | explicit recurrence vs cost trade-off |
| Ablation w/o rollback planner | recovery 0.713, recurrence 0.430, calls 9.19 | | Table 3 | |
| Ablation w/o support check | recovery 0.880, preservation 0.986 | | Table 3 | support check costs recovery to protect benign state |
| Transfer recovery | 0.680 | AgentTrace 0.540; LLM-judge 0.260; MemAudit 0.260; delete 0.100; full reset 0.060 | 50 adapted LongMemEval-V2 cases, 45 with 2 to 4 faults | claim-inv. F1 0.669 vs 0.603; recurrence 0.059 vs AgentTrace 0.037 |

No text/table disagreements found in checked ratios (2x full reset, 43.3%, 41.8%).

## Mechanism details you could implement
- Emit provenance IDs on every step (memory read IDs, claim IDs, tool call IDs, lifecycle ops) at runtime; do not infer them from logs.
- Propagate taint only along typed dependency edges, not along time order.
- Dispositions: delete diagnosed faults; quarantine unsupported derived memories into an audit partition unavailable to retrieval; preserve nodes with an independent admissible source.
- Replay only the execution closure of answer-relevant invalidated nodes; withhold invalidated claims from replay context.

## Limitations, caveats, counter-evidence
- Fault diagnosis is given (oracle); detector accuracy and natural fault prevalence not estimated.
- Single run, no confidence intervals.
- Incomplete provenance under-traces; spurious edges over-invalidate.
- Recurrence is worse than a simple LLM-judge repair and than full reset on the controlled set.
- Full reset still recovers 0.407 at lowest cost; whether that is acceptable depends on value of benign memory.
- Cost in tokens: Table 18 exists; latency not stated in sections read.

## Takeaways for tuning a memory stack
- R8/R2 recovery is feasible if provenance is recorded at write and read time; without it, the choices collapse to delete-source (0.340 recovery) or full reset (0.407, zero benign preservation).
- The independent-support rule (affected nodes cannot vouch for each other) is a concrete instance of B25.
- For coding agents (inference): log which memory entries were read into each session and which files/commits each session produced, so a bad memory can be traced to derived memories and artifacts.

## Open questions
- Recovery with a real (non-oracle) detector? (not stated)
- Effects that left the agent (commits, PRs, emails) are explicitly out of scope; how to compensate? (not stated)
- Why is recurrence higher than LLM-judge repair, and can a broader-but-capped replay fix it at lower cost than 24.01 calls? (open)

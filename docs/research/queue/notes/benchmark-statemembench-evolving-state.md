---
schema_version: 1
artifact_id: N-SURVEY-20260930-06
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:58:20Z
idempotency_key: note:survey:arxiv:2608.19652
input_refs: []
pillar_primary: R6
pillar_secondary: [R2, R10]
memory_stage: staleness
priority: 4
beliefs_affected:
  supports: [B3]
  contradicts: []
evidence: {directness: high, control: high, independence: medium, reproducibility: low, applicability: medium}
strength: paper-ablated
source_url: https://arxiv.org/abs/2608.19652
found_via: survey
---

# Can Agent Memory Systems Track Evolving State? (StateMemBench and StateMem)

- **URL:** https://arxiv.org/abs/2608.19652 (HTML v1 read: https://arxiv.org/html/2608.19652v1)
- **Type:** paper (benchmark plus method)
- **Author / org:** Xinyi Fan, Miri Liu, Ruozhen Yang, Siru Ouyang, Jiawei Han (University of Illinois Urbana-Champaign)
- **Date:** 2026-08-20
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2608.19652.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R6 question 3 (benchmark map: staleness and changed requirements)
- **Relevance to a memory stack:** high. It is a benchmark built around superseded values, with gold answers computed by replaying typed state operations, and a grading scheme that separates "answered with the stale value" from other errors.

## TL;DR
- StateMemBench: 234 multi-session scenarios, 322 graded probes, two length regimes. Each probe is graded against a closed pool holding the current-state answer, the targeted stale ("drift") answer and neutral distractors.
- Every baseline is poor. Reading the full transcript in context scores 0.149 current-state accuracy on both backbones. The best baseline is 0.224 (GraphRAG, Qwen-3.5-9B) or 0.205 (dense retrieval, DeepSeek-V4-Flash).
- The authors' method StateMem reaches 0.233 (Qwen) and 0.363 (DeepSeek). In its ablation, supersession marking is the largest single component ("0.174 → 0.298 on DeepSeek").
- A single-call "state-tracing" wrapper placed over six existing backends adds 32 to 67 points on StateMemBench; a length-matched and cost-matched generic control shows 15 to 32 of those points come from the state structure.
- On LongMemEval with oracle retrieval, 44.4 % of remaining failures (16 of 36) are attributed to state drift, so the facts were present and the stale one was used.

## What it claims / describes
State tracking is defined as answering from the current state after "facts, constraints, and decisions are revised over a long interaction". Each scenario is an executable symbolic event program: typed state operations (rule declarations, value updates, scoped exceptions, commitments, retractions) replayed by a deterministic evaluator that computes the gold answer. The surface text is synthetic, grounded in public data: open-access papers (research domain), the Instacart basket dataset (shopping), a synthetic credit card transactions dataset (personal finance). No software engineering domain.

Sizes: Set A (short) 190 single-probe scenarios, median about 165 turns; Set B (long) 44 fused scenarios, median about 599 turns.

Five probe categories:
- Status: the value changed and the reader anchors on the earlier commitment.
- Salience: the valid value is present and a more prominent competitor wins.
- Sequence: a stated derived value is not recomputed after an input changes.
- Compound: several mechanisms interact.
- Anti-trap: the earlier value is still correct and a later mention is spurious; tests against over-updating.

Grading: a deterministic word-boundary matcher handles the 28 % of answers that name exactly one pool option verbatim; a fixed judge (DeepSeek-V4-Pro) maps the rest to a pool option. Agreement between matcher and judge on the matcher's subset: 94.1 %.

Systems: Mem0, A-Mem, LightMem, MemoryOS, StateMem; BM25 and dense (text-embedding-3-small) retrieval; nano-graphrag, HippoRAG, LightRAG, GraphRAG; long-context reads with Qwen-3.5-9B, Qwen-3.6-35B-A3B, GPT-5.4-Nano, DeepSeek-V4-Flash.

## Numbers
Current-state accuracy on StateMemBench (overall / short / long):

| Condition | Qwen-3.5-9B | DeepSeek-V4-Flash |
|---|---|---|
| No memory | 0.006 / 0.000 / 0.015 | 0.003 / 0.000 / 0.008 |
| Long-context | 0.149 / 0.137 / 0.167 | 0.149 / 0.132 / 0.174 |
| BM25 | 0.125 / 0.095 / 0.167 | 0.143 / 0.105 / 0.197 |
| Dense | 0.130 / 0.105 / 0.167 | 0.205 / 0.168 / 0.258 |
| GraphRAG | 0.224 / 0.216 / 0.235 | 0.174 / 0.137 / 0.227 |
| Mem0 | 0.149 / 0.116 / 0.197 | 0.177 / 0.168 / 0.189 |
| A-Mem | 0.127 / 0.100 / 0.167 | 0.199 / 0.158 / 0.258 |
| StateMem | 0.233 / 0.237 / 0.227 | 0.363 / 0.411 / 0.295 |

StateMem against the strongest memory baseline: p < 0.001, paired McNemar.

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Drift rate (answered with the stale option), n=322 | full context 65.5 % (Qwen), 64.0 % (DeepSeek); Mem0 62.7 %, 59.9 %; BM25 60.9 %, 59.9 %; StateMem 64.3 %, 49.1 % | | in-pool answers only | StateMem does not lower drift on the weaker backbone |
| Supersession marking, ablation | "0.174 → 0.298 on DeepSeek" | StateMem without it | | isolated component, one backbone |
| Dependency propagation | helps target modes; −12.5 pp on Set B anti-traps | | | over-updates |
| Wrapper, StateMemBench, DeepSeek, n=60 paired | Mem0 28.3 alone, 56.7 control, 71.7 wrapper; A-Mem 33.3, 51.7, 75.0; BM25 21.7, 48.3, 70.0; Dense 31.7, 43.3, 70.0; LightMem 1.7, 51.7, 68.3; MemOS 1.7, 50.0, 68.3 | alone and matched control | percent | 60-item subset |
| Wrapper, StateMemBench, Qwen, n=60 paired | Mem0 25.0, 28.3, 56.7; A-Mem 23.3, 35.0, 56.7; BM25 20.0, 31.7, 56.7; Dense 21.7, 28.3, 56.7 | alone and matched control | percent | |
| Wrapper, LongMemEval, DeepSeek, n=60 | Mem0 45.0, 58.3, 60.0; Dense 53.3, 61.7, 56.7 | | | the wrapper is below the generic control for Dense |
| Existing benchmarks, StateMem | LongMemEval 0.580 (Qwen), 0.656 (DeepSeek); LoCoMo 0.566, 0.592 | long-context 0.550, 0.666; 0.612, 0.587; Mem0 0.566, 0.594; 0.481, 0.462 | | StateMem is roughly level with long context here |
| LongMemEval oracle failures due to drift | 44.4 % (16/36); multi-session 71.4 % (10/14); knowledge-update 25.0 % (2/8) | | perfect retrieval | small counts |
| LightMem, MemoryOS on LongMemEval | 0.064 and 0.080 (Qwen) | published scores far higher | released implementations, upstream example configs | the authors note these are "near floor on every benchmark we run, below any plausible level for published systems" |
| Cost, latency | not stated in what was read (the wrapper is described as one added call) | | | |

Judge and system: the judge is DeepSeek-V4-Pro; one evaluated backbone is DeepSeek-V4-Flash (same family, different model).

## Mechanism details you could implement
- Closed-pool grading for staleness: for each probe store the current answer, the specific stale answer a reader would give if it missed the update, and 1 to 2 neutral distractors. Report current-state accuracy and drift rate separately. A deterministic matcher covers verbatim answers; a judge only maps free text to an option.
- Gold by construction: define each scenario as a sequence of typed state operations and compute the answer by replay. No annotation step, so no gold-label disputes of the LongMemEval kind.
- Anti-trap probes: include cases where the earlier value is still right. A system that always prefers the latest mention fails these (dependency propagation lost 12.5 points on them).
- Matched control for any added reasoning step: compare against a generic step of the same length and cost, so that the gain is attributed to the structure and not to extra context. Here the control alone added up to 50 points for weak backends.
- State-tracing wrapper: the paper describes "a lightweight single-call wrapper over existing memory systems" that applies the same state approach (supersession and relational dependencies). The wrapper prompt was not extracted: not stated here. A plausible shape is one call between retrieval and answer that marks which retrieved items supersede which, recomputes derived values, and answers from the resulting state (inference).

## Limitations, caveats, counter-evidence
- Stated: synthetic scenarios in three domains; closed pool cannot measure hallucination; drift labelling is conservative.
- Stated: mechanism labels rely on judges with inter-judge kappa near zero despite high binary agreement.
- Stated: StateMem "mirrors" the policy family used to build the traps, so its scores are an upper bound.
- Two baselines (LightMem, MemoryOS) run near the floor, which suggests configuration problems; do not read their rows as evidence about those systems (inference, supported by the authors' own remark).
- Small open models only (9B to 35B, GPT-5.4-Nano, DeepSeek-V4-Flash). A frontier reader may drift far less.
- Code and data: a release is mentioned; no URL found in the text read.
- Counter-evidence to "graph structure helps state questions": GraphRAG leads the baselines on Qwen (0.224) and trails dense retrieval on DeepSeek (0.174 against 0.205).

## Takeaways for tuning a memory stack
- Verbatim retention is not enough for "what is the current value" questions: the full transcript in context scores 0.149 and drifts to the stale value in about 65 % of in-pool answers. H1's ledger-only arm should be expected to fail this class; it needs a supersession mechanism on top.
- B3 says the isolated contribution of supersede edges is not measured. This paper gives one isolated figure for supersession marking (0.174 to 0.298, one backbone, authors' own method). It is a different system from REALM, so B3's grade should not move on it alone; H7 and PC-20260926-C05 remain the test.
- For the PDLC benchmark, this is the template for "notice a changed requirement" and "spot a stale memory": typed operations replayed to a gold state, closed-pool grading with the stale answer as a named option, anti-trap cases.
- A read-time state-tracing call is a cheap arm to add to H7 or H10 beside write-time edges, with a length-matched control.

## Open questions
- Does drift persist with frontier readers, or is this a small-model effect?
- Would typed supersedes edges written at ingest remove the need for the read-time wrapper?
- How does a PDLC version look: requirement revised, scoped exception for one component, decision retracted?

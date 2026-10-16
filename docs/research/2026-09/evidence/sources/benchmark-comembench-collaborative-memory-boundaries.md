---
schema_version: 1
artifact_id: N-SURVEY-20260930-03
artifact_type: note
producer: triage
run_id: survey-20260930T054503Z-298f
created_at: 2026-09-30T05:56:30Z
idempotency_key: note:survey:arxiv:2609.32192
input_refs: []
pillar_primary: R7
pillar_secondary: [R6, R8, R3]
memory_stage: assembly
priority: 4
beliefs_affected:
  supports: [B22]
  contradicts: []
evidence: {directness: high, control: high, independence: high, reproducibility: medium, applicability: high}
strength: paper-ablated
source_url: https://arxiv.org/abs/2609.32192
found_via: survey
---

# CoMemBench: Benchmarking Collaborative Memory Boundaries across Multi-Agent Workflow Topologies

- **URL:** https://arxiv.org/abs/2609.32192 (HTML v2 read: https://arxiv.org/html/2609.32192v2); site http://comembench.world
- **Type:** paper (benchmark)
- **Author / org:** Sen Zhao, Ruiqi Kong, Zuyu Zhang, Lifeng Shen, Xinyu He, Ding Zou, Xu Zhang, Qinghua Zhang (Chongqing University of Posts and Telecommunications; Towngas; ZTE)
- **Date:** 2026-09-26 (v1), 2026-09-29 (v2)
- **Retrieved:** 2026-09-30 (local copy: out/log/raw/2609.32192.html)
- **Cited by evidence:** survey run survey-20260930T054503Z-298f, R7 question 4 (handoff contracts with measured evidence)
- **Relevance to a memory stack:** high. It measures, with executable oracles and one domain built on SWE-bench Verified, what happens when agents in a workflow get more than their declared handoffs.

## TL;DR
- A "collaborative memory boundary" is the task-conditioned scope of what each agent should see: needed results shared, "irrelevant, stale, unverified, or incompatible information" kept out.
- 800 composite workflows over four domains (200 each), each with a matched polluted twin (1,600 instances), 8,975 node-local contexts, average 17.66 required handoffs per workflow. Scoring uses domain-native evaluators (MCP servers, the SWE-bench harness, corpus checks, the Lean compiler). No LLM judge.
- With the executor fixed (Qwen3.8-27B), handing agents more context raises progress and lowers isolation. On repository code, declared-handoffs-only scored 0.0 % workflow success with 89.4 % isolation; full context scored 16.0 % success with 71.9 % isolation; shared flat RAG 18.0 % and 73.9 %.
- Memory products do not resolve the trade-off: Mem0 on code scored 2.0 % success and 89.1 % isolation; A-Mem 18.4 % and 63.9 %; PlugMem 0.0 % and 91.3 %.
- Rankings change with workflow shape. EvoMAS reaches 72.7 isolation on split-join and 14.3 on reuse.

## What it claims / describes
Workflows are built from source-grounded dependency graphs. Each node has a local specification and a verifiable artifact handoff. Five topology motifs: chain, split-join, reuse (one verified result consumed by several downstream agents), overlap (consumers with partly shared predecessors), bounded revision (a verifier-triggered repair supersedes an earlier result).

Domains and pinned sources:

| Domain | Source | Revision | Count |
|---|---|---|---|
| Stateful tool use | Toolathlon-GYM | 45bb4935 | 200 |
| Repository code | SWE-bench Verified | c104f84 | 200 |
| Offline retrieval | BrowseComp+ | 144cff8e | 200 |
| Formal mathematics | HepLean, HTPI, PNT | 7448822a; 8eeebaec; 23650db8 | 200 |

The repository code domain covers issue analysis, reproduction, localisation, patching and regression testing.

Isolation challenges are built by six pollution operators applied to a clean workflow (named in what was read: sibling crosswire, wrong entity, unverified result; the other three are not stated in the extract). Ground truth: automated gates (schema validation, graph closure, topology witnesses, control and polluted equality, evaluator coverage), a gold execution plan replayed deterministically where "targeted negative mutations must fail", human review, and private leakage audits.

Metrics:
- SR: terminal workflow success.
- VNCR: verified node completion rate, macro average of the verified fraction of required nodes.
- VHS: verified handoff success, fraction of eligible consumers that complete after their mandatory predecessors verify.
- ICS: isolation challenge success, polluted-target success among matched pairs whose clean target succeeds.
- Token cost: input and output tokens, mean, median, 90th percentile (values not extracted).

Systems: Codex, Hermes, Deep Agents, CrewAI, AutoGen, Peer Review, SMoA, OMAC, ADAS, EvoMAS. Backbones: Qwen3.8-27B, DeepSeek-V4-Flash, GPT-6-Luna. Memory mechanisms under a fixed executor: Local-only (declared handoffs only), Full Context (all prior visible artifacts), Shared Flat RAG (all-MiniLM-L6-v2), Mem0 (0.1.104, Qdrant), A-Mem, PlugMem.

## Numbers
Memory-mechanism results, fixed executor, Qwen3.8-27B. Each cell is SR / VNCR / VHS / ICS in percent.

| Mechanism | Stateful tool | Repository code | Offline retrieval | Formal math |
|---|---|---|---|---|
| Local-only | 0.0 / 74.6 / 84.0 / 97.1 | 0.0 / 77.1 / 89.5 / 89.4 | 2.0 / 63.6 / 83.9 / 60.9 | 0.0 / 13.6 / 26.9 / 0.0 |
| Full Context | 2.0 / 86.9 / 86.7 / 72.4 | 16.0 / 61.7 / 89.1 / 71.9 | 6.0 / 77.1 / 88.6 / 80.6 | 0.0 / 11.8 / 26.8 / 0.0 |
| Shared Flat RAG | 2.0 / 86.9 / 86.4 / 70.6 | 18.0 / 72.4 / 90.8 / 73.9 | 8.0 / 74.1 / 88.4 / 75.0 | 0.0 / 14.4 / 29.7 / 20.0 |
| Mem0 | 0.0 / 83.8 / 85.5 / 86.3 | 2.0 / 77.9 / 89.6 / 89.1 | 4.0 / 64.9 / 84.7 / 73.9 | 0.0 / 12.2 / 22.7 / 52.4 |
| A-Mem | 4.0 / 85.8 / 86.6 / 87.9 | 18.4 / 58.2 / 88.4 / 63.9 | 6.0 / 71.8 / 85.6 / 71.9 | 0.0 / 12.3 / 26.2 / 0.0 |
| PlugMem | 0.0 / 83.1 / 85.1 / 90.0 | 0.0 / 68.2 / 88.9 / 91.3 | 4.0 / 56.9 / 83.9 / 52.9 | 0.0 / 14.2 / 29.0 / 33.3 |

Other quoted results:

| Metric | Value | Baseline | Setup | Caveat |
|---|---|---|---|---|
| Stateful tool, VNCR and ICS, Full Context | VNCR "74.6 to 86.9", ICS "97.1 to 72.4" | Local-only | fixed executor | the paper's own summary of the trade-off |
| Best terminal SR among full systems | 8.0 % repository code (ADAS, DeepSeek-V4-Flash); 18.0 % offline retrieval (AutoGen, Qwen3.8-27B) | n/a | 10 systems, 3 backbones | no system solves any stateful tool or formal math workflow |
| Progress without closure | OMAC, DeepSeek-V4-Flash, code: SR 4.0, VNCR 84.2, VHS 89.4; ICS 4.4 | Peer Review ICS 17.1 | | high handoff success with near-zero isolation |
| General-purpose runtimes | Codex and Hermes ICS 0.0 on every backbone | n/a | | |
| Topology, Qwen3.8-27B | chain VHS 56.5 to 85.1 across systems; split-join VHS 20.5 to 51.8 | n/a | | chain is easiest for every system |
| Pollution type | EvoMAS 80.0 % on sibling crosswires, 20.7 % on unverified results; Deep Agents 80.0 % on wrong entity, 31.0 % on unverified results | n/a | | robustness does not transfer across violation types |
| Judge shares a model with the system | no LLM judge | | | |
| n per cell, seeds, confidence intervals | not stated in what was read | | | SR values in steps of 2.0 suggest about 50 workflows per cell (inference) |
| Token cost per mechanism | reported by the paper, not extracted | | | |

## Mechanism details you could implement
- Evaluate a shared memory with matched pairs: a clean workflow and the same workflow with one planted artifact (a sibling branch's result, a wrong-entity record, an unverified result, a superseded result). Score isolation only on pairs whose clean run succeeds.
- Measure handoff reliability separately from task success: VHS counts a consumer only after its mandatory predecessors are verified.
- The Local-only arm is a declared-handoff contract: a consumer receives exactly the artifacts on its incoming edges. It gave the best isolation on stateful tool use (97.1) and came within 2 points of the best on code (89.4 against PlugMem's 91.3), with 0.0 % terminal success on both. It did not lead on retrieval (60.9) or math (0.0).
- Bounded revision is the supersession case in a workflow: after a verifier-triggered repair, the earlier result must stop being served to downstream agents.

## Limitations, caveats, counter-evidence
- No limitations section was found in the text read.
- Terminal success is near the floor almost everywhere, so conclusions rest on intermediate metrics (VNCR, VHS, ICS).
- The memory-mechanism comparison uses one backbone. Per-cell n, seeds and intervals were not found; several ICS cells are 0.0 or have few eligible pairs (formal math), so small differences there mean little (inference).
- Infrastructure and benchmark failures are "quarantined" rather than analysed.
- Release: data, clean and polluted pair specifications, schemas, evaluation code and prompts are promised at http://comembench.world; no repository link was found. Not checked whether the release is live.
- Counter-evidence to a simple reading: on offline retrieval, Full Context has higher isolation (80.6) than Local-only (60.9). More context did not always weaken isolation.

## Takeaways for tuning a memory stack
- A shared context graph served to several agents needs a scope per consumer, not one retrieval surface. Flat shared retrieval bought 18 points of code success and cost about 15 points of isolation against declared handoffs.
- The right comparison for us is a third arm the paper does not run: shared memory filtered by an explicit scope (consumer, verified status, not superseded). That arm is what B22's "one scoped interface" implies.
- For the PDLC memory benchmark: build each case as a clean and polluted pair with an executable oracle; include a revision topology so that "notice a changed requirement" and "spot a stale memory" are scored as isolation, not as recall.
- Unverified upstream results were the hardest pollution type for the two systems quoted. A `verified` flag on handed-over artifacts is a cheap field to carry (consistent with the typed handoff fields in N-SURVEY-20260928-07).

## Open questions
- Does a scope-filtered shared store keep Full Context's progress while restoring Local-only's isolation?
- How do the results change with a frontier backbone as the fixed executor?
- What are the three pollution operators not named in the extract, and which correspond to superseded requirements?

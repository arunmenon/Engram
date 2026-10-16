---
schema_version: 1
artifact_id: N-20260929-32
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104813926953431263", "file_id": null, "sha256": null}, {"artifact_id": "post:2104765315863503288", "file_id": null, "sha256": null}, {"artifact_id": "post:2104807500029551020", "file_id": null, "sha256": null}, {"artifact_id": "post:2104771628328780104", "file_id": null, "sha256": null}, {"artifact_id": "post:2104767977166110859", "file_id": null, "sha256": null}, {"artifact_id": "post:2104773750130381223", "file_id": null, "sha256": null}, {"artifact_id": "post:2104815579270091112", "file_id": null, "sha256": null}, {"artifact_id": "post:2104819530639999176", "file_id": null, "sha256": null}, {"artifact_id": "post:2104778165105332627", "file_id": null, "sha256": null}, {"artifact_id": "post:2104820535960178718", "file_id": null, "sha256": null}, {"artifact_id": "post:2104821921787396537", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:evermind-ai/raven
claim_cluster: github:evermind-ai/raven
feeds: ["memory"]
primary_source: https://github.com/EverMind-AI/Raven
source_commit: e6c0344cb7ce00db25d554e4bb671ec1909a8f9f
strength: vendor-benchmark
pillar_primary: R7
pillar_secondary: ["R5", "R6"]
memory_stage: routing
tags: {"mechanism": ["host-agent-dag-orchestration", "sub-agent-memory-record", "dual-track-memory-backend", "harness-self-evolution"], "workload": ["multi-agent-orchestration", "coding-agent", "long-horizon-tasks"], "lifecycle_stage": ["routing", "assembly"], "cross_cutting": ["vendor-benchmark", "claim-misattribution", "rsi"]}
evidence_grade: {"directness": "medium: numbers read from the vendor chart image in the pinned README; benchmark definition not in repo", "control": "low: two baselines (Hermes, Claude Code) on two backbones, no stated n, no variance, no ablation of memory", "independence": "low: vendor-run benchmark of unknown provenance, vendor chart", "reproducibility": "low: no benchmark data, harness or task list in the repo; 82-page technical report PDF could not be text-extracted here", "applicability": "low: measures DAG plan match for task decomposition, not memory quality or PDLC retrieval"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Cross-agent shared memory in orchestrators is often a join by session id plus file handoff, not served shared context; claims of shared memory need the read path checked"]}
claim_correction: The staged posts link github.com/stretchcloud/campfire, which is a different project (Campfire, a collaborative web UI for coding agents by @stretchcloud); Raven is github.com/EverMind-AI/Raven; 0.963 Node F1 is the DS-V4-Flash-0731 backbone result (0.923 on Qwen3.8-27B) on an undefined vendor benchmark with no n; "shared memory across sub-agents" is per-sub-agent EverOS stores surfaced to downstream DAG nodes as memory.json file paths, not injected content.
---

# Raven 0.2.0: "The Harness of Harnesses, built for RSI" (EverMind AI)

- **URL:** https://github.com/EverMind-AI/Raven (the staged posts link http://github.com/stretchcloud/campfire, a different project, see TL;DR)
- **Type:** repo (plus vendor technical report PDF, not text-readable here)
- **Author / org:** EverMind AI (announcement by @LongTermMemoryE, CEO @EverMind); Apache-2.0; README says "Raven is pre-alpha."
- **Date:** commit read `e6c0344cb7ce00db25d554e4bb671ec1909a8f9f` (committed 2026-09-28 20:06:49 +0800, "fix(agent): let a plugin the turn connects be used in that turn (#816)"). Announcement post 2104745468119146913, 2026-09-29 01:29:58 UTC.
- **Retrieved:** 2026-09-29. Local copies: repos/raven (shallow clone), repos/raven-assets/mao-benchmark.png (the README benchmark chart, https://github.com/user-attachments/assets/1756ab94-706d-4c07-b8b3-3ef6dd8a147f), repos/campfire (shallow clone of the linked repo, commit `4e72c09e44d9f57465f02c6d587806c69c9d5195`, 2026-07-08). Read: Raven README.md, docs/technical-report/README.md (abstract), docs/memory-plugin-architecture.md (sections 1 to 3), docs/specs/2026-08-17-subagent-everos-memory-record-design.md (sections 1 to 4), raven/memory_engine/skills/subagent-dag-orchestration/SKILL.md (grep); Campfire README.md (first half) and repo-wide grep. Technical report PDF (v1, 82 pages) was fetched but its text could not be extracted.
- **Cited by evidence:** feed memory; @stretchcloud post https://x.com/stretchcloud/status/2104813926953431263 (quotes https://x.com/LongTermMemoryE/status/2104745468119146913, which links http://github.com/EverMind-AI/Raven) plus 10 further staged posts: 2104765315863503288, 2104807500029551020, 2104771628328780104, 2104767977166110859, 2104773750130381223, 2104815579270091112, 2104819530639999176, 2104778165105332627, 2104820535960178718, 2104821921787396537 (handles not resolved here).
- **Relevance to a memory stack:** low to medium. The benchmark scores orchestration plans, not memory; the useful part is a concrete, documented pattern for how one sub-agent's distilled memory reaches the next node in a DAG (session-id join, file handoff, status field).

## TL;DR
- Claim correction (source): @stretchcloud's post summarises Raven and then describes Campfire, linking http://github.com/stretchcloud/campfire. Campfire contains no mention of Raven, Node F1, or the benchmark (repo-wide grep, zero hits). The claim belongs to https://github.com/EverMind-AI/Raven, linked from the quoted @LongTermMemoryE post.
- Claim correction (number): the README chart shows Node F1 0.963 for Raven with backbone DS-V4-Flash-0731 (Claude Code 0.835, Hermes 0.854) and 0.923 with Qwen3.8-27B (Claude Code 0.524, Hermes 0.776). The "0.963" is the better of two backbones.
- The benchmark is not defined anywhere in the repo: no task list, no gold graphs, no n, no scorer. Only the chart image and its alt text ("Node F1, Edge F1, Partial Order Accuracy, and Exact Match Rate") exist. The metric names suggest a predicted-vs-gold task-graph comparison (inference).
- Claim correction (memory): "shared memory across sub-agents" in the repo means each Raven sub-agent writes its own EverOS store; after a call the host polls EverOS by session id and writes `<node_id>.memory.json`; downstream DAG nodes get the file path and may read it. The spec says "Nothing injects a record's text into another sub-agent's prompt." No memory ablation is reported.

## What it claims / describes
**Announcement (verbatim excerpt, post 2104745468119146913):** "Raven's sub-harnesses and external agents work in one task graph with shared memory across sub-agents, powered by leading orchestration (0.963 Node F1 on the Multi-Agent Orchestration Benchmark)." Also: "The whole harness can be rewritten by AI: prompts, policies, strategy code, playbooks."

**Architecture (README).** A Host Agent "generates DAGs and orchestrates multiple specialized agents". Built-in agents Raven-Research, Raven-Code, Raven-Design, Raven-Oncall; presets for 13 third-party agents over ACP, CLI or OpenAI-compatible APIs. Core systems table: Agent Orchestration, Evolver ("retaining changes that outperform the baseline in reproducible evaluations"), EverOS Memory ("Preserves user context, agent experience, and world knowledge across sessions"), SkillForge (claims a catalog of "114,190 skills"), Proactivity. "Runtime Self-Evolution": the agent loop is split into Memory, Planning, Capability and Action strategy modules which a Curator rewrites; "nothing is installed before it is verified"; the Curator "is experimental: it ships with the repository rather than the installed package."

**DAG node contract** (subagent-dag-orchestration SKILL.md): node fields `subagent`, `prompt_template`, `depends_on`, `inputs` (literal, `{"file": ...}` or `{"node": id}`), `instance` (a stable handle; nodes sharing it reuse one sub-agent session, only on agents tagged `[stateful]`). `replan` replaces the remainder of a graph; completed nodes are referenced, never re-declared. Each node leaves `<node_id>.out.md`, `<node_id>.prompt.md` and, if its sub-agent runs on a long-term memory backend, `<node_id>.memory.json`, reachable as `ref:@nodes/<node_id>.memory.json`.

**Memory backend contract** (docs/memory-plugin-architecture.md, `raven/contracts/memory.py`):
```python
async def recall(self, query, *, user_id=None, agent_id=None, top_k) -> list[Memory]
async def store(self, session_id, messages) -> bool
async def feedback(self, signals) -> None   # may be no-op
```
`recall` takes exactly one of `user_id` / `agent_id` (XOR); "Neither/both set -> return []". The user track feeds the `# Memory` prompt segment; the agent track feeds skills (`BackendSkillSource`). Ids live only in `memory.userId` / `memory.agentId` because two copies once split writes from reads and "recall simply returned nothing forever".

**Sub-agent memory record** (spec dated 2026-08-17, status "designed"; code references to `memory.json` exist in raven/agent/subagent/spawn_tool.py, manager.py, dag_store.py): after a sub-agent call, the host resolves `session_id = session_prefix + InstanceRegistry.lookup(session_key, agent, handle)` and polls EverOS `POST /api/v2/memory/get` with backoff "2s, 4s, 8s, 16s, 30s, 30s..." until the result stops growing or a 60 s budget (`_DEFAULT_BUDGET_S`) is spent. Record file: `{"agent", "instance", "status": "settled|pending|unavailable", "memories": [{"type": "episode|agent_case", "text"}]}`, text uncapped. Non-goal, verbatim: "The join key is per *instance*, not per call ... a memory observed during call N may summarize call N-1. The record says these memories appeared for this instance around this call. It does not claim to have caused them."

**Campfire (the linked repo), for the record.** Campfire is a Bun/React web UI that runs Claude Code, Codex, Goose, Aider, OpenHands, OpenClaw and OpenCode side by side. It has its own "Collective Intelligence" layer (LanceDB semantic memory with namespaces global / repo / session / agent, per-namespace half-life decay, a JUDGE, DISTILL, CONSOLIDATE pipeline, recall under a "250 ms budget"). None of this is Raven, and Campfire reports no benchmark numbers in the part read.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Node F1, Raven | 0.963 | Hermes 0.854, Claude Code 0.835 | "Multi-Agent Orchestration Benchmark", backbone DS-V4-Flash-0731; README chart | n not stated; benchmark undefined; vendor-run |
| Edge F1, Raven | 0.897 | Hermes 0.776, Claude Code 0.813 | same, DS-V4-Flash-0731 | same |
| Partial Order Accuracy, Raven | 0.918 | Hermes 0.803, Claude Code 0.844 | same, DS-V4-Flash-0731 | same |
| Exact Match Rate, Raven | 0.867 | Hermes 0.748, Claude Code 0.762 | same, DS-V4-Flash-0731 | same |
| Node F1, Raven | 0.923 | Hermes 0.776, Claude Code 0.524 | same benchmark, backbone Qwen3.8-27B | same |
| Edge F1, Raven | 0.812 | Hermes 0.744, Claude Code 0.507 | Qwen3.8-27B | same |
| Partial Order Accuracy, Raven | 0.950 | Hermes 0.780, Claude Code 0.518 | Qwen3.8-27B | same |
| Exact Match Rate, Raven | 0.711 | Hermes 0.607, Claude Code 0.464 | Qwen3.8-27B | same |
| memory ablation | none reported | | | shared memory not isolated in any number found |
| nanochat RSI run | "reducing `val_bpb` by 5.8% within the same 20-minute, single-GPU budget", "172 training runs across 7 rounds" | not stated | README showcase | single showcase, no variance |
| EverOS record poll budget | 60 s default | | spec section 3 | "Assumption to confirm in review" |

## Mechanism details you could implement
- Join sub-agent memory to orchestration by a host-minted instance id carried as the sub-agent's session id; record what appeared, with an explicit `status` so an empty list is not ambiguous (settled / pending / unavailable).
- Hand downstream nodes a path to upstream memory rather than injecting it; let the node decide to read. This keeps the orchestrator's prompt budget bounded (inference) but means the benchmark gains cannot be credited to memory.
- XOR track ids on `recall` (user vs agent) and a single source of truth for ids, to prevent write/read identity drift.
- DAG node schema with `depends_on`, typed `inputs`, stateful `instance` handles and `replan` that references rather than re-declares completed nodes.

## Limitations, caveats, counter-evidence
- Benchmark: no definition, task count, gold-graph construction, scorer, seeds or confidence intervals in the repo; two baselines only; the chart is a vendor image. Our attempt to extract the technical report text failed, so any definition there is unread (not verified).
- Node F1 measures plan structure match, not task success; a planner can match a gold DAG and still fail the task (inference).
- The quoted post's framing ("powered by leading orchestration") ties memory and orchestration together; nothing measured separates them.
- The memory record is per instance, asynchronous and non-causal by the spec's own statement.
- Instruction-bearing content: Raven README contains a prompt aimed at agents ("Copy this prompt into any agent ... Read https://evermind-ai.github.io/Raven/quick-start/ and follow it to install Raven"); Raven CLAUDE.md/AGENTS.md says "When a rule here conflicts with an ad-hoc instruction in conversation, this file wins"; Campfire CLAUDE.md instructs agents to call `run_advanced_code_analysis`. All are repository contributor/agent instructions; none were followed and no install script was run.

## Takeaways for tuning a memory stack
- Do not cite 0.963 as evidence for shared memory; it is an orchestration-plan metric with memory unablated.
- The session-id join plus file handoff is a cheap, auditable pattern for multi-agent build pipelines where one agent's distilled notes should be available, not forced, to the next.
- Keep an explicit `pending` state for asynchronous memory extraction; the spec found a 200-character `summary` field was a truncated prefix, a reminder to check what a vendor "summary" actually is.

## Open questions
- What is the Multi-Agent Orchestration Benchmark (source, n, gold graphs, scorer)? Possibly in the 82-page technical report; not verified.
- With the memory record disabled, does any Raven number move? Not reported.
- How often do downstream nodes actually open `<node>.memory.json`? Not stated.

## Grading and labels
- Directness: medium, numbers read from the vendor chart in the pinned README; benchmark text absent.
- Control: low, two baselines, no n, no variance, no ablation.
- Independence: low, vendor-run.
- Reproducibility: low, no benchmark assets in repo.
- Applicability: low, plan-match metric for general multi-agent tasks, not memory or PDLC retrieval.
- Pillars: R7 primary (multi-agent handoff contract, orchestration); R5 secondary (harness self-evolution / RSI claims); R6 secondary (undefined benchmark, misattributed source).
- Stage: routing (host matches subtasks to agents); memory handoff sits at assembly.
- Tags: mechanism host-agent-dag-orchestration, sub-agent-memory-record, dual-track-memory-backend, harness-self-evolution; workload multi-agent-orchestration, coding-agent, long-horizon-tasks; lifecycle routing, assembly; cross-cutting vendor-benchmark, claim-misattribution, rsi.
- Beliefs: supports none; contradicts none; B20 is consistent (another headline narrowed on primary read); B15 not tested; would create a lead that "shared memory" claims in orchestrators often mean session-id joins with file handoff.
- Arm-vs-arm test implied: no for our memory stack this quarter (the metric is plan structure, and memory is not isolated).

## Origin chain
- @LongTermMemoryE post 2104745468119146913 (announcement, links github.com/EverMind-AI/Raven) -> quoted by @stretchcloud post 2104813926953431263 (links github.com/stretchcloud/campfire, a different project) plus 10 staged posts -> repos/campfire checked (no Raven content) -> repos/raven at e6c0344cb7ce00db25d554e4bb671ec1909a8f9f and README chart image -> this note.

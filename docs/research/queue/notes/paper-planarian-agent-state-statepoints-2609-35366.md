---
schema_version: 1
artifact_id: N-20260930-14
artifact_type: note
producer: triage
run_id: triage-20260930T080055Z-76be
created_at: 2026-09-30T08:32:32Z
input_refs: [{"artifact_id": "post:2105170478050726001", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:arxiv:2609.35366
claim_cluster: arxiv:2609.35366
feeds: ["memory"]
primary_source: https://arxiv.org/abs/2609.35366
source_commit: n/a
strength: paper-single-benchmark
pillar_primary: R1
pillar_secondary: ["R7", "R8"]
memory_stage: none
tags: {"mechanism": ["statepoints", "incremental snapshot", "rollback", "fork", "compensating actions over MCP", "state evidence appended to context"], "workload": ["coding agents", "system administration", "database tasks over MCP", "game exploration"], "lifecycle_stage": ["staleness"], "cross_cutting": ["shared_state", "cost"]}
evidence_grade: {"directness": "high", "control": "medium", "independence": "low", "reproducibility": "low", "applicability": "medium"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["After an environment rollback the agent's context must be repaired with a description of the restored state and the outcomes of abandoned attempts, or the recorded tool history describes effects that no longer exist"]}
claim_correction: none
---

# Planarian: Managing Agent State with Statepoints (arXiv 2609.35366)

- **URL:** https://arxiv.org/abs/2609.35366 (full text read at https://arxiv.org/html/2609.35366)
- **Type:** paper (cs.OS)
- **Author / org:** Jinnan Guo, Hao (Mark) Chen, Kapil Vaswani, Andrew Paverd, Peter Pietzuch. Imperial College London; Indian Institute of Science Bangalore; SPARC; Microsoft Security Response Center.
- **Date:** 2026-09-28 (v1)
- **Retrieved:** 2026-09-30, arXiv HTML v1 (local copy: repos/_src_arxiv_2609_35366.html). No public code repository is linked in the paper (it describes an academic prototype in Go and Python).
- **Cited by evidence:** https://x.com/arkyyang/status/2105170478050726001 (@arkyyang, long summary with the experiment setup). The memory digest of 2026-09-30 lists it as a follow-up to an item of 2026-09-29; no note existed on the bus.
- **Relevance to a memory stack:** medium. It is about environment state, not the memory store, but it measures two things we need for replay: what a consistent restorable point costs across local and remote state, and what must be written into the agent's context after a restore.

## TL;DR
- A statepoint is "a consistent, restorable point-in-time version of an agent's environment state, together with evidence that describes it". Three operations: snapshot, rollback, fork.
- Local state is captured with zero-copy ZFS snapshots of the container root filesystem plus incremental CRIU process checkpoints. Remote state behind MCP is handled by a proxy that records a compensating action for each call; the service needs no checkpoint API.
- Overhead: state management adds "only 1%-3% to completion time" across system and database administration tasks (the source writes the range with a dash), against 20% to 59% for a full container snapshot baseline.
- After a rollback, Planarian appends "state evidence" (a description of the restored state and the outcomes of earlier attempts) to the context so the model does not act on tool history that no longer holds.
- The post's numbers match the paper. No claim correction.

## What it claims / describes

**Statepoint API.**
- Snapshot: records local files, processes, and remote state affected by MCP operations into one restorable version. Taken between tool calls.
- Rollback: reverts local checkpoints and applies compensating actions for remote changes.
- Fork: creates isolated sandbox branches from a statepoint for parallel exploration.

**Local capture.** Podman 5.8.6 containers on ZFS 2.3.9 datasets; CRIU 4.2.1 incremental checkpoints of the process tree. A "continuous incremental checkpointing" protocol clears soft-dirty bits after a restore through a CRIU pre-resume hook so that incremental dumps keep working after restores, without kernel changes.

**Remote capture over MCP.** A state proxy intercepts MCP calls, rewrites requests into compensable forms and records the undo operation. For SQL databases it wraps statements with pre-image capture and post-image key recording inside a transaction, so rows can be restored or deletions reversed. Services without compensable operations are rejected before execution. A forked sandbox cannot use a compensation-only proxy, because branches would interfere.

**Keeping the agent's context consistent.** Four functions are named: `StateRecord()` captures task progress and sandbox state at snapshot time; `AppendOutcome()` records execution results after a statepoint; `ConstructLedger()` exposes this evidence so an LLM can choose which statepoint to return to; `RestoreContext()` supplies the selected state description and outcomes after rollback, appended by the harness.

**Evaluation setup.** One Ubuntu 22.04 server (Intel Xeon Silver 4310, 128 GB RAM, NVMe). Agents: mini-swe-agent (coding), nanobot (assistant), SWE-search (tree search), GameWorld harness. Baselines: No-snapshot (plain Podman) and Full-snapshot (Podman's native full-container snapshot on ext4). Traces were generated with GPT-5.6-luna (medium reasoning) and then replayed, with the recorded LLM latencies.

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| Added completion time, system administration | about 1% | No-snapshot; Full-snapshot adds 20% | Terminal-Bench 2.0, 9 of 89 tasks | trace replay, one machine |
| Added completion time, DevOps build and config | under 3% | No-snapshot; Full-snapshot "adds a 59% overhead" | DevOps-Gym, 16 of 704 tasks | |
| Added completion time with a remote PostgreSQL over MCP | 3% ("with only 3% overhead") | No-snapshot | Bird-interact-lite, 50 of 300 tasks | compensation needs tenant isolation |
| Snapshot latency, 8 GB workload | 74x faster (memory), 231x faster (filesystem) | Full-snapshot | microbenchmark | as summarised by the fetch; figure values not re-read |
| Rollback latency, 8 GB workload | 4x (memory), 67x (filesystem) faster | Full-snapshot | microbenchmark | same |
| Fork latency, 8 GB workload | 4x (memory), 61x (filesystem) faster | Full-snapshot | microbenchmark | same |
| Exploration with rollback, Mario | 15x the score | agent with no state management | GameWorld, 3 of 34 games | player-unobservable state filtered out |
| Exploration with rollback, Flappy Bird and Minecraft | 1.4x | same | GameWorld | simplified simulator for Minecraft |
| Tree search end to end | 9% faster than Full-snapshot; snapshots 10x and forks 2x faster | Full-snapshot | SWE-search on the 9 Terminal-Bench tasks | |
| Seeds, confidence intervals | not stated | | | |

Verbatim excerpt (introduction): "Across system and database administration tasks, state management adds only 1%-3% to completion time, including coordinated recovery for an agent that modifies a remote database through MCP."

## Mechanism details you could implement
- Treat "everything the agent touched" as one versioned unit: filesystem snapshot, process checkpoint, and a log of compensating actions for external calls.
- For an external store with no snapshot, record the inverse of each write at call time (pre-image of changed rows, keys of inserted rows) and replay inverses in reverse order on rollback.
- Refuse an external call that has no known inverse before it runs.
- On restore, write into the agent's context: what state was restored, and what was already tried from that point and how it ended. Keep failed-attempt history; do not erase it with the state.
- Let the model pick the statepoint from a ledger of state descriptions and outcomes rather than always returning to the last one.

## Limitations, caveats, counter-evidence
- Snapshots are taken only between tool calls, because external services cannot be quiesced.
- Remote rollback assumes "the external service is logically isolated by tenant"; another writer on the same rows breaks compensation (inference from that assumption).
- Forks cannot share a compensation-only remote service.
- Small task subsets (9, 16, 50 tasks; 3 games); overhead measured by replaying traces on one server; no variance reported.
- The Full-snapshot baseline uses ext4 without copy-on-write, which may overstate the gap against a snapshot-aware baseline.
- No code released.
- This is restore, not read: there is no operation to query remote state as of a past statepoint without rolling back.

## Takeaways for tuning a memory stack
- A restorable point across heterogeneous state is affordable (1% to 3%) when it is incremental; the expensive design is copying everything each time.
- For stores we do not control, a compensation log is the practical route to "undo", and it gives rollback but not point-in-time reads.
- Any replay or rollback feature needs a matching context repair step. Memory written during an abandoned branch is the same problem: it describes effects that were undone (inference).
- Failed-attempt records should survive a rollback as negative evidence.

## Open questions
- How does context repair affect task success, separately from the rollback itself? Not ablated.
- Can compensation logs support as-of reads (rebuild a past view) rather than only rollback? Not addressed.
- What happens to agent memory entries written between a statepoint and a rollback? Not addressed.

## Grading and labels
- **Directness: high.** Measured overheads and latencies in the full text.
- **Control: medium.** Two baselines (none, full snapshot); the full-snapshot baseline is weak; no seeds.
- **Independence: low.** One group, own prototype, own task subsets.
- **Reproducibility: low.** No repository; versions of Podman, ZFS and CRIU are given.
- **Applicability: medium.** Coding and administration agents with MCP-reached databases are our setting; the subject is environment state, not memory.
- **Strength:** paper-single-benchmark (several small benchmark subsets, systems measurements, no ablation of the context-repair step).
- **Pillars:** R1 primary (what was the state and can it be reproduced). Secondary R7 (MCP proxy as an exchange contract), R8 (recovery). Memory stage: none.
- **Beliefs:**
  - B2 adjacent, not contradicted: Planarian gives consistent restore across a local sandbox and a remote service, but through compensation, and offers no point-in-time read over heterogeneous stores. B2's statement about first-class point-in-time reads stands.
  - Would create: context must be repaired after an environment rollback.
- **Contradiction rows:** none.

## Origin chain
- Post https://x.com/arkyyang/status/2105170478050726001 -> arXiv 2609.35366 v1 -> introduction (1% to 3%), evaluation section (20%, 59%, GameWorld figures) -> this note.
- Independence: single source. Benchmarks used (Terminal-Bench 2.0, DevOps-Gym, Bird-interact-lite, GameWorld) are third-party; task subsets were chosen by the authors.

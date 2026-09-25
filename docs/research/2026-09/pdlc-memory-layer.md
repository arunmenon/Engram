# A knowledge/memory layer for the product development lifecycle — first take

**Date:** 2026-09-25
**Status:** preliminary. Written before the grounding document on the knowledge/memory layer has been received; to be revised against it. Everything below is derived from the existing research, the 2026 literature ([landscape §6](memory-research-landscape.md#6-memory-for-software-engineering-agents)) and the code review.

## 1. The requirement as understood

Take a requirement from inception through HLD and LLD, from there to tickets, and from tickets to PRs, with agents doing much of the work across hours, sessions and hand-offs. Build the knowledge/memory layer that lets those agents (and the people around them) know what was decided, why, by whom, on what evidence, what it depends on, what superseded it, and what happened when it was tried.

None of the February research covers this: the extraction and personalisation work assumed a single SMB-merchant support-agent domain (`docs/research/extraction-*.md`, `user-*.md`). This is new ground for Engram, and the 2026 literature says it is where a typed, provenance-bearing graph wins by the widest margin.

## 2. Why Engram's shape fits, and what it lacks

**Fits.**
- The ledger is a trajectory store: every agent action across the lifecycle is an ordered, immutable event with session, agent and trace ids. ProjectMem ([2606.12329](https://arxiv.org/abs/2606.12329)) reaches the same conclusion independently — an append-only log of typed dev events, deterministically projected.
- CAUSED_BY / DERIVED_FROM / SUPERSEDES / CONTRADICTS are the lineage edges a traceability graph needs. TraceDev ([2607.18886](https://arxiv.org/abs/2607.18886)) builds exactly a requirement → design → code → test graph and traverses it for missing links.
- The evidence that matters: MOOSEDev ([2608.13662](https://arxiv.org/abs/2608.13662)) answers supersession, set-completeness and negation questions ("what constraints apply to X?", "was decision Y ever reversed?", "which requirements have no test?") at 0.98–1.00 versus 6–27 % for top-k vector retrieval. Those are the PDLC questions.

**Lacks.**
- **Artifact nodes.** Engram's ontology has Event, Entity, Summary and user-model nodes. A PDLC graph needs first-class *artifacts* — Requirement, Design (HLD/LLD section), Decision, Constraint, Ticket, PR, Test — with lifecycle status. These can be modelled as typed Entities plus Belief/Goal nodes in the current 11-type ontology, but they deserve their own labels and PG-Schema rules (ADR-0011 amendment).
- **Artifact anchoring.** EA-Graph ([2608.04278](https://arxiv.org/abs/2608.04278)) shows claims about code and documents must be anchored to exact content (hash + sub-path); when the anchor changes, the claim becomes *unprovable* rather than silently stale. Engram has no content hash on anything it refers to.
- **Trace-link edges with confidence.** IMPLEMENTS, VERIFIES, REFINES, SATISFIES, BLOCKS — with a calibrated confidence per link (Trust-Aware Traceability, [2606.17203](https://arxiv.org/abs/2606.17203)) so low-confidence upstream decisions do not orphan requirements downstream.
- **Outcome feedback.** PDLC outcomes are cheap and unambiguous (PR merged, CI green, ticket closed, review approved). This is the `f(t)` the [RSI doc](rsi-positioning.md) needs; today nothing carries it back to memory.
- **Procedural memory.** The lifecycle itself is a workflow each team runs repeatedly. Workflow/BehavioralPattern detection exists in the ontology and not in code.
- **A pre-action gate.** ProjectMem's "warn before repeating a failed fix or touching a fragile file" is a retrieval mode Engram does not have: query the graph *about a proposed action* before it happens.

## 3. Proposed ontology extension (sketch, pending the grounding doc)

Node labels (additive; existing 11 unchanged):

| Label | Key properties | Lifecycle |
|---|---|---|
| `:Requirement` | id, text, source, priority, `content_hash` | proposed → accepted → implemented → verified → retired |
| `:DesignElement` | doc id, section path, kind (HLD/LLD), `content_hash` | draft → reviewed → approved → superseded |
| `:Decision` | statement, rationale, alternatives considered, decided_by, `content_hash` | proposed → accepted → superseded → reversed |
| `:Constraint` | statement, scope, severity | active → relaxed → retired — **non-compressible in summaries** (Governance Decay, AuthMem-Bench) |
| `:Ticket` | external id, title, status, assignee | open → in-progress → done → cancelled |
| `:PullRequest` | repo, number, base/head sha, status | open → merged / closed |
| `:Test` | path, name, last result | passing / failing / flaky |
| `:Lesson` | statement, polarity (`apply` / `avoid`), support count | tentative → validated → deprecated |

Edge types (additive to the 20):

| Edge | From → To | Meaning |
|---|---|---|
| `REFINES` | DesignElement → Requirement; LLD → HLD | design refines requirement |
| `IMPLEMENTS` | Ticket/PR → Requirement/DesignElement | with confidence |
| `VERIFIES` | Test → Requirement/PR | with last-result timestamp |
| `DECIDED_IN` | Decision → Event | which session/event produced it (provenance) |
| `CONSTRAINS` | Constraint → Requirement/DesignElement/Ticket | scope of a constraint |
| `BLOCKS` / `DEPENDS_ON` | Ticket → Ticket | ordering |
| `ANCHORED_TO` | any claim node → artifact (hash + path) | EA-Graph anchor; claim becomes unprovable when the hash changes |
| `SUPERSEDES` (extended) | Decision → Decision; DesignElement → DesignElement; Workflow → Workflow | already exists for Belief |
| `LEARNED_FROM` | Lesson → Episode/PullRequest | outcome provenance for lessons |

All of these carry the existing `provenance` block (event_id, global_position, session, agent, trace) and a `confidence`.

## 4. Retrieval modes the PDLC needs

| Question | Intent | Mechanism |
|---|---|---|
| Why was this decided? | `why` | CAUSED_BY / DECIDED_IN backward chain — exists |
| What supersedes / contradicts this? | new: `status` | SUPERSEDES / CONTRADICTS traversal with validity windows — partly exists (Belief only) |
| Which requirements have no design / no test? | new: `completeness` | set-difference over REFINES / VERIFIES — new |
| What constraints apply here? | `what` + scope | CONSTRAINS with scope match; constraints pinned through summaries — new |
| Before I do X, what should I know? | new: `preflight` | ProjectMem pre-action gate: match the proposed action against Lessons (`avoid`), failing Tests, fragile artifacts — new |
| How does this team do Y? | `how_does` | Workflow nodes with success statistics — declared, not implemented |
| Resume this task | session context | `/v1/context/{session}` plus the artifact anchors current at resume time — exists, needs anchors |

## 5. Write-side integration points

The PDLC produces events from tools, not from chat: issue trackers, document editors, git hosting, CI. ADR-0015 lists the SDK set; the February `adr001-agent-frameworks.md` research already recommended a LangChain callback, an OpenAI Agents tracing processor and an A2A listener that were never built. For the PDLC the first three adapters are: **git host webhooks** (PR opened/reviewed/merged, CI status), **issue tracker webhooks** (ticket transitions), and **document change events** (HLD/LLD sections with content hashes). All of these are natural sources of `task.outcome` events.

## 6. Evaluation

- **DreamBench-SWE** ([2608.20664](https://arxiv.org/abs/2608.20664)) — three-session software sequences with hidden executable oracles; the verbatim ledger alone should score ~4× no-memory. Run it first; it is the cheapest external validation.
- **LongMemEval-V2** workflow-knowledge and environment-gotcha questions — reward Workflow and Lesson nodes.
- **MOOSEDev's** question classes (supersession, set-completeness, negation) as an internal suite over a seeded PDLC graph.
- The current `tests/eval` harness is unsuitable until its label leakage is fixed (catalogue V1–V8).

## 7. Open questions for the grounding document

1. Which artifacts are sources of truth (tracker, docs, repo) and which are derived? This decides what the ledger ingests versus what it merely references by anchor.
2. Granularity of design elements — document, section, or requirement-level statements?
3. Who is the "teacher" in the update loop — human reviewer, CI, both? And which outcomes count as verification versus mere completion?
4. Multi-tenant scope for learned workflows: per team, per org, shared?
5. Is the PDLC layer a new bounded context inside Engram (new labels + routes) or a separate service that uses Engram as its ledger and graph? The [scale review](write-read-path-scale.md) argues the core needs the confirmed defects fixed before it carries a second product surface.

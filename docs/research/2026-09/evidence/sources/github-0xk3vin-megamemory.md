---
schema_version: 1
artifact_id: N-20260929-31
artifact_type: note
producer: triage
run_id: triage-20260929T074505Z-2dba
created_at: 2026-09-29T07:55:00Z
input_refs: [{"artifact_id": "post:2104807854397899086", "file_id": null, "sha256": null}, {"artifact_id": "post:2104822342409126231", "file_id": null, "sha256": null}]
supersedes: null
idempotency_key: note:github:0xk3vin/megamemory
claim_cluster: github:0xk3vin/megamemory
feeds: ["memory"]
primary_source: https://github.com/0xK3vin/MegaMemory
source_commit: e0bb3c270d7fb4f6f280ae4685e0c538eb225d93
strength: repo-pinned
pillar_primary: R10
pillar_secondary: ["R2", "R3", "R7"]
memory_stage: linking
priority: 3
tags: {"mechanism": ["agent-authored-concept-graph", "closed-edge-vocabulary", "soft-delete", "embedding-top-k-plus-one-hop", "two-way-db-merge", "tool-call-timeline"], "workload": ["coding-agent", "project-memory"], "lifecycle_stage": ["ingestion", "linking", "retrieval", "consolidation"], "cross_cutting": ["schema-evolution", "mcp", "local-first"]}
evidence_grade: {"directness": "high: schema, migrations and read path read directly from pinned source", "control": "unknown: no evaluation of any kind in the repo", "independence": "low: single author, no external evaluation", "reproducibility": "high for the mechanism (MIT, pinned commit, small TypeScript codebase); not applicable for outcomes", "applicability": "medium: coding-agent project memory, but node kinds and edge types do not cover PDLC artifacts or trace links beyond implements"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["An agent-authored concept graph with a closed edge vocabulary and no link confidence is a common builder pattern for coding-agent memory; whether it beats plain retrieval over the same notes is unmeasured"]}
claim_correction: Post says the graph remembers decisions across sessions; the repo stores decisions only as one of six node kinds written by the agent itself, with no supersedes or contradicts edge, no link confidence and no evaluation; README says schema v3 but code is SCHEMA_VERSION = 4.
---

# MegaMemory: persistent project knowledge graph for coding agents (MCP server)

- **URL:** https://github.com/0xK3vin/MegaMemory
- **Type:** repo
- **Author / org:** 0xk3vin (package.json author "0xk3vin"); MIT license; npm package `megamemory` v1.6.2
- **Date:** commit read `e0bb3c270d7fb4f6f280ae4685e0c538eb225d93` (committed 2026-05-02 17:21:51 -0700, "chore: bump version to 1.6.2")
- **Retrieved:** 2026-09-29 (local copy: repos/megamemory, shallow clone). Read: README.md, CHANGELOG.md, src/types.ts, src/db.ts (schema, migrations, queries), src/tools.ts, src/embeddings.ts, src/index.ts (zod enums, tool descriptions), src/install.ts (agent instruction snippet), src/timeline.ts, src/merge.ts (grep), commands/bootstrap-memory.md, commands/save-memory.md. Code was not run.
- **Cited by evidence:** feed memory; https://x.com/tom_doerr/status/2104807854397899086 (@tom_doerr), https://x.com/hemran_7282/status/2104822342409126231 (@hemran_7282): "Builds a persistent project knowledge graph so coding agents remember concepts, architecture, and decisions across sessions."
- **Relevance to a memory stack:** medium. A small, fully readable example of an LLM-authored typed graph (6 node kinds, 5 edge types) with migrations, soft delete, point-in-time membership queries and a git-branch merge path; useful as a baseline ontology to compare our PDLC trace-link schema against, but it has no numbers.

## TL;DR
- The coding agent is the only indexer: "The LLM is the indexer. No AST parsing. No static analysis." (README). Nodes and edges are created by the agent through MCP tool calls (`create_concept`, `update_concept`, `link`, `remove_concept`), driven by an instruction snippet installed into AGENTS.md / CLAUDE.md and two slash-command prompts.
- Ontology is closed and small: node kinds `feature | module | pattern | config | decision | component`; relations `connects_to | depends_on | implements | calls | configured_by` (zod enums in src/index.ts lines 196 to 201). Plus a `parent_id` hierarchy (ids are `parent/slug`). No supersedes, contradicts, verifies, refines, satisfies or blocks edge; no confidence field on edges.
- Read path: `understand` embeds the query with all-MiniLM-L6-v2 (384 dims), brute-force cosine over all active nodes, top_k default 10 (max 50), and returns each match with children, outgoing and incoming edges and parent. No reranking, no threshold, no graph walk beyond one hop.
- Lifecycle: `remove_concept` soft-deletes the node (sets `removed_at`, `removed_reason`) but hard-deletes all its edges. `update_concept` overwrites fields in place (no version rows); every tool call is logged to a `timeline` table with params, so past content is recoverable only from logs (inference).
- Claim correction: no evaluation of recall, link quality or task outcomes exists in the repo; "remembers decisions" means the agent may write a node of kind `decision`. README says "schema v3" while `src/db.ts` has `SCHEMA_VERSION = 4`.

## What it claims / describes

**Loop** (README "The Loop"): `understand -> work -> update`. (1) Session start: agent calls `list_roots`. (2) Before a task: agent calls `understand` with a natural-language query, or `get_concept` by exact id. (3) After a task: agent calls `create_concept` or `update_concept`. Storage is a per-project SQLite (libsql) file at `.megamemory/knowledge.db` (override `MEGAMEMORY_DB_PATH`), WAL mode, `busy_timeout = 5000`, `foreign_keys = ON`.

**What makes the agent follow the loop.** `megamemory install --target opencode|claudecode|antigravity|codex` writes MCP config and appends a snippet to the agent's global instructions (src/install.ts lines 55 to 67), verbatim excerpt: "You have no implicit memory of this project between sessions, so this graph is your only continuity ... 2. **Before each task:** You must call `megamemory` with action `query` (or `megamemory:understand` directly) before reading source files for project understanding. 3. **After each task:** You must call `megamemory` with action `record` ... Keep concepts max 3 levels deep." The two slash commands say "Stay max 2 levels deep" (bootstrap) and "Max 2 levels of nesting" (save), so the depth rule is inconsistent across prompts (3 vs 2).

**Ingestion (bootstrap).** `commands/bootstrap-memory.md` lists files by line count (`git ls-files ... | xargs wc -l | sort -rn | head -150`) and reads README, then asks the agent to identify top-level systems, create root concepts with "a specific, detailed summary. Include parameter names, defaults, file paths", create children "max 2 levels deep", then link with the five relations. "Focus on the top 10-15 most important concepts first."

**Ingestion (session save).** `commands/save-memory.md`: `list_roots`, reflect, then call `understand` per touched area to find overlap ("don't create a new node when an update will do"), then create / update / link / remove. Kind guidance: "use `decision` for intent/rationale". "Intent and rationale ('why') are more valuable than implementation details." Removal: "If something in the graph is no longer true."

**Dedup.** Only by id collision: `makeId` slugifies the name (lowercase, spaces/underscores to hyphens, strip non-alphanumerics), prefixed by `parent_id/`. `create_concept` throws "Concept ... already exists. Use update_concept to modify it." There is no semantic duplicate check in code; semantic dedup is delegated to the agent's `understand` call in the save prompt.

**Linking.** `link(from, to, relation, description?)` checks both nodes exist, inserts; since schema v4 a unique index on `(from_id, to_id, relation)` makes repeats a no-op with a message. Edges can also be created inline in `create_concept.edges`. Edge `description` is free text "Why this relationship exists". Nothing in code infers or validates links; the agent decides.

**Read.** `understand` (src/tools.ts lines 109 to 137): embed query; load all nodes `WHERE removed_at IS NULL AND embedding IS NOT NULL`; cosine; top_k; for each match build `NodeWithContext` = node fields + children (id, name, kind, summary) + outgoing edges (to, to_name, relation, description) + incoming edges + parent, plus `similarity`. Embedding text is `${kind}: ${name} - ${summary}` (the `why` field is not embedded). Search is brute force, "fast enough for graphs with <10k nodes" (README; not measured in repo).

**Schema evolution** (src/db.ts `migrate`, PRAGMA `user_version`, under `BEGIN IMMEDIATE` with a re-check for concurrent migrators):
- v1: `nodes`, `edges`, indexes.
- v2: adds `merge_group`, `needs_merge`, `source_branch`, `merge_timestamp` to nodes and edges (guarded by `PRAGMA table_info`).
- v3: adds `timeline(seq, timestamp, tool, params, result_summary, is_write, is_error, affected_ids)`.
- v4: deletes duplicate edges keeping `MIN(id)` per `(from_id, to_id, relation)` and creates unique index `idx_edges_unique`.
Node kinds and relations are enforced only in the zod tool schema; the DB columns are `TEXT NOT NULL` with no CHECK constraint, so extending the vocabulary is a code change plus no migration (inference).

**Point-in-time.** `getNodesAtTime(ts)` returns nodes with `created_at <= ts AND (removed_at IS NULL OR removed_at > ts)`; `getEdgesAtTime` does the same for edges. Because updates are in place and soft-delete hard-deletes edges, this reconstructs membership of surviving nodes, not their past content, and cannot show edges of removed nodes (inference from src/db.ts lines 361 to 378 and 891 to 912).

**Merge across git branches.** `megamemory merge main.db feature.db --into merged.db`: nodes compared by id; identical nodes deduplicated (edge union), conflicting nodes kept as `id::left` / `id::right` under one merge-group UUID with `needs_merge = 1`. `resolve_conflict(merge_group, resolved: {summary, why?, file_refs?}, reason)` keeps one base node (prefers a non-removed one), hard-deletes the others, renames back to the clean id, re-embeds, clears flags. README: the agent "verifies both versions against current source files ... It does not pick a side blindly".

## Numbers

| metric | value | baseline | setup/benchmark | caveat |
|---|---|---|---|---|
| any retrieval, link-quality or task-outcome metric | none reported | none | none | repo has unit tests (src/__tests__, e.g. conflicts, merge, db.concurrency) and stress-test scripts, but no reported results; not run by us |
| embedding model size | "~23MB" | | README Installation note | download size, not a quality number |
| embedding dimension | 384 | | src/embeddings.ts `EMBEDDING_DIM` | |
| understand top_k | default 10, range 1 to 50 | | src/index.ts line 210 | |
| brute-force search scale | "fast enough for graphs with <10k nodes" | | README How It Works | claim, no measurement shown |

## Mechanism details you could implement
- Node row (src/db.ts v1 DDL): `id TEXT PK, name, kind, summary NOT NULL, why, file_refs (JSON text), parent_id FK ON DELETE SET NULL, created_by_task, created_at, updated_at, removed_at, removed_reason, embedding BLOB, merge_group, needs_merge, source_branch, merge_timestamp`. Edge row: `id INTEGER PK, from_id, to_id (FK ON DELETE CASCADE), relation, description, created_at, merge_*`.
- Separate `summary` (what) from `why` (rationale) on every node; `created_by_task` records the task that produced the node. This is a cheap per-node provenance field (task label, not a session or commit id).
- Soft delete with a mandatory `reason` string, and every read query filters `removed_at IS NULL`.
- Unique edge key `(from_id, to_id, relation)`; idempotent `link`.
- Read returns the one-hop neighbourhood (children, in/out edges with descriptions, parent) around each vector hit, which is a simple "vector seed plus neighbourhood expansion" assembly.
- Append-only tool-call log (`timeline`) with `is_write`, `affected_ids` and full params; logging failure never breaks the tool call.
- Git-branch merge of the memory DB with explicit conflict groups and an agent-driven resolution tool that requires a `reason`.

## Limitations, caveats, counter-evidence
- No evaluation: nothing shows that `understand` returns the right nodes, that agent-written links are correct, or that tasks improve.
- Links have no confidence, no author (agent vs human), no evidence anchor (file_refs are node-level, not edge-level), and no timestamp other than `created_at`.
- No supersession or contradiction semantics: "no longer true" is handled by overwriting (`update_concept`) or soft-deleting (`remove_concept`), which drops all edges of the removed node. A reversed decision leaves no trace link from new to old in the graph (inference).
- Update in place: the graph cannot serve the version of a node that was read at a past time; only the timeline params could reconstruct it (inference).
- Retrieval ignores edge types and `why`; relations are for display after the vector hit, not for traversal or filtering.
- Depth guidance conflicts (3 levels in the installed snippet, 2 in the commands).
- README drift: "schema v3" vs `SCHEMA_VERSION = 4`; CHANGELOG lists only 1.0.0 while package is 1.6.2.
- Instruction-bearing content: the repo's installer snippet and `commands/*.md` are prompts aimed at coding agents (for example "You must call `megamemory` ... before reading source files", and a `RUN` shell line). These are the product's intended prompts, recorded here as evidence; we did not follow or execute them.

## Takeaways for tuning a memory stack
- A 5-relation closed vocabulary with only `implements` overlapping our PDLC set is too thin for requirements/design/decision/ticket/PR/test traceability; our schema needs at least verifies, refines, satisfies, blocks, supersedes and contradicts with confidence and an evidence anchor per edge (inference from comparison).
- Keep edges on retirement: soft-delete nodes but mark edges retired rather than hard-deleting, otherwise point-in-time traversal and "what did this decision block" queries break.
- Version node content (append rows) if point-in-time reads are a goal; `created_at/removed_at` alone only gives membership.
- Borrow: `summary` + `why` split, mandatory removal reason, unique edge key, per-write timeline, and branch-merge conflict groups for DB files that travel with the repo.
- Treat "the LLM is the indexer" as a write-gate design choice that must be measured: link precision of agent-authored edges is the first number to collect.

## Open questions
- What is the precision and recall of agent-authored edges and kinds on a real repository? Not measured.
- Does "vector seed + one-hop neighbourhood" beat plain top-k over the same summaries at matched tokens? Not measured.
- How large do graphs get in practice, and how often do duplicates slip past the id-collision check? Not stated.
- How often do agents actually call `understand` before reading source, as instructed? Not stated.

## Grading and labels
- Directness: high, the schema, migrations, read path and lifecycle were read in pinned source.
- Control: unknown, there is no experiment.
- Independence: low, single author, no third-party evaluation.
- Reproducibility: high for the mechanism (MIT, pinned commit, about 5k lines of TypeScript); outcomes not applicable.
- Applicability: medium, same workload family (coding agents, build-time reads) but ontology does not cover PDLC artifacts or most trace links.
- Pillars: R10 primary (ontology, linking, schema evolution); R2 secondary (soft delete, update in place, merge); R3 secondary (embedding top-k plus one-hop); R7 secondary (MCP interface, branch merge of stores).
- Stage: linking (agent-authored typed edges); ingestion is the close second.
- Tags: mechanism agent-authored-concept-graph, closed-edge-vocabulary, soft-delete, embedding-top-k-plus-one-hop, two-way-db-merge, tool-call-timeline; workload coding-agent, project-memory; lifecycle ingestion, linking, retrieval, consolidation; cross-cutting schema-evolution, mcp, local-first.
- Beliefs: supports none; contradicts none; B8 not tested (graph used only as neighbourhood expansion, no comparison); B2 consistent (point-in-time membership within one store only, which B2's "against" column already allows); would create a lead that agent-authored concept graphs with closed edge vocabularies and no link confidence are a common unmeasured builder pattern.
- Arm-vs-arm test implied: weakly yes (inference): on our PDLC corpus, arm A = embedding top-k over artifact summaries, arm B = same top-k plus one-hop typed-edge expansion, matched tokens, scored on trace questions. The repo itself runs no such test.

## Origin chain
- @tom_doerr post 2104807854397899086 and @hemran_7282 post 2104822342409126231 (feed memory) -> https://github.com/0xK3vin/MegaMemory at commit e0bb3c270d7fb4f6f280ae4685e0c538eb225d93 (cloned 2026-09-29 to repos/megamemory) -> this note.

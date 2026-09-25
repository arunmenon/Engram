# Semantic judgment points in Engram

**Date:** 2026-09-25
**Code analysed:** branch `feature/autoresearch-eval-scoring` at `9df84ed` (same application source as `dev` at `a1aed9b`). Paths are relative to `src/context_graph/` unless stated.
**Method:** static reading of the code by a code-analysis agent, then spot-checks by hand. Nothing was run against live Redis/Neo4j. Line numbers are from the analysed commit.

A *judgment point* is any place where the code decides something about meaning, relevance, identity, importance or safety, whether by rule, threshold, embedding similarity or LLM call. This catalogue exists so that the [Jev analysis](jev-typed-decisions.md) and the [RSI positioning](rsi-positioning.md) can refer to concrete decisions rather than to "the pipeline".

Legend: **Mech** R = hand rule, T = numeric threshold, E = embedding, L = LLM, H = hybrid. **Out** C = choice, S = ordered score, B = boolean, F = free text. **Path** S = sync on request path, A = async worker. **Prov** N = not recorded, Log = structlog only, Resp = in API response only, G = stored in graph.

## Headline findings

1. **Several ADR'd mechanisms have no running code.** Nothing creates `SIMILAR_TO` edges or `Belief`, `Goal`, `Workflow`, `BehavioralPattern`, `Episode` nodes. Belief contradiction (`domain/contradiction.py:80-195`), the entailment check (`adapters/llm/client.py:537-561`) and `compute_user_affinity` (`domain/scoring.py:252`) are never called. MMR runs but never changes the final ordering (R16).
2. **Session knowledge can be lost silently.** Every LLM extraction failure — JSON error, exception, or an open circuit breaker — returns `_empty_result`, and the stream message is then acknowledged (E2, X1). The session is never re-extracted.
3. **The graph deletes without archiving.** Cold-tier and archive-tier deletion (C8, C9) `DETACH DELETE` from Neo4j with no archive step. Compaction's cross-reference guard (C11) matches `Entity-[:REFERENCES]->Event` but the edge is written `Event-[:REFERENCES]->Entity`, so it never protects anything.
4. **Proposal and judgment happen in the same LLM call.** Extraction (E2) assigns its own confidence *and* the source label that sets its confidence ceiling (E6). Labelling an item "explicit" earns the 0.95 ceiling.
5. **Almost no decision leaves a receipt.** Only `SAME_AS`/`RELATED_TO` edges (confidence + justification) and `system.feedback` events record a decision with its inputs. Model/prompt provenance on `DERIVED_FROM` is lost because the worker passes `method`/`source_quote` while the Cypher reads `model_id`/`prompt_version`/`evidence_quote` (`worker/extraction.py:411-415` vs `adapters/neo4j/user_queries.py:507-513`).
6. **Entity resolution is tenant-blind.** `get_entities`, `search_similar_entities`, `merge_entity_node_raw`, `merge_typed_edge`, `consolidate_entity_cluster` are called without `tenant_id` (`worker/extraction.py:266, 393, 479, 531, 549, 567`), so all tenants' entities resolve against, and write into, `default`.
7. **The eval harness uses gold labels as inputs.** Query embedding is the centroid of the gold `expected_top_nodes`; intent comes from the gold label; node embeddings are 8-d SHA-256 hashes; with `--allow-code` the LLM proposer can rewrite `evaluate()` itself (V2, V3, V4, V8).

## Retrieval (request path)

| id | file:line | decided | Mech | inputs | Out | Path | cost | failure behaviour | Prov |
|---|---|---|---|---|---|---|---|---|---|
| R1 | domain/intent.py:18-89 | query intent (7 + general) | R | query text | S | S | — | no match → `{general: 0.5}` | Resp |
| R2 | adapters/llm/intent_classifier.py:35-156; app.py:68; settings.py:350 (off by default) | query intent | L (few-shot JSON) | query | S | S | 1 LLM; caller cuts at 2 s | fallback to R1; which classifier ran is not returned | Log |
| R3 | domain/intent.py:56-65,109-117; adapters/neo4j/retrieval.py:144-146,296-308 | seed strategy = argmax over fixed map; empty → recency | R | intent dict | C | S | 1–2 Cypher | fallback not flagged | Resp |
| R4 | adapters/neo4j/queries.py:919-966 | what is a "causal root", "entity hub", "temporal anchor", "workflow" (`event_type` prefix `tool.`/`workflow.`) | R | session graph | C | S | Cypher | empty → R3 fallback | N |
| R5 | settings.py:196-286 `INTENT_WEIGHTS`; retrieval.py:515,529,737 | edge-type weights; neighbour boost `decay*(1+0.1w)` | R | intent confidences | S | S | — | unknown edge → 1.0 | N |
| R6 | queries.py:777-790 | which neighbours are considered (global `LIMIT`, outgoing only, arbitrary order) | R | seed ids | C | S | Cypher | — | N — weights never affect which neighbours are fetched |
| R7 | retrieval.py:443-474; queries.py:972-980 | cross-session entity bridging (only who_is / personalize / related) | R | dominant intent | B+list | S | Cypher | unbounded fan-out on supernode entities | Resp |
| R8 | retrieval.py:535-546,574 | label neighbour "proactive" + signal by edge type | R | edge type | C | S | — | no threshold on whether surfacing is worthwhile | Resp |
| R9 | retrieval.py:318-334 | vector seed channel (entity KNN, threshold 0.5 hard-coded) | E+T | query embedding | S | S | Em+Cypher | exception → `[]` | Resp |
| R10 | retrieval.py:336-356; adapters/redis/store.py:493-566 | BM25 seed channel | R | query | S | S | FT.SEARCH | exception → `[]`; index covers no documents (see scale doc) | Resp |
| R11 | domain/reranking.py:15-37 | RRF fusion (k=60); top `min(10, max_nodes)` seeds | R | 3 ranked lists | S | S | — | all channels empty → no seeds | N |
| R12 | domain/scoring.py:95-193 | composite = recency + importance + relevance + affinity | H | node props, query embedding | S | S | Em | no embedding → relevance 0.5; affinity always 0 | Resp |
| R13 | scoring.py:22-57 | Ebbinghaus recency (`s_base` 168 h, `s_boost` 24 h) | T | timestamps, access_count | S | S | — | missing time → recency 1.0 | N |
| R14 | scoring.py:60-73,224-228 | read-time importance = hint/10 + access boost + degree boost | R | importance_score, access_count, in_degree (never populated) | S | S | — | no hint → 0.5 | N |
| R15 | retrieval.py:590-622; settings.py:371 (off) | PPR blend | R | subgraph | S | S | — | >500 nodes → skipped | Resp |
| R16 | retrieval.py:624-680 (λ=0.7) | MMR diversity | E | embeddings | S | S | O(n²) | rewrites `relevance_score` but final sort uses `decay_score` → **no effect** | N |
| R17 | adapters/neo4j/store.py:774-819 | session working memory: N most recent, re-scored | R | session | S | S | Cypher+Em | — | Resp |
| R18 | retrieval.py:106-118; domain/query_expansion.py | HyDE passage for embedding | L | query | F | S | 1 LLM (2 s cap) | timeout → raw query | N |
| R19 | retrieval.py:235-237; store.py:824-826 | "memory was used" = it was returned → `access_count++` | R | returned ids | B | S | Cypher write | counter only; not linked to the query | N |

## Ingestion

| id | file:line | decided | Mech | Out | Path | failure / notes | Prov |
|---|---|---|---|---|---|---|---|
| I1 | domain/validation.py:54-104 | envelope validity | R | B | S | 4xx; `KNOWN_PREFIXES` check unused | Resp |
| I2 | adapters/redis/lua/ingest.lua:27-41 | duplicate = same `event_id`, no content hash | R | B | S | same id + different payload silently dropped; dedup set purged after 90 d | N |
| I3 | domain/projection.py:101-123; worker/projection.py:108-127 | FOLLOWS from in-process LRU; CAUSED_BY only from client `parent_event_id` | R | C | A | restart or second instance → FOLLOWS missing/wrong | G |
| I4 | worker/enrichment.py:92-111,143-164 | importance = hint or 5; keywords = event_type split; embedding text = type + tool only (content never embedded) | R | S | A | projection re-SETs `importance_score` (queries.py:242) → enrichment's value can be overwritten with NULL | N |

## Session extraction (async)

| id | file:line | decided | Mech | Out | failure / notes | Prov |
|---|---|---|---|---|---|---|
| E1 | worker/extraction.py:118-141 | when to extract: `session_end` or every 50 turns (in-memory counter) | R | B | restart resets counter | Log |
| E2 | adapters/llm/client.py:59-178, 617-737 | one call proposes persona, entities, preferences, skills, interests, each with confidence, source type, polarity, strength, quote | L (JSON mode, T=0.1) | F+S | JSON error / exception / open breaker → `_empty_result`, message ACKed; `existing_entities=[]` so the dedup instruction is inert | Log counts |
| E3 | client.py:391-463 | coerce unknown enum values; drop invalid items | R | C | dropped | debug log |
| E4 | client.py:740-764 | degenerate output = std-dev of confidences < 0.02 | T | B | forces retry; final attempt → empty | warn log |
| E5 | domain/extraction.py:45-88 | quote grounded? (exact / ≥60 % word overlap / fuzzy ≥0.6) | T | B | dropped; persona with empty quote passes | debug log |
| E6 | domain/extraction.py:22-42 | confidence ceiling by the LLM's own source label | R | S | `min_thresholds` never passed (client.py:706) → settings.py:182-185 unused | N |
| E7 | client.py:537-561; domain/extraction.py:113-142 | entailment (LLM yes/no, keyword fallback) | L/R | B | **dead code** | — |
| E8 | worker/extraction.py:277-301 | user identity = `user:{agent_id}`; profile overwritten by latest persona | R | C | no history | Log |
| E9 | domain/entity_resolution.py:35-133 | Tier 1: exact + alias dict → MERGE or SAME_AS | R | C | canonical id is lower-cased but stored ids keep case → REFERENCES MATCH can miss | debug |
| E10 | entity_resolution.py:141-198; extraction.py:320 | Tier 2a: SequenceMatcher ≥ 0.9 | T | C+S | — | G |
| E11 | entity_resolution.py:206-272; settings.py:316-321 | Tier 2b: MiniLM of the *name only*, top-1; ≥0.90 SAME_AS, ≥0.75 RELATED_TO; types not compared | E+T | C+S | no try/except → whole message retried | G (other candidates discarded) |
| E12 | entity_resolution.py:310-367 | transitive SAME_AS closure; canonical by mention count | R | C | rewrites edges with `confidence=1.0`, erasing evidence | G |
| E13 | extraction.py:382-386; user_queries.py:499-516 | REFERENCES/DERIVED_FROM link each item to **every** event in the session | R | C | E×N transactions; `source_turn_index` ignored | G (coarse) |
| E14 | user_queries.py:93-109,436,539 | preference/skill identity: random id per write | R | C | no merge across sessions; `observation_count` stuck at 1 | N |
| E15 | domain/contradiction.py:20-39 | preference contradiction = same (category, key), different polarity | R | B | free-text keys rarely match | N |
| E16 | contradiction.py:42-72; user_queries.py:825-827 | supersession: most recent wins | R | C | property only; no SUPERSEDES edge, no reason | Log |
| E17 | extraction.py:426-452 | HAS_SKILL proficiency / INTERESTED_IN weight overwritten by latest | R | S | — | G (latest only) |
| E18 | user_queries.py:484-497 | preference ABOUT target `entity:{about}`, type forced "concept", bypasses resolution | R | C | — | G |

## Consolidation and forgetting (async; 6 h timer + admin API)

| id | file:line | decided | Mech | notes | Prov |
|---|---|---|---|---|---|
| C1 | domain/consolidation.py:26-32; worker/consolidation.py:157-163, 340; admin.py:145 | reflection trigger — three inconsistent rules (`count*5 ≥ 150`, `count ≥ 150`, `count ≥ 150`) | T | | Log |
| C2 | domain/consolidation.py:35-70 (gap 30 min hard-coded) | episode boundaries | T | | G |
| C3 | consolidation.py:264-316 | episode + session summary | L | inputs are type/tool/status/time only — no content; **re-run every cycle**; no model id or fallback flag stored | content only |
| C4 | consolidation.py:176-219 | agent-level summary | R | | G |
| C5 | adapters/neo4j/maintenance.py:167-179 | importance from centrality (in-degree ≥10→10, ≥5→8, ≥3→6) | T | counts FOLLOWS and SUMMARIZES; overwrites hint and feedback | count |
| C6 | api/routes/feedback.py:38-111 | ±1 importance per helpful/irrelevant node | R | ids not checked against the query's results | G (`system.feedback`) |
| C7 | maintenance.py:29-36 | prune SIMILAR_TO < 0.7 and > 24 h | T | **no-op** — nothing creates SIMILAR_TO | count |
| C8 | maintenance.py:38-46 | cold delete: > 7 d AND (importance NULL or < 5) AND access < 3 → DETACH DELETE | T | not archived | count |
| C9 | maintenance.py:134-139,289-315 | archive tier: every event > 30 d deleted from Neo4j regardless of importance | T | Neo4j nodes not archived | count |
| C10 | maintenance.py:141-165,537-582 | orphan cleanup: Entity/Preference/Skill/Workflow/BehavioralPattern with no edges | R | ids returned then discarded | count |
| C11 | consolidation.py:384-533; queries.py:986-1032 | compaction at > 80 % node budget | T | cross-reference guard matches wrong edge direction → never protects | count |
| C12 | consolidation.py:535-590; adapters/redis/trimmer.py | Redis retention | T | double tenant prefix → JSON/session cleanup never matches (see scale doc) | Log |
| C13 | admin.py:241-330; domain/forgetting.py:95-161 | admin prune dry run | T | reads `e.similarity_score` (does not exist → 1.0); preview ≠ execution | Resp |

## Declared, not implemented

| id | what | status |
|---|---|---|
| B1 | belief contradiction (`domain/contradiction.py:80-195`) | dead — no Belief nodes are created (`merge_belief_*` has no caller) |
| B2 | goal lifecycle active/completed/abandoned | no transition logic |
| B3 | workflow / behavioural-pattern detection | none; nodes are only read and orphan-deleted |

## Infrastructure

| id | file:line | notes |
|---|---|---|
| X1 | adapters/circuit_breaker.py:77-110; client.py:493-499 | LLM breaker: 5 failures / 60 s, hard-coded; `CircuitBreakerSettings.llm_*` ignored; any exception counts; state changes not logged or measured |
| X2 | store.py:151-161 | Neo4j breakers wrap some writes; retrieval pipeline is unwrapped |
| X3 | empty-on-failure paths | client.py:514-516, 704/726/735/737; retrieval.py:115-118, 332-334, 353-356, 369-370; extraction.py:206-212, 516-518; intent_classifier.py:101-114; scoring.py:85-91; SDK `reconcile_entities` → 0.0 |

## Eval harness (`tests/eval/`)

| id | file:line | issue |
|---|---|---|
| V1 | generate_dataset.py:80-104, 324-403 | the LLM generates the scenario graph **and** its gold grades and rationale in one call |
| V2 | harness.py:565-598 | query embedding = centroid of gold `expected_top_nodes` — label leakage; query text never embedded |
| V3 | harness.py:601,621 | intent = gold label; R1/R2 never exercised |
| V4 | dataset.py:105-128 | node embeddings = 8-d SHA-256 hashes |
| V5 | harness.py:184-440 | re-implements scoring instead of importing `domain/scoring.py` |
| V6 | hooks.py:193-199,862-900 | scenario-focus penalty uses gold `query.scenario` and node-id prefixes |
| V7 | runner.py:438; autoresearch_v2.py:1320-1348 | accept if score > best; no margin, no held-out set, no repeats |
| V8 | autoresearch_v2.py:167-199, 234-551 | proposer sees `evaluate()` source; `--allow-code` lets it replace the judge |

## Cross-cuts

### (a) Wrong decision → irreversible effect
C8, C9, C11 (Neo4j delete, no archive); the importance→deletion chain (I4 → C5/C6 → C8); C10 orphan deletion; C12 Redis delete when no archive store; E9 MERGE; E11/E12 SAME_AS + closure (evidence erased); E16 supersession (no reason); E8/E17 overwrites; I2 dropped conflicting payload; E2+X1 empty extraction ACKed; V8 accepted code patches persist on disk.

### (b) LLM proposes and judges in one call
E2 (items + own confidence + own source label); R2 (label + confidence); SDK `reconcile_entities`; V1 (dataset + gold); V8 (proposer can rewrite judge). C3 and R18 are proposals with no judge at all.

### (c) Global constants that should be per-tenant or learned
`INTENT_WEIGHTS` (module constant, not env-configurable); intent keyword lists; seed map; decay weights and `s_base`/`s_boost`; vector threshold 0.5, MMR λ 0.7, neighbour boost 0.1, seed limit 10, RRF k=60; fuzzy 0.9, `same_as` 0.90 / `related_to` 0.75; `DOMAIN_ALIAS_DICT` (payments/devtools-specific); `CONFIDENCE_CEILINGS`; quote-match 0.6; degenerate std 0.02; `cold_min_importance` 5, `cold_min_access_count` 3, tier hours; centrality bands; `DEFAULT_IMPORTANCE` 5; feedback ±1; `reflection_threshold` 150; episode gap 30 min; node budget; LLM breaker 5/60.

### (d) Decisions taken but never recorded
Intent + seed strategy (response only, not persisted; fallback not flagged); HyDE text; RRF/MMR/PPR intermediates; access bumps unlinked to query; proactive reasons; E9 merge candidates; Tier 2b candidate list; E12 original justification; E3/E5/E6 dropped items; E2/E4 empty results; model + prompt provenance on DERIVED_FROM; entity confidence; persona history; supersession rationale; C3 model/prompt/fallback; C5, C7–C13 ids; I2 dedup hits; X1 breaker transitions.

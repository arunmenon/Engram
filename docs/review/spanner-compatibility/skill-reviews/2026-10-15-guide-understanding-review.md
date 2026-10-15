# Guide review: understanding and hidden assumptions

Completed the requested assumed-knowledge and terminology pass across all 27 HTML pages. Applied `explain-with-depth` for a junior engineer with basic HTTP/database knowledge and no Engram history. The aim is to explain why each component exists, what it receives, how it acts and what its outputs establish, without requiring this conversation or replacing technical substance with vague wording.

The pass includes the four interactive worker lessons, consolidation lesson, both tenant journey catalogs (49 candidates) and shared probes (18). Astra independently reviewed source explanations at low effort, identified the current User path and checked the revised guide. No empirical learner test or runtime verification is claimed.

## Important correction to the earlier review

The earlier claim that the current bound User writer loses quotes and links preferences to every session Event was incorrect. It followed the older generic writer without tracing runtime construction. Current `worker/__main__.py` requires UserExtractionStore when User extraction is enabled; `worker/extraction.py` selects that branch and bypasses legacy User output writing.

The current branch freezes an accepted owner/session input window, validates quote membership and persists quote-matching support. `domain/user_extraction.py` normalizes case/whitespace for textual matching and stores `evidence_quote` on DERIVED_FROM. It does not independently establish truth or resolve every attribution ambiguity. Core Entity REFERENCES associations still cover the collected input window. Pages 9, 15 and 24 now distinguish these behaviors; the preference animation points to E22 only. This supersedes the contradictory conclusion in the earlier version of this review, preserved in Git history.

## Page-by-page disposition

| Page | Hidden knowledge or connection addressed |
|---|---|
| 1 | States the reader baseline; introduces ledger, graph nodes/edges, worker loop, packs, LLM and embedding before the architecture boxes; keeps provider clients distinct from external services. |
| 2 | Explains node labels/properties and JSON; introduces group/cursor/pending/shard/binding/epoch before the tables; explains text tokens, approximate vector matching and database-enforced foreign keys versus Engram-managed associations. |
| 3 | Teaches interface versus adapter versus startup composition; defines transaction, snapshot, mutation and SDK pool before the call flow; explains why blocking SDK calls run in threads. |
| 4 | Separates authentication, authorization, acceptance and receipt; explains webhook source adaptation, request fingerprint and batch atomicity. |
| 5 | Explains consumer notification versus stored payload, ledger position, batch tie-breakers, session hashing, partitions and delivered cursor progress. |
| 6 | Defines polling, batch, ACK and PDLC before the worker examples; connects cursors to pending work; defines extraction profiles and fixes the pointer to the 15 examples on page 19. |
| 7 | Defines triggers, capabilities and versioned behavior IDs; explains lag without treating it as output proof. |
| 8 | Defines deterministic mapping, TestCase/TestRun and scoped identity; uses T17 for the separate test example so page 4's Billing event E17 does not change meaning. Moves repeated configuration matrix to optional reference detail. Repairs the initial accepted-input visual. |
| 9 | Teaches the actual bound User path: accepted-window trigger, saved extraction receipt, quote-matching evidence and retry reuse. Distinguishes the core Entity window associations and legacy branch. Keeps User transaction separate from provider call, core writes and ACK. |
| 10 | Defines annotation, metadata and embedding; explains fixed importance fallback, numeric vector versus searchable index and current missing-target dependency wait. Calls the changes record properties, not a newly created schema. |
| 11 | Defines Summary versus Episode membership snapshot; teaches the source-time gap rule, including the exact 30-minute boundary and late bridge example; explains overlapping historical snapshots and read truncation. |
| 12 | Defines extraction profile and proposal before use; explains content-hash identity and why validation, persistence and producer confirmation differ. Keeps forbidden operational claims explicit. |
| 13 | Connects the result lesson to planning, flush and ACK; explains database commit-size limits separately from model-call limits. |
| 14 | Defines ontology, pack, loader, bundle, dependency and capability before composition diagrams; explains pinned configuration and deployment boundaries. |
| 15 | Distinguishes attributed Belief, explicit Goal, User preference and Episode; replaces “evidence spine” with shared source Events; corrects current User quote support. |
| 16 | Defines subgraph, seeds and intent before the read flow; replaces unexplained fuse/hydrate labels with their operations; explains search channels, approximate similarity, provenance and truncation. |
| 17 | Defines artifact, traversal, lineage and GQL before comparison; translates weighted exploration and source/read rules; explains the development evaluation override's limits. |
| 18 | Defines dispatcher, credential grant, child runtime, owner/binding and epoch before the routing diagram; explains why fencing rejects stale generations and what scripted-provider isolation evidence does not establish. |
| 19 | Defines journey and development document abbreviations before the examples; retains explicit payload/reference preconditions and source index. |
| 20 | Reintroduces tenant/pack responsibilities for direct pilot entry; explains profile selection and separates candidate coverage from pass claims. |
| 21 | Defines test case/run, code revision and independent expectation; explains graph arrow direction, coverage versus test success and separate execution histories. |
| 22 | Defines attribution and scope with Alice/Bob/context examples; explains positive owner controls and immutable old Episode membership. |
| 23 | Introduces specification, requirement, HLD/LLD, ticket/PR/release/deployment vocabulary before development examples; distinguishes event-type coverage from relationship producers. |
| 24 | Defines trigger and applicability; labels teaching stages as explanatory, not runtime barriers; corrects actual User quote validation and separates domain/Memory reads without inventing a semantic relationship. |
| 25 | Defines exact seed, lexical discovery, paraphrase, query limits and truncation; replaces sibling-drift shorthand with the concrete unwanted behavior. |
| 26 | Defines probes, forbidden effects and controlled fault checks; all 18 probes now use story/question/meaning before optional technical contracts; explains why isolation exclusion needs a positive rightful-tenant read. |
| 27 | Defines fixture, runner and pinning; explains binding/generation and producer-to-user mapping; states the full-suite runnable-command gap up front. No artificial call-count or spend ceiling is introduced. |

Reference matrices remain available in expandable sections; worker-specific schema tables, mechanisms and material caveats stay in the main path. No new presentation framework, ontology or runtime behavior was introduced.

## Source-grounded understanding checks

1. **A write succeeded; why might no preference be ready?** Acceptance stores input. Extraction needs its trigger, User capability, valid provider result, source projection, stored User mutation and applicable read behavior. ACK or lag alone does not prove those outputs.
2. **E21 mentions Billing; E22 states a preference. Should the preference point to both?** In the current bound User path, only quote-matching E22 supports this preference. Core Entity associations can span the collected input window. Textual support is not independent truth verification.
3. **What happens if a worker crashes after graph writes but before ACK?** The pending delivery can survive and be redelivered; writes need retry-safe behavior. This does not establish unlimited automatic live retries.
4. **Why can an Event contain an embedding but be absent from Entity ANN search?** Stored numeric properties and index eligibility are different. The current ANN index admits eligible Entity rows, not every Event/domain artifact.
5. **Events occur at 09:00, 09:05, 09:40; a 09:20 Event arrives late. Why can a new Episode contain all four?** Current grouping splits gaps greater than 30 minutes. The late Event changes consecutive gaps from a separating 35 minutes to 5, 15 and 20 minutes. A later eligible consolidation may create a new membership snapshot while preserving earlier snapshots.
6. **A rerun passes; may retrieval erase the failed execution?** No. Each run retains its own identity, outcome and source Event. Coverage and successful execution are different claims.
7. **Does selecting PDLC start a new worker service or make every event call the model?** No. Shared workers must be deployed; selected supported rules/profiles and triggers decide applicable work. Deterministic test projection does not need a pack-extraction call.
8. **Can another developer run every candidate from page 27 now?** No. The guide distinguishes the reproduction requirements and existing first checkpoint runner from a complete fixed-fixture runnable suite.

These are desk-review checks. No real learner has yet demonstrated comprehension.

## Verification performed

- Rebuilt the existing guide: 27 pages, 25 A candidates, 24 B candidates and 18 probes. All 67 entries have story, question and meaning; exact contracts remain optional detail.
- Rebuild is idempotent. All inline JSON parses; IDs are unique and all 24 page-button targets resolve. Ruff passed for the modified guide builder.
- Chrome navigation checked every page: exactly one visible page, nonempty heading/content and no document-level horizontal overflow.
- Exercised all 16 interactive worker graph states, all eight two-tenant teaching states and all 67 catalog selections, checking explanations, visible graph content and selected-state controls.
- A rendered check exposed the initial graph-projection visual outside its interactive container. Moved it out of the schema diagram into the animation; all 16 states then passed. This was a real presentation defect, not an empty-graph result claimed as success.
- Checked every page at requested viewport width 390 (effective document width 354 in this browser); no document-level horizontal overflow. Wide graph/table references remain internally scrollable. Restored the normal viewport afterward.
- Visually inspected mobile introduction and the repaired accepted-input and User graph views. This is not comprehensive accessibility certification.

## Independent review

Astra's low-effort final pass found one remaining material mismatch: the User example's trigger label still said delivered-event threshold. Corrected it to the interval of accepted non-system Events for this owner/session, matching the mechanism. Astra reported no other material educational blockers in its bounded source review. It did not run browser/runtime tests or claim empirical learner validation.

## Execution boundary

Only guide content, its existing builder and this review record changed. The pilot remains paused; no Spanner operation, worker/API start or provider call occurred for this documentation pass. The separate retained-contract restart and derived-field policy questions remain under #63.

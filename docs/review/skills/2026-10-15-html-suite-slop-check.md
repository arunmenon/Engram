# HTML suite artifact-quality gate — 15 October 2026

**Verdict: REVISE.** Two material teaching defects remain. This is a review of the guide, not a product-readiness verdict or an AI-authorship assessment. No HTML or runtime fixes were applied.

## Scope and evidence

Reviewed repository revision `c2567b2`, with the guide last changed at `07dcbd7`. Audience: an engineer familiar with HTTP and database rows who is new to Engram. The guide must explain the actual architecture, how packs configure processing, and what the proposed pilot can establish without assuming implementation or execution success.

Inspected all 27 pages of `docs/guide/engram-architecture.html`, the pilot chapter template, the 49 journey and 18 shared-probe teaching entries in `pilot-journey-explanations.json`, builder and linked discovery contracts. Traced material worker, embedding, User evidence, Episode, projection and retrieval claims against current source. Runtime construction/callers were checked rather than treating unused helpers as the active path.

Browser checks in this audit: all 27 pages selected successfully, each with one visible page, a heading and no outer horizontal overflow at the current desktop viewport. Exercised all 16 interactive worker-demo stages on pages 8, 9, 10 and 12, and all eight tenant/stage combinations on page 24; their state controls updated and pilot captions/graph content were populated. Inspected the rendered consolidation lesson and reproduction handoff. No captured console errors were returned. These checks establish rendering/state behavior, not backend execution. Earlier unchanged-guide browser evidence for all 67 catalog selections and narrow layouts is recorded in `docs/review/spanner-compatibility/skill-reviews/2026-10-15-guide-understanding-review.md`; those exhaustive selector/mobile checks were not rerun in this audit.

## Required corrections

### F1 — Page 1 puts local embeddings outside Engram

- **Location:** `docs/guide/engram-architecture.html:11`, Application side → Provider clients.
- **Observation:** “call external embedding and LLM services when needed” presents both inference paths as remote services.
- **Grounding:** `src/context_graph/adapters/embedding/service.py:42–74` constructs a local `SentenceTransformer` and invokes `model.encode` through an executor. The actual API constructor at `api/app.py:68–79` and worker constructor at `worker/__main__.py:48–59` use this adapter. LLM provider calls are a separate path. Initial model acquisition/cache requirements should not be confused with remote embedding inference.
- **Consequence:** A newcomer learns the wrong deployment and data-processing boundary and may plan an unnecessary embedding service or assume text is sent to it.
- **Smallest correction:** Distinguish the locally running sentence-transformer adapter from external LLM provider calls on the overview. Keep the embedding definition; change its location/communication claim.
- **Meaningful recheck:** Compare the revised overview to both constructors and the adapter, render page 1, and answer explicitly where embedding inference and LLM inference run. This is a desk comprehension check, not a learner study.

### F2 — Page 11 omits consolidation’s mutation and retention work

- **Location:** Page 11, `#worker-deep-dive-consolidation`, especially the four-box flow and “How the graph changes.” Related overview wording appears on page 1 (“keeps the original event history”) and page 6 (“maintenance policies”).
- **Observation:** The deep dive explains eligible Summary/Episode creation and historical membership, but does not explain importance recomputation, forgetting or ledger lifecycle cleanup. Its flow says distinct Events remain in the ledger, without a retention qualification. The generic maintenance reference on page 6 does not teach these consequences.
- **Grounding:** `worker/consolidation.py:238–245` calls importance recomputation, forgetting and log cleanup after summarization; `:345–421` applies configured edge/event/orphan pruning and ledger trim/expiration. This is active Spanner behavior as well: `SpannerGraphStore` inherits `GraphOperations` (`adapters/spanner/graph.py:150`), whose `graph_ops.py:978–1007` deletes qualifying cold/archive Event nodes. `adapters/spanner/log.py:1027–1107` removes eligible events from the delivery window and expires stored documents, archiving first when an archive store is supplied. Effects depend on settings, ages, predicates and successful execution; this audit did not execute deletion.
- **Consequence:** Readers can conclude consolidation only adds memory and that source history remains available indefinitely. They cannot explain changes to importance, missing old evidence or the retention choices needed for a retained-data pilot. An unchanged Episode membership record does not ensure all its source documents remain retrievable.
- **Smallest correction:** Add a compact full-cycle map: eligible summaries/Episodes → importance update → conditional graph retention → ledger lifecycle cleanup. Explain what can change or expire, which settings govern it, and that membership preservation differs from source availability. Qualify the overview’s history statements. Add one small Event/Summary/Episode graph with named evidence/membership edges; page 11 currently supplies process boxes but not the graph explanation requested for every worker.
- **Meaningful recheck:** Trace each depicted step to the current cycle and adapters; verify the graph against `domain/episodes.py` and its read validation. Render the lesson and check that a reader can distinguish immutable membership, mutable derived fields and retention-governed source records. Do not claim a retention policy was executed merely because the diagram is corrected.

## Optional improvements

- **Page 6 repetition:** The opening worker explanation, “Distinguish the three pieces” and “Where these workers actually live” repeat the application-versus-Spanner boundary. Merge the repeated paragraphs while preserving the process-location diagram, delivery/ACK distinction and pack applicability table. The cost is repeated reading before reaching the pack-specific answer; length itself is not the defect. Recheck that a first-time reader still learns worker, group and adapter separately.
- **Page 27 handoff:** It honestly states that the full pilot suite is not executable yet. Improve the first-checkpoint handoff by directly linking its existing runner and failed-run/evidence record alongside prerequisites. The linked README is a useful index, but a direct checkpoint path would reduce searching. Keep the incomplete-suite warning; do not invent a runnable full-suite command or a successful pilot.

## Useful content to preserve

The guide distinguishes schema from records, shared workers from pack-specific applicability, acceptance from semantic output and ACK, and illustrative animations from observed runs. The pilot separates exact-ID lookup from discovery, explicit Memory actions from automatic inference, and source evidence from model usefulness. The 67 teaching entries use concrete stories/questions and preserve important differences such as skipped versus passed tests, interest versus skill and approval versus review. These mechanisms provide useful depth; they should not be removed merely to shorten the artifact.

The current bound User path retains validated quotes and quote-matching source membership. Its explanation is supported by `worker/extraction.py`, `domain/user_extraction.py` and the Spanner receipt application. The legacy generic writer is not grounds for calling that explanation false. Likewise, Entity-only ANN scope and the enrichment hint/default behavior are stated with appropriate bounds.

## Gate boundary and next action

Resolve F1 and F2, then recheck their source claims and rendered pages. Optional improvements do not block this verdict. This pass does not certify every link destination, accessibility behavior, browser/device combination, provider quality or pilot journey. No new Spanner run, model call, independent Astra review or pilot completion is claimed. The gate identifies concrete artifact defects; it does not estimate a percentage of “slop.”

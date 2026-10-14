# Independent #61 source and harness preflight

2026-10-14. Read-only review of issue #61, the one-line retrieval diff, the unit regression and the draft Spanner harness. **Runtime fix is appropriate; tighten the harness before cloud reset.** No additional runtime design or service is needed.

The change selects Event nodes by validated Atlas node type after pagination. It removes the legacy identifier-prefix assumption and preserves the existing access-write path and timing. The unit regression exercises UUID Events, repeated reads and a subsequent cursor page. Its explicit expected order now matches the existing neighbor scoring; that is a fixture correction rather than a weakened accounting assertion. Concurrent increment atomicity remains outside scope.

## Pre-cloud corrections

1. **AC03 can pass without reading an Event.** The one-node page only requires len(returned)==1. If ranking chooses an Entity/Episode/Summary, returned_events is empty and the count loop exercises no increment. Require exactly one returned Event on the tested page, or traverse real pages until an Event page is reached and assert that page's single increment and all other Events unchanged. Keep fixture ordering expectations explicit rather than silently accepting a different scenario.

2. **Empty session is not necessarily an empty subgraph.** `seed_nodes=[]` is falsey and does not disable seed channels. `RetrievalEngine._get_vector_seeds` searches Entities without a session predicate; global vector matches can seed referenced Events even for the empty session. Thus AC04's unconditional zero-node expectation is not implied by the endpoint contract. Use a deterministic true-empty result fixture/case, or explicitly establish that this fixture has no other-channel seeds. Preserve the narrow no-returned-Events/no-access-write assertion and do not imply general session/tenant isolation from this test. Do not expand #61 into a retrieval scoping redesign.

3. **The unchanged-table claim exceeds the snapshot.** `snapshot()` includes Events, GraphNodes, GraphEdges, deliveries and dead letters, but omits ConsumerGroups/Cursors and the physical embedding column. If retaining “everything else unchanged,” compare per-request fingerprints for every application table except GraphNodes, and verify unchanged physical node columns separately or narrow the claim to the inspected properties. The final one-second stability observation does not prove requests left those omitted fields untouched.

## Small supporting improvements

- Assert baseline access counts are zero if keeping the absolute counter initialized at zero; otherwise derive each expected increment from the saved before-state. Require monotonically updated request-bounded timestamps and save their before/after values, as the current record already enables.
- For unpaged AC01 reads, require meta.truncated=false and confirm returned Event node types/owner/session against accepted inputs. Dynamic returned-event membership is appropriate for deriving accounting deltas only after independently validating that response membership.
- Preserve request intent/status=None and any transport exception before a request can fail, as prior runners do. Reuse fresh HTTP connections if avoiding the previously observed keepalive failure is desired; do not add automatic mutation retries.
- Mark record state failed if final shutdown errors occur. Main already raises and prevents the next reset, but leaving a saved state='passed' with shutdown_errors is misleading.

The harness correctly stops and joins all five production workers before access comparisons, using the now-fixed production shutdown rather than an external lock workaround. Scripted extraction/summary outputs are labeled. The retained epoch37 dataset must be preserved through the existing exact owner/fingerprint verified-export reset protocol, with final data and post-process fingerprints retained. Core and Core+PDLC+Memory establish the selected access-accounting paths, not full producer reevaluation, concurrent ownership/tenant guarantees or pilot readiness. Final closure remains pending corrected harness and actual evidence.

## Corrected harness recheck

2026-10-14 — **Go for bounded cloud verification; no remaining preflight blocker found.** Rechecked the current runner. AC03 now follows bounded one-node cursor pages until an Event page is positively observed, auditing every intervening page's actual access effects. AC04 uses an exhausted cursor on the same query, so its empty-result oracle no longer assumes session-isolated seed selection. Per-request comparisons include all six other application-table fingerprints and physical GraphNodes columns excluding props, alongside exact property deltas. Zero baseline counts, untruncated full reads, returned Event provenance, transport-error journaling, fresh HTTP connections and failed shutdown state are present.

This clears execution under the existing verified epoch37 export/reset safeguards, not final acceptance. The production diff remains the one-line post-pagination Event-type selection. Keep the composed-read identity/type test and scripted-provider limits distinct from live evidence, and retain final state plus a post-process owner/fingerprint check.

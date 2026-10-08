# G07 Spec-axis bounded recheck

**Verdict: all four prior findings resolved; ready for cloud execution once the external PermissionDenied prerequisite is cleared.** Reviewed `c8eb4f5`, including fix `0efca34`, only for the four findings in `/tmp/engram-g07-spec-review.md` and regressions introduced by those fixes. No cloud calls or repository modifications; this is not cloud proof.

1. **Observation provenance fixed.** B/D fixtures now declare exact per-event observed identities. The harness uses `fixture_observations` at `scripts/engram_goal03_implementation_demo.py:752`; references do not acquire evidence merely by appearing as edge endpoints. Previously observed rollback targets use state assertions, unknown targets remain null-provenance placeholders, and late fill contributes the original deployment observation. The combined manifest audit found zero observation mismatches.

2. **Ownership registry fixed.** `cleanup_artifact_ids` at `scripts/engram_goal03_implementation_demo.py:156` collects independently authored primary, extra, assertion and edge-endpoint identities before writes. All combined-plan artifacts fall within that predeclared registry; the 17 previously omitted references are covered. Unknown runtime identities and ownership-fence failures still cause refusal.

3. **Timestamp ties fixed.** `assert_latest_source` at `scripts/engram_goal03_implementation_demo.py:169` admits only declared sources at the maximal timestamp. Older and unrelated sources still fail. Exact complete DERIVED_FROM equality remains enforced at line 879.

4. **B05 public Event read fixed.** `retrieve_ledger_only_event` at `scripts/engram_goal03_implementation_demo.py:176` uses the existing `/v1/query/subgraph` endpoint and verifies exact Event identity, type, time, source, session, agent, trace and committed position. Raw payload/payload_ref availability is explicitly recorded rather than falsely claimed; exact ledger content remains independently checked. The specification documents this existing public-response limitation without adding an API feature.

Validation: **57 passed** across `test_goal07_observation_manifest.py`, `test_goal07_harness_transport.py` and `test_g07_deployment_operations.py`. An independent combined-fixture audit additionally returned zero observation mismatches and zero unregistered plan artifacts. No introduced blocking finding identified in this bounded recheck.

Real HTTP/five-worker/Spanner acceptance and final delivery evidence remain unexecuted. The readiness verdict does not promote local tests to cloud acceptance or waive access, retention, source-freeze or final evidence requirements.

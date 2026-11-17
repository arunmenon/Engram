# Slice-1 payload-contract prototype review — 2026-10-07

**Verdict: acceptable as a bounded local prototype; no demonstrated blocking implementation defect in the reviewed contract/path-check code. Not full slice-1 exit or closure of #4, #36, #39, PE-01 or PE-08.**

Reviewed the new contract model, EventDef addition and projection-path validation, both PDLC YAML copies, the two requested test modules and contract fixtures against the published issue snapshot and Astra design report. Existing unfinished runtime changes outside this scope were not reviewed. Source inspection included the existing event resolver and producer shapes to understand compatibility. Only this report was written.

## Findings and smallest next steps

1. **P2, blocks exact-conformance/PE-08 completion, not prototype retention:** `tests/unit/test_pdlc_payload_contracts.py:69–76` checks trusted node identity sets, edge identity sets and target-state dictionaries, but not complete node/property/edge-property deltas, unexpected untrusted stubs, multiplicity, or retrieval answers. `tests/fixtures/pack_contracts/pdlc.json:19–25` exemplifies the limited oracle. A wrong title, incorrect edge evidence property, extra stub or duplicate edge can escape these assertions. Smallest fix: extend the same fixture format with expected complete planned nodes/stubs/properties and edge properties, and compare complete normalized plans; add explicit question/answer/evidence expectations as #39 proceeds. Call the current result catalog-wide contract/identity-plan coverage, not exact graph/evidence conformance. No backend execution is needed to improve the plan oracle.

2. **P2 coverage gap, before broader producer/subscriber compatibility claims:** `tests/unit/test_pdlc_payload_contracts.py:105–186` exercises GitHub producers only; `:189–217` uses a separate handwritten lab path rather than the catalog fixture runner. No external-owner contract regression or CRM fixture uses that runner. `src/context_graph/domain/ontology.py:1095–1098` correctly resolves the referenced event and reads its owner's contract by inspection, including qualified external references; this is not executed subscriber evidence. Smallest fix: add one subscriber fixture with a valid owner-declared path and an invalid undeclared path, run the two existing Jira webhook fixtures through contract validation, and reuse the catalog runner for lab/CRM when claiming #39 generality. No new framework is required. Existing Jira producer fields appear compatible by source inspection; no incompatibility was demonstrated.

## Verified strengths

The executed tests cover full model-dump round trip, schema-less EventDef compatibility, declaration depth/field limits, required/optional distinction, explicit nullable values, strict booleans/integers/strings, finite numbers, numeric bounds, enums, length bounds, forbidden extras and reserved source names. Validation returns no rewritten payload and does not mutate/default the caller's object. The private generated model's optional-field default is not exported as a payload change. Bounds here limit declared structure; they are not a global payload-byte, arbitrary-extra-field or evaluated-write budget.

Nested payload paths and paths inside function expressions are checked at registry load. Wildcard traversal requires a declared array and object traversal requires an object. Preserved unknown payload fields do not become permissible mapping inputs. Unsupported declaration keywords fail validation. Both PDLC YAML copies are byte-identical; version 1.8.0 matches the fixture. All 23 owned events have contracts and examples; tests distinguish 16 deterministic mappings, six missing mappings and the extraction-only case without presenting empty plans as executed extraction.

Fixture provenance is honest: normalized examples are explicitly synthetic; public REST records are put into explicitly reconstructed wrappers; captured deployment failure is asserted to emit no event. Positive deployment tests use handwritten examples, not the captured failure as success evidence.

## Scope gates remaining open

Path existence does **not** validate result types or cardinality. A declared list feeding a scalar property without key fan-out can still become `None`; this review does not mark that known #36/PE-01 problem fixed. Missing/null write behavior, mismatched expansion, write bounds, ordering and property authority remain outside this implementation. Lab's single-item bound proves a narrow nested-array path, not general fan-out correctness.

No ingress enforcement, activation/version rollout, worker completion/evidence, persisted graph/retrieval or Spanner acceptance was established. #4's broader all-route/CRM acceptance and #39's common runner/exact oracles remain open.

## Tests actually executed

`PYTHONPATH=src /private/tmp/engram-ontology-review-venv/bin/python -m pytest tests/unit/test_pack_payload_contracts.py tests/unit/test_pdlc_payload_contracts.py -q`

**93 passed in 0.78s.** No integration tests, service runners, credentials, downloads, cloud, Redis or Neo4j operations. The YAML mirror comparison also passed. These results describe the current working tree, including dependencies on unreviewed existing runtime changes, not a clean isolated commit.

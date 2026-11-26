# Slice 89: restore meaningful pack baseline tests

Issue: https://github.com/arunmenon/Engram/issues/89
Task branch: fix/89-pack-test-baseline
Integration target: integration/engram-ontology-v2
Base: ad71ea42c560685e89e295fcb8354a72f071b9dd

## Problem and scope

The packaged PDLC test still expected version 1.8.0 although the shipped pack is 2.1.0. A separate admission test asserted 23 event types even though the unchanged fixture catalogue and pack both contain 25. These produced 26 initial failures and prevented deeper checks from executing.

The version check also hid an outdated 17-node assertion; the shipped pack has 18 named domain types, including DesignApproval. This slice updates the pinned version and explicitly checks the intended node-name set, preserves dependency ordering, and replaces the admission count with agreement between declared events, unique fixture events and compiled policy entries. Per-event contract/admission assertions remain intact.

The authoring runbook now distinguishes the two intentional CRM 1.0.0 variants: the worked fixture has no payload contracts, the workbench catalogue variant adds contracts and explicit processed handling. Evidence must identify purpose/path, selected packs and existing composed-content digest. No pack version or payload was changed.

## Codex verification

All commands below ran locally in the isolated task worktree with PYTHONPATH=src and the existing project virtualenv. Imports were verified to resolve to that worktree, not the dirty integration checkout.

- Before: pytest tests/unit/test_ontology_packs.py tests/unit/test_pack_admission.py -q --tb=short : 26 failed, 38 passed. Exact failure IDs are retained in local implementation evidence.
- Final changed-file selection: the same selection : 65 passed. The catalogue guard also checks compiled events against declared events.
- Final affected regression selection: test_ontology_packs.py, test_pack_admission.py, test_ontology_registry.py, test_pack_composition.py, test_pack_versioning.py, test_pack_payload_contracts.py and test_pack_common_layer.py : 216 passed. These selections overlap; do not add them as a unique total.
- Ruff check and format check on the two changed test files pass; git diff --check passes.
- CRM memory end-to-end control: pytest tests/unit/test_pack_toy_end_to_end.py -k memory -q --tb=short: 1 passed, 2 deselected, with two FastAPI deprecation warnings. The two external-backend parametrizations were not run.

Only tests and documentation changed. No runtime source, pack, payload fixture, evaluation expected answers or dependency changed. No product-provider or cloud operation was performed; the two Fable review calls are separately recorded. The original dirty integration worktree remains untouched. This slice does not fix replay completion, classification, runtime handoff, vectors or UI behavior.

## Independent reviews

User requested two feedback rounds: Codex implementation/checks → Fable round1 → Codex disposition/correction → Fable round2. Round 1 is complete with no material findings; its minor documentation corrections are applied. Round 2 is complete and accepted within the stated local scope. No product issue closure, merge or deployment is claimed.

## First review and reconciliation

[Fable round 1](slice89-fable-round1.md) independently reran the changed tests (65 passed), affected regression selection (216 passed), CRM memory control (1 passed, 2 deselected), Ruff and diff checks. It inspected shipped definitions, fixture/compiled catalogue agreement and both CRM variants. No material finding. Codex applied its three minor documentation corrections and retained the check results. Baseline failures below are reported from Codex's run; Fable did not rerun the original failing base.

The seven-file regression command was:

```sh
PYTHONPATH=src python -m pytest tests/unit/test_ontology_packs.py tests/unit/test_pack_admission.py tests/unit/test_ontology_registry.py tests/unit/test_pack_composition.py tests/unit/test_pack_versioning.py tests/unit/test_pack_payload_contracts.py tests/unit/test_pack_common_layer.py -q --tb=short
```

Commands used the existing project virtualenv with Python 3.14; this is local verification, not the Python 3.12 GitHub CI job or real-backend evidence. The runtime import path was checked against this task worktree.

Baseline failing case IDs (26 total; full assertion traces retained locally):

```text
tests/unit/test_ontology_packs.py::TestPdlcPack::test_loads_with_its_requirements
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.created]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.updated]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.merged]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.abandoned]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.reviewed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.change.committed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.release.published]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.testcaserun.finished]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.testcaserun.skipped]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.service.deployed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.service.rolledback]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.service.upgraded]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.incident.detected]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.incident.resolved]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.incident.reported]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.ticket.created]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.ticket.updated]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.ticket.closed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.request.created]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.spec.approved]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.requirement.changed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.design.section_changed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.decision.recorded]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.spec.changed]
tests/unit/test_pack_admission.py::test_whole_pdlc_catalog_distinguishes_mapping_from_contract[pdlc.design.approval_recorded]
```

## Final acceptance checkpoint

[Fable round 2](slice89-fable-round2.md) accepts the slice with no material findings or new minor requests. It independently reran 65 changed-file tests, the 216-test affected selection, the CRM memory control (1 passed, 2 external cases deselected), Ruff and whitespace checks. Both requested feedback rounds are complete.

The accepted code/runbook candidate is `1026719bd0908d227936c068c427c9c5fc8d084a`. Only reviewer reports and this status record were appended afterward. The three reviewed file hashes remain unchanged. This evidence supports the bounded test/documentation slice; it does not attest live backend behavior, Python 3.12 CI, a deployed fix or approval to merge. Issue 89 remains open until the agreed merge/closure process.

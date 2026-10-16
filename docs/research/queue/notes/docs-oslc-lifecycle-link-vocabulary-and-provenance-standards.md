---
schema_version: 1
artifact_id: N-SURVEY-20260928-19
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: []
supersedes: null
idempotency_key: note:survey:docs:docs.oasis-open-projects.org/oslc-op
claim_cluster: docs:oslc-rm-cm-qm+openlineage+slsa+in-toto
found_via: survey
source_url: https://docs.oasis-open-projects.org/oslc-op/core/v3.0/oslc-core.html
strength: standard (ratified specs, no effectiveness evidence)
pillar_primary: R10
pillar_secondary: ["R7", "R1"]
memory_stage: linking
priority: 3
tags: {"mechanism": ["linked-data integration without copying", "resource shapes", "trace-link vocabulary", "version negotiation", "typed predicates bound to digests", "run/job/dataset facets"], "workload": ["requirements, change and quality management tools", "build provenance"], "lifecycle_stage": ["linking", "ingestion"], "cross_cutting": ["federation contract", "interchange"]}
evidence: {"directness": "high for vocabulary, none for effect", "control": "none", "independence": "high: OASIS, OpenSSF, LF AI and Data standards bodies, multi-vendor", "reproducibility": "high: public specs, stable namespaces", "applicability": "high: OSLC RM/CM/QM already name most PDLC trace links; in-toto and OpenLineage give a digest-bound, extensible event shape for 'this PR at this digest was verified by this run'"}
beliefs_affected: {"supports": [], "contradicts": [], "would_create": ["Our PDLC trace-link names should map onto OSLC RM/CM/QM properties rather than be invented, so that export to lifecycle tools is lossless"]}
answers_watch_request: null
---

# OSLC RM, CM and QM link vocabulary, and the provenance standards (OpenLineage, SLSA v1, in-toto v1) as templates for PDLC trace links

- **URL:** OSLC Core 3.0 https://docs.oasis-open-projects.org/oslc-op/core/v3.0/oslc-core.html. RM 2.1 https://docs.oasis-open-projects.org/oslc-op/rm/v2.1/requirements-management-vocab.html. CM 3.0 https://docs.oasis-open-projects.org/oslc-op/cm/v3.0/errata01/os/change-mgt-vocab.html. QM 2.1 https://docs.oasis-open-projects.org/oslc-op/qm/v2.1/os/quality-management-vocab.html. OpenLineage https://openlineage.io/docs/spec/object-model. SLSA https://slsa.dev/spec/v1.0/provenance. in-toto https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
- **Type:** standards
- **Author / org:** OASIS OSLC Open Project; LF AI and Data (OpenLineage); OpenSSF (SLSA, in-toto)
- **Date:** OSLC Core 3.0 OASIS Standard 2021-08-26; RM 2.1 2021-06-21; CM 3.0 Errata 01 2023-07-06; QM 2.1 2022-01-19; SLSA provenance v1.0; in-toto Statement v1
- **Retrieved:** 2026-09-28 (summarising fetch; property names as returned)
- **Relevance to a memory stack:** high. Most of our proposed PDLC edges already have standard names, and the provenance standards solve "a claim about an artifact is bound to its exact bytes".

## TL;DR
- **OSLC integrates tools by linking, not copying.** Each tool keeps its resources at their own URIs. Other tools link to them and show them through Resource Preview and Delegated Dialogs. Resource Shapes declare the expected properties. Versions are negotiated with the `OSLC-Core-Version` header, and versioned resources use Configuration Management 1.0 and Tracked Resource Set 3.0.
- **Standard trace links already exist.**
  - RM: `implementedBy`, `validatedBy`, `satisfiedBy`/`satisfies`, `elaboratedBy`/`elaborates`, `specifiedBy`/`specifies`, `decomposedBy`/`decomposes`, `constrainedBy`/`constrains`, `affectedBy`, `trackedBy`.
  - CM: `implementsRequirement`, `affectsRequirement`, `tracksRequirement`, `tracksChangeSet`, `testedByTestCase`, `affectedByDefect`, `blocksTestExecutionRecord`.
  - QM: `validatesRequirement`, `testsChangeRequest`, `blockedByChangeRequest`, `reportsOnTestCase`, `producedByTestExecutionRecord`.
- **Nothing in OSLC for design decisions or pull requests as such.** `tracksChangeSet` to `oslc_config:ChangeSet` is the nearest hook for a PR. There is no Decision class.
- **in-toto Statement v1**: `subject` is a list of resource descriptors, each with a required digest. `predicateType` is a type URI. "subject artifacts are matched purely by digest, regardless of content type". New predicate types extend the model without changing the envelope.
- **OpenLineage**: Run ("An instance of a Job that represents one of its occurrences in time"), Job, Dataset. Events are START, RUNNING, COMPLETE, ABORT, FAIL and OTHER. Facets on each extend it, and custom facets carry `_producer` and `_schemaURL`, so a version travels with each facet.
- **SLSA provenance v1**: `buildDefinition` holds `buildType`, `externalParameters` and `resolvedDependencies`; `runDetails` holds `builder.id` and metadata. Minor versions keep the predicateType and stay backward compatible.
- **ReqIF** (OMG; search snippets only): SpecObjects and SpecRelations with user-defined SpecTypes. Exchange is by file, so data is copied.

## Numbers
| metric | value | baseline | setup | caveat |
|---|---|---|---|---|
| effectiveness | not applicable | | | standards; no measurement of trace quality |

## Mechanism details you could implement
Proposed mapping of our PDLC sketch edges (pdlc-memory-layer section 3) onto standard names (inference):

| Our edge | Standard property | Gap |
|---|---|---|
| `IMPLEMENTS` Ticket to Requirement | `oslc_cm:implementsRequirement` (inverse `oslc_rm:implementedBy`) | none |
| `IMPLEMENTS` PR to Requirement | `oslc_cm:tracksChangeSet` plus implementsRequirement on the ticket | PR is not a first-class OSLC type |
| `VERIFIES` Test to Requirement | `oslc_qm:validatesRequirement` (inverse `oslc_rm:validatedBy`) | none |
| `VERIFIES` Test to PR | `oslc_qm:testsChangeRequest` | only through the change request |
| `REFINES` Design to Requirement | `oslc_rm:elaborates` / `specifies` | no DesignElement class |
| `SATISFIES` | `oslc_rm:satisfies` | none |
| `CONSTRAINS` | `oslc_rm:constrains` | none |
| `BLOCKS` Ticket to Ticket | none in CM (`blocksTestExecutionRecord` is test-specific) | custom |
| `DECIDED_IN`, `SUPERSEDES` (Decision) | none | custom; PROV `wasDerivedFrom` / `wasInvalidatedBy` are closest |
| `ANCHORED_TO` (hash plus path) | in-toto `subject.digest` | adopt the digest-bound subject shape |

- Store each trace link as a small typed attestation: subject (the artifacts with digests), predicateType (for example `engram/trace/implements/v1`), and predicate (confidence, decided_by, evidence spans). The link then stays checkable when the code changes.
- OpenLineage's facet-with-`_schemaURL` rule is a cheap way to version ontology extensions per property group without a global schema bump.

## Limitations, caveats, counter-evidence
- These are standards, not evidence. OSLC adoption beyond IBM ELM, Siemens Polarion and PTC is not measured here.
- OSLC assumes RDF and linked-data servers. Neither Jira nor GitHub exposes OSLC natively (inference, not checked this run).

## Takeaways for tuning a memory stack
- Name PDLC link types after OSLC where one exists. Invent only Decision, PR, BLOCKS and SUPERSEDES.
- Bind every trace-link claim to artifact digests in the in-toto shape. This answers the EA-Graph "unprovable when the hash changes" rule with a standard form.

## Open questions
- Is there an OSLC or SPDX profile for pull requests or architecture decisions? Not found this run.

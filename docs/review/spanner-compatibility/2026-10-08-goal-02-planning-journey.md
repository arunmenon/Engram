# G02 — Versioned planning journey on real Spanner

Status: IN PROGRESS. User explicitly authorized G02 on 2026-10-08. G01 complete; G03 and later goals remain unstarted. The old broad control goal remains paused. Follow goal-verification-standard.md; this file tracks only G02.

## Outcome and existing gap

Demonstrate PRD → Requirements ← HLD ← LLD, approval bound to an exact design revision, and revision history through Engram's ordinary authenticated events API, actual worker loops and artifact retrieval on reserved real Spanner. Native document-service adapters are absent: the producer supplies explicit normalized event payloads through the supported generic events API. Source fixtures are attributed documents or explicitly synthetic password-reset examples; do not call them captured webhooks.

Current PDLC 1.8 declares requirement.changed and design.section_changed but has no deterministic projection rules for either. DesignElement identity is doc_id+section_path, so a revision overwrites the same identity. REFINES does not allow DesignElement targets. Spec only has approved-event projection. These are inspected code gaps, not inferred cloud results.

## Smallest proposed pack change (review before runtime acceptance)

Use existing interpreter, common event envelope, keyed endpoint placeholders, source authority and shared storage. No new service, projection engine or direct artifact insertion.

PDLC 2.0 is a breaking pack revision: DesignElement identity becomes doc_id+section_path+version, Requirement identity becomes spec_id+spec_version+local_id. Old records require separate migration/replay work; this goal activates only a known empty disposable database and does not claim upgrades proved. Spec is already keyed by doc_id+version.

Add deterministic spec.changed, requirement.changed and design.section_changed rules. Requirement explicitly REFINES its Spec revision. Design explicitly REFINES named Requirement or DesignElement revisions. Version 2 SUPERSEDES explicitly named version 1; both revisions remain. Extend REFINES endpoints for DesignElement targets. Add DesignApproval keyed by approval_id, with reviewer/approved verdict/time and exact DesignElement target via APPROVES. Design approval is an artifact, not a mutable blanket flag. Only approved is admitted by this approval event; changes_requested is rejected, not recorded as approval. Approval is a separate record; DesignElement lifecycle status is not automatically promoted by this slice. Version 2 receives no implicit approval. APPROVES and SUPERSEDES have explicit trace/status weights; PL11 uses status intent to include superseded history and trace for current content. Approval asserts a revision key, not an immutable content hash or independently verified reviewer identity. A producer reusing an event ID with changed content conflicts through existing admission; identity immutability beyond that is not implied.

References name explicit revision keys. Existing keyed endpoints create placeholders with identity/default lifecycle and no content-event provenance. A placeholder is not a complete design or inferred approval. When its actual event arrives, it fills the same keyed node and adds provenance. Test this visible intermediate state; do not silently count it as fully processed content. References omitted mean no invented domain relationship.

Existing pack LLM extraction is retained. Any triggered inference must use the actual configured provider; generated proposals are separate from declared links and cannot substitute for required deterministic outputs. No mocks or disabling required workers to obtain green results. Credential/provider failures block the affected acceptance.

## Predeclared scenarios

| ID | Action | Required result / forbidden effects |
|---|---|---|
| PL01 | Submit password-reset PRD v1 as spec.changed | One draft Spec with exact title/scope/source, Event and DERIVED_FROM; retrieved through API |
| PL02 | Submit expiry and single-use requirements naming PRD v1 | Two distinct Requirements and confirmed REFINES to exact Spec revision; no invented design |
| PL03 | Submit HLD section v1 naming both requirements | Versioned DesignElement kind hld and exact REFINES links/evidence |
| PL04 | Submit LLD section v1 explicitly refining HLD v1 and expiry requirement | Exact LLD→HLD and LLD→Requirement links; connected retrieval includes expected chain |
| PL05 | Record approval of HLD v1 | Exact DesignApproval→HLD v1 APPROVES edge and evidence; no approval of LLD |
| PL06 | Submit HLD v2 explicitly superseding v1 | Both revisions, SUPERSEDES edge; v1 approval remains attached only to v1; no implicit v2 approval |
| PL07 | Retry identical event, then same ID with altered contents | Stable duplicate response/no persistent effects; changed-content conflict/no writes |
| PL08 | Submit missing required version and invalid design kind | 422 and no ledger/graph effects |
| PL09 | Submit LLD pointing to not-yet-received HLD, then receive that HLD | Explicit identity-only placeholder before arrival, same identity filled afterward, evidence added and link retained; no manual repair |
| PL10 | Submit unrelated feature with its own PRD/requirement/design | Query expiry journey never includes unrelated feature; identical local requirement IDs scoped by Spec revision |
| PL11 | Retrieve from requirement, HLD v1, HLD v2 and LLD | Exact declared paths, source evidence, approval/version differences; report explicit-ID query separately from text discovery |
| PL12 | Run text-only expiry query | Intended expiry Requirement discovered without supplied node IDs, correct connected evidence; ambiguity/incompleteness reported honestly |

All acceptance uses actual HTTP API → Spanner ledger → five running ordinary workers → graph → actual retrieval API. Direct SQL is observation/owned cleanup only. No manual repair accepted. Every accepted record must preserve tenant/database/bundle/source authority. Await worker completion and fail on pending/dead-letter/errors. Additional inferred artifacts are recorded, not promoted to declared mappings.

## Verification, safety and end boundary

Before each local/cloud run register exact source hashes, request fixtures, expected nodes/relationships and cleanup ownership. Target only projects/portiq-mvp/instances/engram-experiment/databases/engram-compat-target, never source DB engram. Pin known predecessor owner, activate with existing fenced empty-target helper. Retain failures and reruns. Credentials stay outside repository.

Publish per-scenario actual event IDs, API outcomes, worker results, stored graph/evidence and returned API results in 2026-10-08-goal-02-verification.md. Independent review must cover pack semantics and final evidence. Reconcile #34/#39/#40/#41 and relevant projection/admission sub-issues without broad premature closure. Assess new defects/bucket needs. Provide recorded stakeholder demo and repeat command. G03 requires explicit user approval.

## Discovered retrieval defect and bounded scope adjustment

Full cloud all-01 passed all17 source requests but failed the final HLD-v1 connected retrieval oracle: an observed LLD→Requirement REFINES was omitted although both endpoints were selected. Local red triangle repro confirmed shared engine drift filtering, not a Spanner service defect. #46 under #34 owns the fix: defer drift-blocked observed edges, attach only when both endpoints were otherwise selected after the BFS level; no additional nodes, scores, frontier expansion or backend reads. Existing rejected-edge filtering and admission remain. 168 local checks, lint, type check and scoped review passed before cloud rerun. This necessary generic retrieval fix is the explicit exception to the initial pack-only implementation expectation; it does not authorize a broader engine rewrite. Runner now persists retrieval responses before assertions.

## Reviewed oracle correction after all-02

The expiry-seeded final trace originally required the separate single-use Requirement. That conflicts with the existing sibling-drift suppression policy: sharing a Spec or HLD is not sufficient to expand an expiry answer into sibling requirements. Astra confirmed the oracle error against the saved failed response. The corrected query still requires expiry, its Spec and current HLD; exact graph assertions and HLD-seeded queries still require both requirements and all declared links. Preserve all-02 as failed; rerun the whole journey. This correction does not weaken the HLD/LLD chain or evidence assertions.

# Approved Astra review request: pilot composition assessment

Status: completed by `astra_pilot_composition_assessment`, model `gpt-6-astra`,
reasoning effort **medium**, following stakeholder approval. [Full report](2026-10-08-astra-pilot-composition-assessment.md)
is preserved and findings incorporated into the discovery brief. Review was code
inspection only; no implementation or new runtime/cloud acceptance is claimed.
Requested source baseline: `51a680a`; reviewer must record the actual full commit.

## Task

Ground Engram's pack-composition assessment in current code. Review
[the discovery brief](2026-10-08-controlled-pilot-discovery-brief.md) against current
source. Explain actual processing, identify assumptions and recommend concrete
additions to the assessment plan. Work read-only: no implementation, repository
edits, cloud tests, credential access, retained-data changes or migration analysis.
Return the report outside the repository for incorporation by the coordinating agent.

## Configurations

Core alone as control; core+user; core+user+memory; core+PDLC; core+PDLC+memory.
Schema loading alone is not proof a combination works.

## Review dimensions

1. Pack dependencies, types, rules and capabilities: resolution, conflicts and process-global assumptions.
2. Actual processing inventory: graph projection, session knowledge extraction, enrichment, consolidation, pack extraction and any additional active loops. Explain inputs, writes and specialized versus pack-declared behavior.
3. Worker and sub-operation applicability: what runs per configuration; disabled-pack outputs; accidental disabling of mandatory core processing.
4. Concrete user preference/correction and PDLC ticket/PR examples using actual supported contracts and declared identities. Show memory-added effects or explicitly unsupported/unverified behavior.
5. Worker handoffs: ordering, retries, shared identities, provenance, duplicate/conflicting writes when domain and memory behavior consume the same event.
6. Both event-memory and artifact retrieval: intents, discovery, vectors, hydration, traversal, ranking, evidence and fallback; hidden optional-pack assumptions.
7. Tenant database and pack-context propagation through APIs, workers, registries, caches and reads. Distinguish storage separation from shared-runtime isolation.
8. Assessment quality: bounded probes, expected outcomes and failure cases; pilot blockers versus deferrable improvements.

## Required output

- Configuration-by-worker table: inputs, enabled behavior, outputs, dependencies and retrieval support.
- Two small graph/flow diagrams grounded in actual declarations.
- Prioritized findings with file/line evidence, impact and smallest correction or verification probe.
- Specific additions/corrections to the assessment brief.

Label conclusions **code-established**, **execution evidence available** (only
inspected evidence), or **unverified**. Avoid general architecture advice without
a concrete code path. No subordinate reviews or broad test runs are requested.
G1–G6 evidence is bounded core+PDLC, not composition/public-tenant sign-off.

## Integration of the result

Preserve the review report with source references, then reconcile its findings
into the assessment brief as supported/unsupported/unverified configuration
behavior, explicit probes and bounded dependencies. Record dispositions without
silently authorizing implementation or changing G07 scope. Existing ownership:
#34/#35/#42/#43/#39/#40/#41. No issue changes are part of the reviewer assignment.

G07 is selected first. Assessment and pilot execution remain later checkpoint
choices. G05/G06 data remains protected. The retired broad goal stays paused.

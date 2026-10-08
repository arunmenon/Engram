# G04 — Astra design and implementation/harness review

Reviewer: gpt-6-astra, medium effort, read-only. Scope: G04 design, PDLC declarations, shared G03/G04 harness, exact fixtures and local regressions. No cloud calls performed by reviewer.

## Design findings and disposition

- Deployment identity lacked repo/service: corrected all Deployment keys to repo+service+environment+artifact_id+started_at, PDLC3.0, with deliberately equal-timestamp collisions across repos/services. No historical migration.
- Retrieval oracles needed seed-specific sets: frozen separately; one attempt does not imply sibling expansion, Component catalog identities can explicitly be shared.
- API provenance is newest event only, while storage retains all: asserted separately; reference placeholders have no event provenance before arrival.
- Outcome authority is event type; extra payload fields are preserved, not asserted rejected. Incidents remain outside G04, including their older environment/artifact latest lookup.

## Initial harness changes requested

Exact edge equality and per-edge section/environment values; exact latest API provenance and stored source sets; rejected-candidate absence via HTTP; full SELECT* fingerprints across seven tables rather than partial snapshots; source contents archived before execution; local execution of all four retrieval oracles. All corrected. Fixture payload aliasing found in local testing was fixed with deepcopy; failed local logs retained. No cloud failures were hidden or expectations weakened.

## Final recheck

Astra: “Approved for the bounded G04 cloud run. No remaining concrete pre-cloud blockers found.”

Recheck confirmed exact topology/property assertions, latest API and complete stored provenance checks, placeholder/negative retrieval checks, full-table no-write fingerprints, frozen source archive, and local execution of all four RD12 oracles. G03 retains its default fixture path; strengthened assertions are G04-gated. Approval covers implementation/harness readiness, not end-to-end acceptance or stakeholder delivery.

## Review request

Review G04 design and final changes against current pack, artifact traversal and shared harness. Prioritize scoped identity, explicit release/change links, failed outcome preservation, exact seed-specific traversal, no-write rejection/retry evidence, source provenance, placeholder behavior and owned cleanup. Work read-only; no cloud calls, migration, G01–G03 reruns or G05. Return concrete blockers and smallest corrections, then review their disposition. Model: Astra, medium.

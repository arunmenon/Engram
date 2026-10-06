# Research pack, 2026-10

## Walkthrough

- **[walkthrough.md](walkthrough.md) — shareable engineering walkthrough of ontology packs, the PDLC ontology, ingestion and retrieval after the refactor, and the Spanner backend: https://claude.ai/artifact/2xnRzwTAnwV1D21hyBLW7g**

## Ontology

- **[ontology/pdlc-ontology-v1-summary.md](ontology/pdlc-ontology-v1-summary.md) — start here: one-page sign-off for PDLC ontology v1.0, ADR-0018, connectors and the Spanner approach.**
- [ontology/connector-design.md](ontology/connector-design.md) — how tools feed Engram through the existing ingest API.

- [ontology/pdlc-ontology-and-ontology-packs.md](ontology/pdlc-ontology-and-ontology-packs.md) — current ontology and where it is hardcoded; research on PDLC ontologies (OSLC, CDEvents, Backstage, Essence, Palantir, PROV-O); proposed PDLC MVP (16 node types, 18 edges); ontology packs as the way to import any domain ontology; impact per layer; plan.
- [ontology/pdlc.pack.yaml](ontology/pdlc.pack.yaml) — draft PDLC pack in the proposed format, internally consistent (no dangling endpoints, every rule on a declared event).
- [ontology/competency-check.md](ontology/competency-check.md) and [ontology/competency-questions.yaml](ontology/competency-questions.yaml) — 30 PDLC questions checked against the pack; produced v0.3 (four new links, five fields) and the finding that 8 of 30 questions are not graph walks.
- [ontology/mapping-step2.md](ontology/mapping-step2.md) — OpenDAL, Kafka and GitLab samples mapped onto the pack; produced v0.4 (Component, Release, AMENDS, git-only rule).
- **[../../adr/0019-pluggable-storage-backends.md](../../adr/0019-pluggable-storage-backends.md) — draft ADR: ingestion and retrieval decoupled from Redis, Neo4j and Spanner (five storage ports, registry, conformance suites, in-memory reference backend; revised after one review pass).**
- **[ontology/spanner-design-brief.md](ontology/spanner-design-brief.md) — consolidated design brief for Engram on Spanner (ledger and graph), reviewed once; supersedes the two documents below for decisions.**
- [ontology/spanner-everywhere.md](ontology/spanner-everywhere.md) — Spanner replacing Redis as well as Neo4j: what changes, cost, options; recommends staged (graph first, ledger second) if GCP is the target.
- [ontology/spanner-graph-gap-analysis.md](ontology/spanner-graph-gap-analysis.md) — Neo4j to Spanner Graph gap analysis; spike, no code.
- [../../adr/0018-ontology-packs.md](../../adr/0018-ontology-packs.md) — draft ADR (Proposed).

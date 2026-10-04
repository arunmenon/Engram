# Research pack, 2026-10

## Ontology

- [ontology/pdlc-ontology-and-ontology-packs.md](ontology/pdlc-ontology-and-ontology-packs.md) — current ontology and where it is hardcoded; research on PDLC ontologies (OSLC, CDEvents, Backstage, Essence, Palantir, PROV-O); proposed PDLC MVP (16 node types, 18 edges); ontology packs as the way to import any domain ontology; impact per layer; plan.
- [ontology/pdlc.pack.yaml](ontology/pdlc.pack.yaml) — draft PDLC pack in the proposed format, internally consistent (no dangling endpoints, every rule on a declared event).
- [ontology/competency-check.md](ontology/competency-check.md) and [ontology/competency-questions.yaml](ontology/competency-questions.yaml) — 30 PDLC questions checked against the pack; produced v0.3 (four new links, five fields) and the finding that 8 of 30 questions are not graph walks.
- [ontology/mapping-step2.md](ontology/mapping-step2.md) — OpenDAL, Kafka and GitLab samples mapped onto the pack; produced v0.4 (Component, Release, AMENDS, git-only rule).
- [ontology/spanner-graph-gap-analysis.md](ontology/spanner-graph-gap-analysis.md) — Neo4j to Spanner Graph gap analysis; spike, no code.
- [../../adr/0018-ontology-packs.md](../../adr/0018-ontology-packs.md) — draft ADR (Proposed).

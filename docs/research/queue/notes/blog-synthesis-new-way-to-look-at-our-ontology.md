---
schema_version: 1
artifact_id: N-SURVEY-20260928-26
artifact_type: note
producer: triage
run_id: survey-20260928T144404Z-faac
created_at: 2026-09-28T14:56:44Z
input_refs: [{artifact_id: N-SURVEY-20260928-17, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-18, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-19, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-20, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-21, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-22, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-23, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-24, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-25, file_id: PENDING, sha256: PENDING}, {artifact_id: N-20260928-07, file_id: PENDING, sha256: PENDING}, {artifact_id: N-SURVEY-20260928-14, file_id: PENDING, sha256: PENDING}]
supersedes: null
idempotency_key: note:survey:synthesis:ontology-as-federation-layer-20260928
claim_cluster: synthesis:ontology-as-federation-layer
found_via: survey
source_url: n/a (synthesis of the notes in input_refs, plus https://foundationcapital.com/ideas/context-graphs-ais-trillion-dollar-opportunity, https://foundationcapital.com/ideas/context-graphs-one-month-in, https://github.com/open-semantic-interchange/OSI)
strength: synthesis (vendor docs and standards for design; papers for the model decisions)
pillar_primary: R10
pillar_secondary: ["R9"]
memory_stage: ingestion
priority: 3
tags: {"mechanism": ["semantic and kinetic halves", "bindings", "interfaces", "action types with preconditions", "ontology versioning", "decision traces"], "workload": ["PDLC memory", "federation gateway"], "lifecycle_stage": ["ingestion", "linking", "gated action"], "cross_cutting": ["federation contract", "G2", "G4", "G7", "G13"]}
evidence: {"directness": "medium", "control": "low for the ontology claims (no source measures an ontology's effect on agents); medium-high for the model decisions (entity matching, pre-action checks)", "independence": "mixed: vendor docs (Palantir, Microsoft, Zep, Cognee, OpenBKN), standards bodies (OASIS, OpenSSF, LF), academic papers", "reproducibility": "mixed", "applicability": "high: every finding is mapped onto ADR-0011 and the gateway components"}
beliefs_affected: {"supports": ["B25"], "contradicts": [], "would_create": ["The ontology is the gateway's contract (types, bindings, actions, versions), not a tag set applied at serve time", "Leading ontology products copy and index source data by default; federation without copying is an OSLC-style linked-data property, not a Palantir property"]}
answers_watch_request: null
---

# A new way to look at our ontology

Today our ontology describes what happened (events, the things they touched, and how they connect). The new way, which Palantir built and Microsoft and others now copy, treats the ontology as the contract every connected system signs. It says what kinds of things exist across all our tools, how each tool's records map onto those kinds, who may see them, and, the part we lack entirely, which actions an agent may take on them and what must be true first. We should adopt the contract and the actions. We should not adopt the hand-built, copy-everything way Palantir runs it. The evidence that an ontology makes agents better is thin everywhere: vendors describe, nobody measures. The evidence that small, cheap models can do the ontology's routine decisions (spotting the same item in two tools, checking an action before it runs) is better than we expected.

## For example

A payments team keeps requirements in Confluence, tickets in Jira, code in GitHub and test results in CI. An agent opens a pull request for ticket PAY-1423 and is about to merge it.

Today, the memory can say what the agent did and what it looked at. It cannot say that PAY-1423 implements requirement R-88, that R-88 is verified by a test that has been failing since Tuesday, or that the design decision R-88 depends on was superseded last week. It cannot stop the merge either.

With the ontology as a contract:
1. Jira issues, GitHub issues and Linear tickets all map onto one shared kind, "work item".
2. The link from PAY-1423 to R-88 is stored with a confidence and the exact version of both.
3. "Merge pull request" is a declared action, and its precondition says "no linked requirement has a failing verifying test".
4. The agent asks before it merges. It gets back "blocked: R-88's test T-311 is failing" and a reason it can act on.

Nothing had to be copied out of Jira to do this. The gateway holds the mapping and the links, and fetches the records live under the caller's permissions.

## Our call

**Change ADR-0011 in four ways.**
1. **Add the kinetic half.** Add an Action type (name, typed parameters, the node types it touches, preconditions written as graph predicates, a failure message per condition, and an action log entry as a PROV activity). Start with five actions: merge PR, close ticket, mark requirement verified, supersede decision, relax constraint.
2. **Add interfaces.** Shared kinds (`WorkItem`, `ChangeSet`, `Requirement`, `TestRun`) that source-specific types implement. This is how several tools meet one model without being flattened.
3. **Name the PDLC links after OSLC wherever a standard name exists** (`implementsRequirement`, `validatesRequirement`, `satisfies`, `elaborates`, `constrains`). Invent names only for decision, pull request, blocks and supersedes. Bind every link to artifact digests in the in-toto subject shape.
4. **Version the ontology like code.** Use a branch and a proposal. A change that breaks existing links cannot be saved without a migration instruction, following Palantir's OSv2 rule. The schema version is recorded in every snapshot manifest.

**Change the gateway design in one way.** Make the ontology schema registry (component 15) the contract the registry, normaliser, planner and guard all read.
- Every backend manifest carries a versioned **binding**: which source fields map to which shared type and property, the identity key, and how the source's permission carries onto the object.
- **G7 then moves from serve time to bind time.** Items arrive typed because their source is bound, and serve-time tagging is kept only for fields the binding cannot type.
- The registry today lists kinds and scopes; it has no mapping, and "explicit lossy ontology mappings" (component 17) is named but not designed. The binding is that design.

**Do not copy from Palantir:**
- Types modelled by hand per customer. Keep a prescribed PDLC core and admit new types through a gate, as EvoOntology and EDC do.
- Copy-and-index as the default. Our rule is integrate-not-absorb, and Palantir indexes source rows into its own object stores.
- Permissions that stop at export. Our snapshots must re-check entitlement on replay.
- Writeback into systems of record as a first step. Actions here are checks and proposals; the agent's own tools still do the writing.

## 1. Palantir's Ontology, from its documentation (note N-SURVEY-20260928-17)

**Semantic half.**
- Object types, properties, link types, interfaces, and multi-datasource object types (one type backed by up to 70 datasources, joined on the primary key).
- Primary keys must be deterministic, or "edits can be lost and links may disappear".

**Kinetic half.**
- An action type is "the definition of a set of changes or edits to objects, property values, and links that a user can take at once". It has:
  - parameters
  - rules (create, modify or delete objects and links, or call a function)
  - side effects (webhooks)
  - writeback datasets
  - an action log with undo
  - submission criteria ("the conditions that determine whether an action can be submitted"), with a failure message per condition
- Functions hold the logic.

**Backing.** By default, the Object Data Funnel reads datasources and user edits and indexes them into object databases. That is a copy. Virtual tables (pointers to outside platforms) can back objects too; whether those objects are indexed was not stated in what we read.

**Permissions.**
- Viewer on the dataset gives access to its objects.
- Object and property security policies add cell-level control and classification markings.
- A user without access to one datasource of a joined object sees its properties as null.
- These controls "do not extend to downstream outputs or exports".

**Versioning.**
- Ontology branches and proposals, "analogous to a Pull Request".
- Breaking changes (datasource, primary key, property type, rename or delete of edited properties) require a migration instruction.

**SDK.** Typed code generated for the subset an app needs, with tokens scoped to those types and the user's own permissions.

**Agents.** AIP agent tools are Action, Object Query, Function and others. An action tool "can be configured to run automatically or to run after confirmation from the user".

**Which half we lack.**
- We have part of the semantic half: types and links, grounded in PROV-O, with PG-Schema documentation.
- We lack all of the kinetic half: no action types, no preconditions, no action log as ontology, no functions.
- We also lack the mapping part of the semantic half: nothing says how a Jira field becomes a property of our type.

**What transfers.** Action types with preconditions and failure messages; interfaces; deterministic source keys; mandatory migrations; null-on-no-access.

**What does not transfer.** A hand-modelled ontology per customer; copy-and-index; and "an ontology is a thing people build", where ours must also grow from agent traffic.

## 2. Other new ways to look at ontology

**Context graphs as decision traces** (Foundation Capital, Gupta and Garg, around December 2025, with a follow-up quoting Dharmesh Shah and Arvind Jain).
- New idea: "a living record of decision traces stitched across entities and time so precedent becomes searchable", including "we used X definition, under policy v3.2, with a VP exception, based on precedent Z".
- Evidence: none; it is a thesis.
- Fit: very high for us. It is our Decision node with its policy version, exception and precedent as first-class properties. Garg's refinement is to capture the "how" and infer the "why", which matches our ledger-first design.

**Microsoft Fabric IQ ontology** (N-SURVEY-20260928-18, preview).
- New idea: bindings as a separate artifact, and relationships carrying `confidence` and `effectiveAt`. Instances record "which source created them and when they were true".
- Evidence: none.
- Queries are routed to native engines, but the instance graph is materialised on a refresh schedule.
- Fit: good pattern, OneLake-bound.

**Open Semantic Interchange, now Apache Ossie** (https://github.com/open-semantic-interchange/OSI, Apache-2.0).
- New idea: a vendor-neutral file for datasets, fields, relationships and metrics, with an `ai_context` block (instructions, synonyms, examples) and `custom_extensions`. Only definitions are exchanged; data stays where it is.
- The spec in the repo is "version 0.2.0.dev0", a draft, and 0.2.0 is breaking. Press says v1.0 shipped in January 2026; we could not reconcile that.
- Evidence: none. Fit: weak (analytics metrics). Worth borrowing the `ai_context` idea for type descriptions shown to decision models.

**Graphiti and Cognee** (N-SURVEY-20260928-20).
- Graphiti offers prescribed types (Pydantic) or learned types, with an endpoint-typed `edge_type_map`.
- Cognee grounds extraction in an OWL file, in annotate mode (unmatched items kept) or strict mode (dropped).
- Neither publishes a number on whether typing helps.

**OpenBKN** (N-SURVEY-20260928-21).
- Object, Relationship, Risk, Action. Risk types gate action types before, during and after execution. Data virtualisation is claimed.
- The self-reported Q&A accuracy of 99.31% on 145 samples has no baseline and does not test the gate.

**Learned and self-evolving ontologies.**
- EvoOntology (N-20260928-07): its paired-evaluation gate was the largest ablation, at -11.2 points without it.
- EDC (N-SURVEY-20260928-25): canonicalising new relation types into existing ones kept 200 types at 0.956 precision against 280 at 0.724.
- AutoSchemaKG (same note): induced a schema at scale with an 8B model, with no admission gate.
- No paper ablates a type-admission gate on its own.

**Lifecycle standards** (N-SURVEY-20260928-19).
- OSLC RM, CM and QM already name most of our trace links, and integrate tools by linking to resources where they live. This is the only mature "federation without copying" design we found.
- ReqIF exchanges requirement files (a copy).
- OpenLineage (run, job, dataset, versioned facets), SLSA v1 and in-toto v1 (digest-bound subjects, typed predicates) are the right shape for "this PR at this digest was verified by this run".
- W3C PROV stays our base (ADR-0011).

## 3. Ontology as the federation contract

| Mechanism | Palantir | Fabric IQ | OSLC / semantic layers | Our gateway component | Missing in our design |
|---|---|---|---|---|---|
| Map source records onto shared types | datasource to object type column mapping; MDO | data bindings (identity keys, column to property) | Resource Shapes; OSI datasets and fields | registry manifest lists kinds only; normaliser adds tags | **the binding itself**: field to property, identity key, per backend, versioned |
| Shared type across sources | interfaces | entity types | OSLC classes (Requirement, ChangeRequest, TestCase) | none | interface types in ADR-0011 |
| Same thing across sources | deterministic primary key per source; MDO joins on the key | identity keys | URIs (one resource, many links) | fusion dedups by content hash and source id; G13 | cross-source identity rule in the binding (which keys are shared, for example a Jira key cited in a PR title) |
| Permissions carried | dataset Viewer carries to objects; object and property policies; null on no access | not described | owning tool serves its own resource | scope resolver, live authorisation twice | a per-binding rule saying how source permission maps onto the object, and null-per-property on partial access |
| Versioning the model | branches, proposals, mandatory migrations | "schema evolution rules" (unspecified) | `OSLC-Core-Version`; facet `_schemaURL` | component 15 "versioned with the manifest"; component 17 "schema migration" named | the migration rule: no breaking type change without a migration of existing links |
| Actions | action types, submission criteria, action log | Activator rules | none | none (the preflight retrieval mode in the PDLC doc is a query, not a check) | an action check the harness calls before acting |
| Snapshot and receipts | action log; branches | none | Configuration Management | snapshot composer, receipts | record the ontology version and binding versions in each manifest |

**The one change:** make the ontology schema registry the gateway's contract, with a versioned binding per backend, and move G7 from serve time to bind time (see "Our call"). The action check is a second, separate addition to the verbs, and the kinetic card tests it.

## 4. Where Jev or an open-weight System One model helps at this layer

| Decision | G id | Evidence | Source | Verdict |
|---|---|---|---|---|
| Map a source record or field to an ontology type | G7 | A small encoder retriever plus LLM rerank reaches 0.860 MRR against COMA++ about 0.35. LLM-only mapping falls from 0.79 (23 classes) to 0.51 (300 classes). A small type annotator loses about 5 points on an unseen serialisation. | N-SURVEY-20260928-24 | Some evidence; no Jev or typed-model row. **Sharpens G7**: do it at bind time, with a retriever before the Choice once types exceed a few dozen. |
| Same entity across hubs | G13 | A GPT-2 (124M) matcher reaches 81.96 F1 against GPT-4 at 86.36, at about 1/3,900 of the cost per 1K tokens. Cross-encoders beat bi-encoders; generative matchers help mainly under distribution shift. | N-SURVEY-20260928-22 | Strong evidence for small models on generic records; none on engineering records; no Jev row. **Sharpens G13.** |
| Type a proposed link | (none; linking) | Covered by N-SURVEY-20260928-14 (PAIChecker and others) and card PC-SURVEY-20260928-06 | existing | Not repeated here |
| Admit a new type into the ontology | (none) | EvoOntology gate by task score (-11.2 without it); EDC canonicalisation by sameness | N-20260928-07, N-SURVEY-20260928-25 | Some evidence, no System One row. A closed Choice (`same_as(k)` or `new`) fits a decision model (inference). |
| Check an action's preconditions before the agent acts | new, proposed **G14** | A 4B guard matches GPT-5.4 on step safety (83.0 / 83.3 against 83.0 / 84.4 Acc / F1) at 599.9 ms per call. Deterministic predicates cost 1 to 3 ms but LLM-written rules had 70.96% recall. | N-SURVEY-20260928-23 | Strong evidence for the mechanism on safety; nothing on PDLC preconditions; no Jev row. |
| Listwise rerank using ontology features | G4 | GAAMA: typed-edge propagation adds +1.2 points overall on LoCoMo, with the same model as judge. No ablation of type features in a reranker. | (not written as a note; arxiv:2603.27910, research agent's read) | Nothing usable. |
| Route by object type | G2 | WorkSurface-Bench: with gold routing, route F1 is 98.7 to 99.8% but answer accuracy only 56.1 to 75.3%, so routing is not the bottleneck. | (arxiv:2607.25765, research agent's read) | Weak. Do not prioritise. |

Builder reports: none found this run of Jev used for ontology typing, entity resolution across tools, or action checks. The Jev reranker reports already on the bus (hev/reranker, Hindsight) do not use type features.

## Limitations of this synthesis
- All reads went through a summarising fetch tool. Palantir and OSLC quotes should be checked against the live pages before external use.
- "Ontology helps agents" rests on vendor descriptions, not measurement.
- The G2 and G4 rows rest on papers read for this run but not written up as notes (below the bar).

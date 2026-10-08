# G06 to-tickets draft: incident to corrective action and feedback

Status: proposed for stakeholder review. No new GitHub tickets published, runtime changes, cloud execution or goal activation. Prepared with to-tickets. Parent scope already exists in #40 under #34; reuse it. #39 owns general conformance, #41 cloud verification, #36 projection semantics, #8 lookup correctness, #7 rejected-link exclusion and #10 extraction evidence. These broad issues remain open unless their complete acceptance is separately proved.

## User-visible outcome

A password-reset deployment starts accepting expired tokens. Engram records the incident, identifies the affected deployment using explicit scoped evidence, connects a corrective PR, records resolution, and preserves an authored lesson that a later specification explicitly cites. Retrieval explains what happened, what fixed it and what future work reused, with event evidence. Occurrence is not proof of cause; a merge is not proof of resolution; a recorded lesson is not automatically validated knowledge.

## Code-grounded starting point

Current PDLC3.0 defines Incident, Lesson, AFFECTS, OCCURRED_ON, ATTRIBUTED_TO, REMEDIATES, LEARNED_FROM and CITES. Detection and resolution have projection rules. incident.reported has a payload contract but no projection rule. No deterministic REMEDIATES or LEARNED_FROM projection is present in the inspected pack. Spec approval already supports explicit CITES; CITES does not currently allow DesignElement as source. Use a later Spec as the bounded feedback consumer rather than pretending direct HLD citation exists.

Incident detection currently chooses the latest deployment matching environment/artifact_id, without service/repository in the match. G04 deployment identities include repository/service. Cross-service selection and ambiguous ties need a concrete regression before classifying or fixing any defect; existing local tests cover temporal selection but do not establish this scope boundary.

Lesson extraction exists as a proposal from design/spec/core observation prose. That does not supply a deterministic authored incident lesson or prove its incident attribution. Keep inferred proposals separate from confirmed source declarations. The trace/preflight retrieval weights also need inspection for the new explicit journey edges; do not assume declared relationships are traversed by the chosen query intent.

## Proposed tickets

### T1 — Retrieve an incident with the correct affected deployment

Parent: #40. Blocked by: none within G06.

**What to build:** Send two deployment records through Engram, then report/detect the password-reset incident. Retrieve its identity, state, affected service and exact deployment, with their source events. Include a second repository/service with the same artifact/environment so lookup cannot silently choose the unrelated deployment. Decide and document the smallest supported incident producer contract, including reported versus detected behavior; event declarations alone are not implementation.

**Acceptance:**
- Explicit deployment reference uses its complete identity, or a scoped lookup has a documented unique-selection and temporal rule. Ambiguous references cannot silently select an arbitrary match. Occurrence does not imply causal attribution.
- A later deployment cannot be retrospectively selected for an earlier incident.
- An incident without sufficient deployment information stays retrievable with the missing relationship explicitly represented; missing is not a false success for deployment identification.
- Missing/ill-typed required identity fields reject before append; same-ID identical retry is unchanged, changed-content reuse conflicts without mutation.
- Retrieve incident→deployment/service and deployment→incident with exact typed nodes, edges and event evidence through real HTTP/worker/Spanner flow. Unrelated service/repository data must stay out.
- Verify unfamiliar local incident IDs in a second scope under the chosen identity policy; reject collisions rather than overwrite silently.

### T2 — Connect the corrective PR and record resolution without inventing causality

Parent: #40. Blocked by: T1 (incident contract and identity).

**What to build:** A producer explicitly declares that PR8 corrects the incident. Engram stores REMEDIATES from that Change to the Incident. Merge the fix, inspect the still-open incident, then submit a separate resolution event. Retrieval shows the fix and resolution evidence independently.

**Acceptance:**
- Complete source-declared PR and incident references map through pack contracts/rules; no new PDLC-specific engine dispatcher.
- Merge does not automatically resolve the incident; only the supported explicit resolution event changes its state. Fixing a problem does not imply causing it.
- A second incident and an unlinked PR do not acquire remediation or causal links from shared wording, service or commit.
- Malformed references reject before append. For well-formed references arriving before their artifact, pin one explicit placeholder/deferred/rejection policy before fixtures; no silent dropped link and no placeholder masquerading as completed remediation.
- Duplicate/conflict behavior and event-level evidence for the relationship and final state are checked. Late detection after resolution must follow an explicit lifecycle policy, preserving occurrence evidence without silently reopening the incident.
- Query both incident→fix and PR→incident, checking exact topology, lifecycle and evidence through actual Engram/Spanner.

### T3 — Record an incident lesson and prove a later specification uses it

Parent: #40. Blocked by: T2 (recorded corrective outcome).

**What to build:** Submit an authored lesson, “Check token expiry server-side,” explicitly linked to the incident and, where declared, the corrective PR. Submit a later approved Spec with an explicit citation to that lesson. Retrieve the chain from future Spec back to Lesson, Incident and corrective Change, and from Incident to the lesson and citing Spec.

**Acceptance:**
- Define a typed producer contract and deterministic mapping for authored Lesson/LEARNED_FROM, reusing existing types and generic projection. Freeze stable identity and attribution rules, including identical lesson text supported by distinct incidents; neither overwriting provenance nor merging lifecycle accidentally is acceptable.
- Declared lesson evidence is a producer assertion, not authenticated human approval. Keep tentative/validated meaning explicit; authored content does not auto-validate itself.
- Later Spec→CITES→Lesson exists only when explicitly provided. Similar prose and a second unrelated Spec must not create that link. This goal proves reuse in a specification, not automatic future design generation.
- Validate malformed lesson and citation references. Pin unknown-reference behavior and preserve exact revisions/pinned evidence without migration work.
- Natural-language and explicit-seed retrieval return declared lesson/incident/fix/citation evidence without unrelated incidents or treating inferred/proposed claims as confirmed facts. Restricted or rejected relationships follow the existing admission policy; exercise a rejected-link case through a supported Engram write path, or record an unsupported acceptance gap.
- Verify from Incident and future Spec starting points on real Spanner. When no lesson or no citation exists, retrieval must honestly show that absence or uncertainty, never fabricate feedback.

## Shared execution and verification contract

For each ticket, freeze inputs, expected graph deltas, forbidden outputs and retrieval questions before cloud execution. Use authenticated bound Engram API, actual ledger, all relevant ordinary workers, graph and retrieval API on real Spanner. Native source adapters are not implied: normalized producer examples must be labeled as such; if a raw incident adapter is promised, its translation becomes explicit acceptance before implementation.

Local regressions supplement cloud acceptance, never replace it. Preserve failures, source hashes, receipts, worker outcomes, exact artifacts/edges/provenance and no-write fingerprints. Run scoped review and relevant tests; reconcile known limitations without turning partial checks green. End G06 with verification document, stakeholder demo, issues updated and new-bucket assessment. No automatic G07, historical migration, Redis/Neo4j runners, ANN stress suite or hierarchy-policy implementation.

G05 retained dataset is protected. The current target must not be cleared, overwritten, extended under another pack version or reused without explicit stakeholder approval. Before G06 cloud execution, select an authorized separate disposable database or obtain explicit approval to clean/reuse the retained target. This resource decision does not block this ticket draft or local design work. Serialize cloud runs and preserve database ownership fences.

## Dependency graph and review checkpoint

T1 → T2 → T3. Each ticket is an independently demoable write-to-read journey; verification is embedded rather than split into a separate horizontal test ticket. G05 stakeholder delivery/reconciliation remains separate and must not be labeled complete merely because its cloud checks and Astra evidence review passed.

Review requested: Is this granularity and sequence right, and should any ticket be merged or split? Publish only after stakeholder approval of the breakdown, per to-tickets step4/5. Existing parent #40 is not modified by drafting.

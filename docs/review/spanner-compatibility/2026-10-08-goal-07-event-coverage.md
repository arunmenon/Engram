# G07 specification: complete the declared PDLC event paths

Status: SELECTED FOR EXECUTION by the stakeholder after scope discussion. Specification
is published; no implementation, new tickets, Astra review, cloud execution or completion
is claimed yet. Complete the ticket/review gates before runtime work. G08 is not started.

## Outcome and boundary

A producer can send every event declared by the selected PDLC pack through Engram,
and retrieve the promised artifact changes and their evidence from real Spanner.
In particular, a request must become a Request, a skipped test must remain skipped,
and a rollback must identify the exact deployment it changes. An accepted event
and zero worker lag cannot hide a missing domain mapping.

G07 closes declared-event gaps. It does not claim every PDLC journey, lifecycle
state, schema relationship, source integration or inferred assertion is implemented.
The [verification standard](goal-verification-standard.md) applies without exception.

## Code-grounded baseline

Baseline: branch `feature/engram-g06-incident-feedback`, commit `f243598`; runtime PDLC **4.2.0**. Pack SHA-256: `c062269b2aa48c380b52c3e149fd0959d0b7e6b25d992425d101887de91ce15d`.

The runtime pack is authoritative, not the old 23-event inventory or research copy.
There are **28 declared events, 24 with deterministic rules, four without**.
The existing local catalog test explicitly asserts this 24/4 split; it does not
prove cloud behavior. Successful scenario records from the six selected G1–G6
runs contain examples of **19 distinct event types**. Nine have no successful
example in those records: request.created, decision.recorded, ticket.updated,
ticket.closed, change.abandoned, change.committed, testcaserun.skipped,
service.rolledback and service.upgraded. This is an evidence inventory, not a
claim that no earlier diagnostic test ever exercised them.

The [28-row coverage matrix](2026-10-08-g07-event-coverage.csv) records required
fields, current writes/edges, exact prior run/scenario and the proposed slice.
Prior evidence is reused for design and regression selection, **not promoted to
passing on a newer pack**. Every row starts NOT RUN for G07.

Code anchors:
- `src/context_graph/ontology/packs/pdlc.pack.yaml`: events, projection, retrieval and types.
- `tests/fixtures/pack_contracts/pdlc.json` and `tests/unit/test_pdlc_payload_contracts.py`: all28 local examples, including four deliberately empty plans.
- `src/context_graph/sources/github.py`: GitHub skipped/neutral check translation already emits testcaserun.skipped; rollback/upgrade native adapter coverage is not provided here.
- `scripts/engram_goal03_implementation_demo.py` and G04–G06 fixtures/drivers: existing HTTP/worker/Spanner evidence machinery. Reuse narrowly; no new runner framework.

## Proposed slices and acceptance scenarios

Each slice is a write-to-read journey, independently demoable. These are ticket
**drafts**, not published issues. Reuse #40 (journeys), #39 (conformance), #36
(semantics), #37 (admission), #41 (Spanner) under #34. Check existing issues and
comments before publishing any new child. Slice E depends on A–D; A–D have no
necessary cross-slice dependency and are proposed in the order below for visibility.
Execute one selected slice at a time, with a checkpoint; no automatic move to G08.

### G7-A — Retrieve a request, its approved specification and scoped decisions

Why: the graph currently cannot materialize request.created, while decision.recorded
has rules but no successful example in our selected cloud runs.

- A01: submit `{source_system: "product", external_id: "RESET-REQUEST", title: "Prevent expired token use", description: "Reject password-reset tokens after fifteen minutes"}`. Create `Request:product|RESET-REQUEST`, status `new`, supplied content and DERIVED_FROM to this Event. Add Request to applicable pack retrieval seeds rather than a PDLC switch in engine code.
- A02: approve Spec `RESET-PRD|1` with `request_system: product, request_ids: [RESET-REQUEST]`. Assert Spec→Request REFINES, confirmed declared evidence, forward and reverse retrieval. A similar request in source_system `support` must stay separate.
- A03: record decision statement “Check token expiry on the server”, rationale, explicit applies_to_node_ids for the exact requirement/design created through the API. Decision ID is SHA-256 of the exact statement; status accepted; APPLIES_TO only those permitted typed endpoints.
- A04: a different statement explicitly supersedes A03 using supersedes_hash. Verify Decision→Decision SUPERSEDES, status-query historical/current labeling and event evidence. No supersession or APPLIES_TO from similar prose alone.
- A05: request with no title is valid under the existing optional-field contract and still accessible by exact typed ID; missing source_system/external_id rejects. Cross-source collision and undeclared/ill-typed reference handling are explicit fixtures.

Demo questions: “Which request does this specification address?” and “What decision
applies to this design, and which decision did it replace?” Freeze the exact response
node/edge sets per intent, including supersession policy, before cloud execution.
No Request→Incident RAISES claim is introduced.

### G7-B — Retrieve ticket progression, abandonment and a commit-derived change

Why: four existing mappings lack selected cloud acceptance; they must not be
mistaken for four new features.

- B01: create parent and child tickets through Engram; update the child from To Do to In Progress, change title, keep its identity and existing source events. Verify parent→child DECOMPOSES_INTO and only explicit requirement/design IMPLEMENTS references.
- B02: close one ticket as Done, another as Won't Do; expect `done` and `cancelled` respectively and their supplied resolutions. Closing a ticket does not merge its PR or satisfy its tests.
- B03: open a PR, abandon it, then reopen through change.created. Expect open→abandoned→open, one Change and separate supporting Events. A merged PR cannot become abandoned via a late abandon event under existing only_from guards.
- B04: send normalized commit `{repo: "g07/<run>/auth", subject: "fix(tokens): enforce expiry (#17)", body: "Fixes RESET-17", files: ["src/token.py"]}`. Expect scoped Change17, change_type `fix`, scope `tokens`, and the declared Jira WorkItem link. Check the exact current expression behavior before freezing fixture expectations.
- B05: subject without a PR number currently yields no Change despite valid envelope/contract. Preserve that as an explicitly documented ledger-only case, not a fake artifact pass; retrieval must not invent a Change. Capture the Event through Engram's normal event read path. A new commit identity model is outside G07.
- B06: exercise commit reviewer text separately: current rule can create Review from “Reviewers:” but does not declare REVIEWS or authenticated approval. Show what is actually produced and keep that semantic gap explicit; do not count it as reviewed code or silently add links. A larger reviewer-mapping feature requires a separate bounded issue if needed.

Demo questions: “What happened to this work ticket?”, “Was this PR abandoned or
merged?”, and “Which ticket does the commit-derived change implement?”

### G7-C — Show skipped verification honestly

Why: GitHub already emits skipped events, but their current deterministic plan is empty.

- C01: create a Change and normalized skipped test event with repo/test_id/run_id, outcome `skipped`, commit_sha and change_number. Reuse TestCase/TestRun, EXECUTES and optional RAN_AGAINST; TestRun outcome stays skipped and never counts as success or failure. No fabricated VERIFIES link without an explicit supported requirement reference.
- C02: translate reconstructed GitHub check_run payloads through the existing authenticated webhook API for skipped and neutral conclusions; both normalize to skipped. Record source wrapper provenance, translation, actual ledger payload and retrieval. This proves these two adapter cases only.
- C03: skip with no change reference remains a retrievable TestRun/TestCase with no RAN_AGAINST; malformed run/repo/test ID rejects. Tighten the skipped event outcome contract to `skipped` (proposed) so a mismatched `success` cannot masquerade as a skip.
- C04: finished outcomes success/failure/cancel/error remain independently visible with separate run IDs; query returns exact outcomes and evidence. A retry creates neither a new TestRun nor duplicate evidence.

Demo question: “Did this change pass verification, fail, or was its test skipped?”
Do not claim completeness plugin or all CI providers are covered by this slice.

### G7-D — Identify an exact rollback and a separate upgrade

Why: both events have provisional contracts but no mapping. Their meaning must be
settled before implementing any graph writes. The following policy is proposed,
not a description of existing behavior:

- D01: create succeeded deployment A and a later succeeded deployment B via Engram. A rollback names **B's exact identity**, using repo/service/environment/artifact_id plus a required `target_started_at` timestamp. That timestamp selects B; event.occurred_at is the later rollback observation. Do not choose the latest deployment by guesswork.
- D02: mark B `rolled_back` while retaining its original artifact, start time, prior observations, DEPLOYS/DEPLOYED_TO and rollback Event evidence. A is not automatically restored or marked active: the current schema does not represent live routing. A restoration, if demonstrated, is a separate service.deployed event.
- D03: repeat artifact IDs at different start times and across repo/service/environment. Only the complete selected key changes. A late service.deployed observation for the same B identity must not silently undo rolled_back; pin the minimal transition guard before the final fixture.
- D04: unknown exact rollback target uses the existing identity-only reference policy: the rollback declaration is preserved with a distinguishable reference-only target, and must not be presented as an observed successful deployment. Its original deployment event later fills it without erasing rollback evidence/state. Verify null observation provenance before fill and proper provenance after. If current generic mechanisms cannot express this honestly, report the concrete blocker before adding machinery or changing the policy.
- D05: an upgrade is a producer assertion of a **completed successful new deployment**, keyed by its own occurred_at using existing Deployment identity, with explicit change references where supplied. Add a small declared `operation: upgrade` property if needed to distinguish it in graph/retrieval; it does not automatically retire other deployments, prove traffic moved, or imply compatibility of old data.
- D06: missing target_started_at, naive/ill-typed target timestamp and malformed scoped identity reject before append. Upgrade with no changes has no invented DEPLOYS link; collision controls keep other services/repos separate.

Demo questions: “Which exact deployment was rolled back?” and “What artifact was
installed by this upgrade?” A rollback cannot be represented as a successful
upgrade, and upgrade success is a source assertion rather than an active health check.
No historical-data migration or ontology-version upgrade is involved.

### G7-E — Freeze and verify the complete declared catalog

Why: historical passes from different pack versions are not current whole-catalog acceptance.

- Freeze the resulting pack version, bundle, source archive and fixture/oracle hashes. Do not call it PDLC4.2 after changing its contracts/rules; choose the proper new version when implementing. Do not add events simply to raise coverage numbers.
- Execute at least one **unique valid event per declared type** on that final configuration. Reuse/adapt G1–G6 fixture values and independently authored expected outcomes; do not compute expected graph outputs using the projector under test.
- Run unchanged retry and changed-content same-ID conflict for each type. For every top-level required field, reject missing, null and wrong type; for nested references exercise required nested fields, empty strings where forbidden and invalid enums. Verify complete table fingerprints unchanged for all rejections/conflicts/duplicates, not just event counts. Freeze the exact generated scenario count in the manifest before the run; no pass count is promised now.
- Distinguish mapped cases, intentional ledger-only commit cases, explicit unknown references and failures. The four missing mappings must have real artifact paths; do not relabel them intentional no-ops to get a green catalog.
- Query every promised artifact and declared slice relationship with exact typed IDs, relevant properties/states, edge directions and supporting event sets. Cover forward/reverse intent paths, at least one original natural-language question per slice, unrelated scope controls and unknown IDs. An unresolved-ID discovery query may legitimately return other matches; assert candidate absence, not an invented ID-only lookup contract.
- Test the relevant nonempty reference/list branches and absent references explicitly. Catalog coverage is not every optional-field combination or every possible schema edge. Record branches not exercised, including inference behavior, in the final matrix rather than hiding them.
- Run existing affected local tests and scoped review, then the final real-Spanner acceptance. Do not rerun the entire original G1–G6 journey suites unless a changed behavior warrants it. The small all-event pass on the final pack remains required.

## End-to-end execution and safety

Use the existing normalized events API for synthetic producer contracts and webhook
API only for the native cases explicitly promised above. For every accepted input:
authenticated bound tenant → admission → Spanner ledger → ordinary applicable worker
loops → Spanner graph → Engram HTTP retrieval and evidence. Direct storage reads
are verification only, never setup or a substitute for Engram retrieval. No direct
artifact inserts, manual repair, mocked Spanner or memory/Redis/Neo4j runner qualifies.

Use mandatory core plus final PDLC, memory/user disabled. Record private-bound
single-tenant scope; this does not prove G08 core-only, public dispatcher or tenant
isolation. Record extraction applicability per event, real provider outcomes where
applicable and zero pending/dead-letter work; zero lag alone is not a domain-output
check. LLM-generated extra artifacts cannot silently contaminate exact oracles or
be deleted manually to pass. Any unevaluated-pack bypass and Monitoring IAM limits
must be disclosed, not turned into pack-wide evaluation claims.

G05 `engram-compat-target` and G06 `engram-g06-target` are retained and protected.
**No G07 writes, activation, pack changes or cleanup on either.** Proposed separate
target: `engram-g07-target` on portiq-mvp/engram-experiment, not created or checked
by this preparation. Verify existence, database-scoped service-account access,
empty owned dataset, schema and epoch before execution. Store tokens outside git
and never print them. Database allocation/access is a future execution prerequisite,
not authorization to touch retained data. Use registered keys and ownership fences
for failed attempts; successful G07 demo data is retained pending explicit cleanup
approval, following the user's retention preference.

Before each cloud attempt, snapshot read-only G05/G06 fingerprints and ownership;
compare after completion/failure. Serialize cloud runs. Safe preparation must fail
before writes on target/epoch/version mismatch, reused run IDs or insufficient
permissions. Preserve failed attempts and document oracle corrections separately.
No run command is invented here: publish the exact tested command once a runner exists.

## Definition of done and stakeholder verification

1. The final pack event set equals the fixture and results event sets; every declared
   event has an explicit disposition, no missing row and no silently accepted missing mapping.
2. A–D required journeys and the final E catalog acceptance pass through Engram on
   real Spanner on a frozen source/configuration; blocked/partial is not verified.
3. All required artifact properties, state changes, links and event-level provenance
   match predeclared expectations; forbidden cross-scope and causal/approval claims stay absent.
4. Independent Astra review covers semantics, harness false-pass risks, implementation
   and final evidence as required. This preparation has not commissioned or received that review.
5. Complete the [G07 verification document](2026-10-08-goal-07-verification.md), deliver
   a recorded or explicitly live stakeholder demo, and update affected GitHub issues
   with actual receipts/status/remaining acceptance. Assess whether any discovery needs
   a distinct feature bucket. Do not close broad #34/#39/#40/#41 from catalog coverage alone.
6. Stop after G07 delivery; G08 requires separate approval. The retired broad goal stays paused.

Suggested demo order: request→approved Spec; decision→design and supersession;
ticket progression→abandoned/reopened PR→commit; skipped versus failed/passed test;
exact deployment rollback and explicit successful upgrade; finally the 28-row
expected/actual table, failure evidence, issue updates and remaining boundaries.

## Review and next action

Review the proposed rollback/upgrade semantics and slice sizes above. Then use
`to-tickets` to publish only approved missing work with native blocking edges under
the existing umbrellas, reusing existing issues rather than duplicating them.
`implement-spec` is for execution after authorization, not this preparation.
The local `to-spec` skill is absent; this is a persisted manually prepared spec,
not a claim that the missing skill ran or was installed. No new orchestration,
adapter generator, framework or foundation rewrite is justified by this plan.

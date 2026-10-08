# G02 scoped design review

Reviewed the G02 planning-journey proposal, current PDLC 1.8 declarations, keyed placeholder/provenance projection behavior, extraction declarations, and artifact traversal selection. Design review only: no implementation acceptance or cloud execution.

**One blocking omission before acceptance implementation:** the proposal adds APPROVES but does not specify retrieval intent weights for it. `ArtifactRetriever` traverses only weighted edges (`retrieval/artifacts.py:266-297`); the present trace/status weights contain no APPROVES, and trace does not include SUPERSEDES. Merely declaring/projecting these edges cannot establish PL11's approval/version differences through the API. Minimal fix: explicitly add APPROVES to the intended pack retrieval intents, define whether trace also follows SUPERSEDES or use a separate status query, and predeclare those queries and expected returned edges. Keep this pack-only; no traversal bypass is needed.

The remaining direction is sound within its stated boundary: breaking 2.0 composite revision keys preserve separately named revisions on an empty target; keyed references produce identity/default-lifecycle placeholders without content-event provenance; later actual content fills the same identity; deterministic declarations remain distinct from live LLM proposals. New payload contracts must require all revision-key fields on both subjects and references, and DesignApproval must participate in DERIVED_FROM provenance. These are implementation requirements to verify, not accepted implementation claims.

Approval scope must remain described precisely: the proposal expressly permits later events to mutate the same artifact identity. Therefore this proves approval attached to a named revision key, not immutable approved content or globally immutable approval identity. Do not claim otherwise. Likewise, a SUPERSEDES edge can support retrieval supersession without implying the interpreter automatically transitions the older node's stored lifecycle state.

Retaining real extraction is appropriate. The execution manifest/cleanup must account for its actual proposed nodes/edges through recorded provenance and fail closed on unowned keys; predeclared deterministic artifacts alone are not the entire possible write set. Provider failures must remain blocking, as the proposal specifies.

Verdict: proceed with the minimal pack implementation after making the retrieval declarations/PL11 query contract explicit; independently review the resulting pack and harness before cloud acceptance. No broader architecture changes requested.

## Precloud implementation review

The retrieval-weight omission is fixed. Versioned subject/reference keys, keyed placeholders, real catalog authentication, generic HTTP ingress, five consumer tasks, and provider construction follow the proposed path. No direct fixture insertion found. Historical migration and reviewer/content immutability remain outside the stated claim.

Blocking findings before full acceptance:

1. **P1 — negative verdict projects positive APPROVES** (`pdlc.pack.yaml:90-93,1003`). DesignApproval allows `changes_requested`, but the rule always creates a confirmed APPROVES edge. A rejected design is therefore represented with the same approval relation as an approved one. Minimal G02 fix: restrict this approval event to `approved`, or condition the APPROVES edge on the approved verdict and test the negative case. Do not infer approval merely from a recorded review.

2. **P1 — required connected retrieval is not verified** (`engram_goal02_fixtures.py:223-247`; `engram_goal02_planning_demo.py:292-322,451-490`). PL04 only retrieves its own node with status intent. PL11 has no HLD-v1 query; its LLD status query requires only LLD, and the requirement query checks nodes but no REFINES edges. Missing/broken returned LLD→HLD→Requirement→Spec relationships can pass despite the required connected journey. Minimal fix: add an LLD trace query before v2 supersedes v1, the explicit HLD-v1/history query, and exact expected returned path/edge assertions; retain the separate status history checks. PL01 should also assert its supplied scope/source, rather than title/status alone.

3. **P1 — real extraction failure can be recorded as success** (`engram_goal02_planning_demo.py:337-359`; existing `worker/pack_extraction.py:151-160`). The ordinary consumer logs malformed model answers and returns, so zero lag/no dead letters does not prove successful triggered inference or absence of extraction errors. With the configured 1024-token cap, this is a concrete acceptance risk. Minimal fix: collect the real consumer's per-event applied/invalid/error outcomes in run evidence and require a successful extraction outcome for each design source event (zero valid proposals is acceptable). Observation/log capture must not substitute a provider or alter its answer. Malformed/failed results must make the affected run fail.

Cleanup's bounded provenance predicate is narrow enough for this disposable empty target: generated artifacts need a registered Event link and every deleted edge must have owned endpoints, followed by the existing exact-owner transactional cleanup guard. It is not permission to clean unrelated databases or accept inferred links as deterministic expected results.

Verdict: implementation not yet accepted for the full run. PL01 alone does not exercise these design/LLM gaps; its checkpoint can proceed if explicitly reported only as the Spec ingress checkpoint, while the three findings are fixed before the full journey.

## Focused recheck

Approval semantics and extraction observation blockers are resolved by inspection: both approval schemas accept only `approved`, a negative-verdict 422 fixture exists, and matching real per-event/per-pack extraction outcomes must be present and exclusively `pack_extraction_applied`. The processor observes actual consumer logs without changing model responses; missing capture fails closed. Connected PL03/PL04 queries and explicit HLD-v1 status retrieval are now present.

One small remainder of finding 2: connected response assertions check the node chain but only assert the LLD→HLD edge (`planning_demo.py:517-523`). A response omitting HLD→Requirement or Requirement→Spec edges can still pass. Add the exact expected REFINES triples for PL03/PL04 (both requirements to Spec, HLD to both requirements, and PL04's LLD links), and required chain edges for the HLD-v1 PL11 query. This is an assertion-only fix; no architecture/runtime expansion needed.

PL01 checkpoint remains cleared. Full-run review clearance follows that final edge-assertion addition; no other blockers found in the requested delta. No cloud execution or implementation acceptance claim made.

## Full-run preflight clearance

The remaining assertion gap is fixed: `retrieve()` now requires every predeclared expected edge whose endpoints are both required by the query. This covers the PL03/PL04 chains and PL11 HLD-v1 chain. The ledger authority comparison now correctly uses `binding.bundle_digest`, consistent with the tenant acceptance contract, rather than the active pack bundle's distinct identity.

**No remaining blocking findings in these reviewed changes. Cleared to execute the scoped G02 full run after the PL01 checkpoint.** This is preflight code-review clearance, not successful G02 runtime acceptance. The reported failed PL01 attempt and its cleanup were not independently re-audited in this narrow delta review; retain their original failure records. No cloud calls performed.

## Issue #46 implementation recheck

No blocking findings in the focused `_traverse` change. Drifted rows arrive through the existing validated-neighbor path, are deferred until same-level node selection finishes, and contribute only an edge when both endpoints are selected. They cannot create nodes or alter scores/frontiers; subsequent admission remains unchanged. The triangle regression asserts the previously missing LLD→Requirement edge, excludes both unrelated siblings, and confirms a rejected edge remains excluded while its endpoints remain visible.

The runner now records parsed retrieval responses before acceptance assertions, preserving evidence for failed graph-response checks. **Scoped G02 rerun is cleared once the affected local regression checks pass.** This is implementation review of the repair, not a claim that the rerun or full G02 acceptance has passed. No cloud calls performed.

## Final G02 evidence review — all-03

**No blocking findings in the bounded technical acceptance evidence.** Reviewed all-03 observations, fixtures, manifest, executed-source hashes and the verification walkthrough against the reviewed harness. All recorded source hashes match current files. Independently verified 22 passing subchecks across PL01–PL12, twelve accepted ledger identities, thirteen exact declared planning edges, five zero consumer lags for every ingress step, and unchanged snapshots for four rejects plus the duplicate.

All six unique design events have actual `pack_extraction_applied` outcomes, with no invalid/rejected outcomes in this run; zero-proposal results are correctly allowed. Required final retrieval nodes and edges match the fixtures, including approval only on HLD v1 and revision supersession. The expiry-seeded sibling expectation correction preserves the existing anti-drift contract, with both-requirement coverage retained in HLD-seeded checks.

Cleanup evidence shows all seven application tables empty and the intended core owner active at epoch 28, without shutdown errors. Prior all-01 and all-02 failures remain retained and independently show empty post-cleanup tables. The walkthrough accurately distinguishes synthetic normalized ingress, private bound authentication, actual LLM extraction, named-revision approval limitations, and unverified historical migration/public tenant dispatch. Publication/GitHub reconciliation remain explicitly pending and are not implied complete by this technical verdict. No cloud calls or reruns performed.

## all-02 retrieval oracle review

Astra reviewed the retained failed all-02 response and fixture. Requiring the sibling single-use Requirement in an expiry-seeded trace contradicts the existing sibling-drift rule. The response contains the expiry path with no truncation; the preceding HLD-seeded query returns both Requirements and their Spec links. Remove only the sibling requirement expectation, retain exact stored-graph and HLD-seeded assertions, keep all-02 failed, and rerun. No additional engine change.

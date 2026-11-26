# Relationship-default impact of pack edits

Issue #87, ARCH-1-002. Base b0bfcf688307f51d3cda8de9290cea31b17ecc0d; branch fix/87-link-default-impact.

## Product flow and chosen boundary

An operator changes an existing pack's relationship defaults, for example from confirmed to proposed. New graph construction can then give links a different status while existing links retain the old value. The comparator currently ignores effective defaults and may describe the edit as harmless documentation. This is an engine upgrade-assessment issue, not an authoring-agent or new UI feature.

Compare effective composed defaults, not arbitrary policy text. Any added, removed or changed effective relationship default is conservatively graph-breaking and needs the existing fresh-graph rebuild path and version requirement. This is deliberately stricter than automatic in-place replay: merge writes retain removed default properties. A changed value can converge in the demonstrated memory case; applying the rebuild rule to all effective-default edits is a conservative policy, not proof that every changed value needs reconstruction. Create-only extraction links do not consume these defaults. No new automatic graph edits, cutover, generic migration framework or bypass is authorized. Existing administrative allow-breaking overrides remain explicit and do not prove reconstruction.

Verification uses the established public seams: classify_change/version requirements, PackProjector plus MemoryGraphStore, reconcile refusal and rebuild into a fresh target from preserved source events. Observe actual link values for a complete retained example; do not claim a question score proves all link state. Preserve current fixtures, business expectations, admission compatibility, normal/pre-1.0 version rules and unchanged effective-default no-ops. Policy validation, foreign-contributor ownership and full migration of out-of-ledger operator decisions remain separate. At most two Fable calls ($5 each), stop early on acceptance. No cloud/provider/deployment or merge without further user authorization.

## Verification

The runtime diff adds one comparison to the existing edge classifier. The new test file has five public-seam cases. The original confirmed-to-proposed comparison fails on the base (additive instead of breaking) and passes after correction. Addition/removal cases preserve the same declared property schema, so their result cannot be explained by preexisting property-removal detection. An implicit confirmed default remains equivalent to an explicit confirmed default, and pre-1.0 version requirements remain intact.

The retained-event memory example constructs a confirmed link. With an adequate major version, normal reconcile still refuses both a changed default and a removed default before altering the original graph/state. Rebuilding separate fresh targets produces proposed status or no status respectively; the original graph and source documents remain identical. This synthetic pack has no retrieval intents, so its successful build is not a question-score or full tenant-migration proof.

85 focused/versioning/admission-impact tests pass. The broader selection passes 895 tests, including memory end-to-end controls, with 4 external-backend cases deselected. It covers projection/extraction, admission/contracts, ownership/trust, readiness, composition, versioning and hex purity. Ruff check/format, runtime-module mypy and whitespace checks pass. Local Python3.14 differs from Python3.12 CI, which targets main rather than this integration branch. No live Spanner/provider/UI run was made.

Local evidence: `output/implementation/ontology-v2/slice87-links/`, including red/green comparator output, `focused.txt`, `regression.txt` and `review-manifest.json`. These local paths are not published artifacts.

## Independent review and disposition

[Fable round 1](link-default-impact-fable-round1.md) returned PASS with no blocking defect. It reproduced the old failure independently, verified the final policy, downstream version/refusal/readiness gates and recorded-state round trip, and ran the 85 focused tests. It also demonstrated that changing the value converges in its one-edge memory replay while removing the default does not.

Both nonblocking wording corrections are applied: the code comment no longer cites extraction's create-only behavior as a reason for this projection-default policy, and the module's breaking-change documentation now names effective defaults. The initial status text Fable read was superseded during review; this final record reports completion. These are documentation/comment-only changes after the reviewed source. Fable explicitly requested no second round for them. One of at most two authorized review calls was used; reported cost $2.451401. Original peer report unchanged; reviewed/final hashes are retained separately.

Conservative limits: a changed effective default remains breaking even when a rule overrides it or no rule writes that edge. The fresh-memory example establishes the specified retained-event behavior, not cross-backend convergence or production cutover. Existing explicit allow-breaking can record a version without reconstruction; this slice does not strengthen that override or claim it is safe migration. Invalid status values and dropped rule-level property sets remain separate findings.

Status: implemented, verified and independently accepted for the bounded scope; delivered in a draft PR into Ontology V2. No merge or deployment.

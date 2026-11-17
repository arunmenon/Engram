# Video rehearsal — 2026-11-03

Scope: current local Chrome workbench, real Spanner sandbox, synthetic frozen PDLC stories. This is preparation for the reviewed video plan, not a deployment or a full recording signoff.

## Observed runs

| Scene | Fresh result | Meaning |
|---|---|---|
| Implementation | 111 passed, zero failed/unsupported/errors; Spanner cleanup verified | Ready to demonstrate this saved story |
| Planning | 79 passed, zero failed/unsupported/errors; Spanner cleanup verified | Ready to demonstrate revision/approval behavior |
| References | 13 passed, zero failed/unsupported/errors; Spanner cleanup verified | Ready to demonstrate reference boundaries |
| Release | Failed before execution: ValidationError, reference `7e056bdbbd7b` | Do not present as a passing Spanner scene |
| Assistant journey outline | First proposal failed validation (`6a7b0ffe3373`); second succeeded after stage-specific format guidance | Real-provider recovery observed; generation and execution still need inspection |

Screenshots and media are under `output/video/rehearsal/`. The first implementation attempt failed authentication (`52f9207cf9d8`) and cleaned up. The acceptance-only launcher reused an expired startup token for later clients; fetching a current token per client allowed the successful retry. Production authentication code was not changed.

## Release mismatch diagnosis

`release_journey()` declares `webhook:github` and `webhook:jira` as trusted producers. `SpannerExecution._claim()` copies those values into `settings.ontology.trusted_source_ids`. That setting accepts authenticated source IDs matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`, so colon-bearing legacy agent aliases fail when tenant settings are validated.

Reproduced without database writes by assigning the two IDs on a Settings object and validating its serialized form. Result: `ontology.trusted_source_ids: Invalid authenticated source ID`.

This needs an explicit distinction between legacy event agent identities and authenticated synthetic producer identities. Do not relax the authenticated-ID validator or silently rename frozen fixture identities to get a green shot. The UI's generic proposal error is also misleading for a journey-execution configuration failure. Preserve this as a visible limitation until the harness identity contract is reconciled and tested.

## Architecture guide preparation

Updated `docs/research/2026-10/walkthrough.html` in place with a dated scope notice, UTF-8 encoding, mandatory core versus optional memory/user packs, PDLC's 18 types including DesignApproval, tenant-bound payload/handling/processing checks, and explicit versus discovery seed selection. Checked loader, PDLC YAML and admission compiler. Opened the rendered page in Chrome and inspected the pack-layer view. Historical benchmark and infrastructure sections remain historical; do not film them as current operational claims.

## Production preview

`output/video/rehearsal/architecture-screen-voice-preview.mp4` is a 29-second 1920×1080 MP4 with an audio stream. It uses an actual guide screenshot and local synthesized Daniel narration at 140 words/minute. It is visibly labelled as a still-frame rehearsal. Inspected an encoded frame for readable text; speech naturalness still requires listening review. It is not a screen-action recording or the finished walkthrough.

## Technical appendix checks

`pytest tests/unit/test_ontology_cli.py tests/unit/test_pack_versioning.py -q`: 38 passed. Log: `output/video/rehearsal/lifecycle-tests.log`. These are local automated checks of CLI helpers and pack lifecycle behavior, not a fresh persistent-backend CLI/API recording. Do not substitute them for the planned live lifecycle scene.

## Still required

- Finish and inspect the assistant-generated journey, preserve baseline expectations, then run the saved variant.
- Rehearse the current ontology-onboarding UI from supplied evidence through reviewed results.
- Decide how the release mismatch is addressed or explicitly presented; no success claim is authorized by this failure.
- Rehearse the exact backend lifecycle commands on a disposable persistent target.
- Finish source/configuration manifest, shot timing, script review and final recording/caption QA.

No full video, production activation, ontology change or frozen-oracle modification is claimed here.

## Completed follow-up in the same rehearsal

The assistant-generated retry variant was independently compared with the baseline before saving. All seven original event envelopes and all thirteen original checks were retained exactly. The first generation omitted the requested unchanged checkpoint; a second generation added it. Its duplicate disposition uses 201, which the runner contract explicitly accepts for created/duplicate outcomes; the operator's earlier suggestion of 200 was incorrect. This was checked against the runner before execution, not adjusted to observed output.

Saved through the UI as a separate reviewed workspace, then run through the UI on Spanner: **15 passed, zero failed/unsupported/errors**, cleanup verified. Selected delivery 8 and observed **duplicate**, with 11 domain nodes and 11 edges. The explicit unchanged checkpoint passed. Baseline remains a separate seven-delivery workspace. Evidence: `assistant-variant-reviewed.json`, `assistant-variant-passed.png`, and `verified-runs.json` under the rehearsal output directory.

The existing real-provider-authored Northstar pack was revalidated without a new authoring request and rerun through the UI: revision 35, both US/EU questions exact matches, mean F1 1.0 against 1.0 on Spanner, cleanup verified. Rehearsed setup, three-source evidence inventory, model review, readable expected-entity choices, trust, testing and handoff screens. This is saved-authoring-history plus fresh execution, **not a new ontology-generation session**. Approval remains unclicked. Evidence: `northstar-current-result.json`, `northstar-refreshed.png`, and `onboarding-*.png`.

A 310-file source/input archive and SHA256 manifest were generated and verified: `source-snapshot.tar.gz`, `source-manifest.json`. Credentials and runtime SQLite data are excluded. This is a rehearsal snapshot; refresh the manifest for final capture after further edits.

Remaining filming decisions and work: release identity mismatch; exact persistent-backend lifecycle rehearsal; whether to show clearly labelled saved ontology-authoring history or rehearse another fresh generation; final script/voice review and shot timing. The guide changes cover the selected architecture scenes, not every historical claim on the long page. Full recording remains pending.

## Release remediation scope (authorized follow-up)

The sandbox must accept the reviewed legacy event envelopes without treating their agent aliases as production authenticated source IDs. The smallest shared fix maps every sample producer to a deterministic `sample-<sha256>` source ID in both the sandbox principal and the run's trusted-source policy. Mapping all producers prevents a literal alias from impersonating another alias's encoded ID. Event agent IDs, payloads, pack semantics and frozen expectations remain unchanged. Production source-ID validation is unchanged. Run metadata explicitly identifies synthetic attribution; this remains a sandbox, not a test of external producer authentication.

Verification includes a bound-settings test with legacy GitHub/Jira aliases, an untrusted producer and a literal encoded-ID impersonation attempt, plus event-envelope immutability, affected workbench tests and the real release journey through the UI. No new production service or identity adapter is introduced.

## Remediation and lifecycle verification completed

The sandbox source-identity fix passed 55 affected workbench/journey/execution tests, scoped Ruff, and mypy on execution.py. The test preserves event envelopes, accepts colon-bearing legacy aliases via synthetic source mapping, and rejects trust inheritance by a producer whose literal name equals another producer's mapped ID. No production source validator changed.

Fresh release execution through Chrome on real Spanner: 33 passed, zero failed/errors, one explicitly unsupported group (original API/worker checks outside normalized replay). Cleanup verified at epoch 20. The frozen pack, event envelopes and expected answers were not modified. Evidence: `output/video/rehearsal/release-source-fix-result.json` and `release-ui-verified.png`. This supersedes the release blocker above; the unsupported group remains intentionally visible.

The command-line rehearsal harness `scripts/rehearse_workbench_lifecycle.py` ran on an exclusively leased real Spanner sandbox. It uses the actual artifact router and the actual CLI evaluation routine, with no mocked retrieval or evaluation response. Observed initial change classification; explicit trace request returned 409 while pending; frozen release events were projected; all 11 evaluation questions scored F1 1.0 against 0.95 and were recorded; recorded pending list cleared; the route returned 200 with Spanner provenance. Cleanup verified. Final rerun additionally asserts no failed/error checks or dead letters while retaining the one unsupported group. Evidence: `output/video/rehearsal/lifecycle-spanner-final.json` and `.log`.

The harness uses ASGI in-process and TTL zero for explicit refresh. This does not establish network authentication, shell CLI startup configuration, default-cache refresh timing, or a live blue/green cutover. Those boundaries must stay in the narration. Candidate-only additive/mapping/breaking classifications and version bumps were verified with the actual classifier; no changed pack was activated (`change-classification.json`).

The concrete script and 29-second synthetic voice/screen preview have been submitted for recording review under the existing video plan. No final video has yet been recorded. The source snapshot was refreshed after the code fix; refresh documentation hashes once this appended review is final.


## 2026-11-04 automated narrated recording

Adapted the ship-manager Playwright/macOS speech/ffmpeg approach in
`scripts/video/`. The recording uses isolated Chromium pages, synthetic Samantha
voice, and explicit scene windows; desktop switching and sign-in are omitted.

Fresh UI operations during filming: Northstar revalidation and Spanner sandbox
run (epoch 23, cleanup verified); PDLC reference-story Spanner run (epoch 24,
cleanup verified). Northstar returned both reviewed question answers at F1 1.0;
PDLC returned 13 passed, 0 failed, 0 unsupported, 0 errors. No approval or live
activation was performed. The saved assistant-authored pack and retry story are
explicitly identified as prior authoring history; no new model call is claimed.

A recording selector initially required an exact label although the select's
accessible label included its options. Recording stopped at the rejected-event
scene. Removed exact matching and resumed; retained earlier completed scenes.
No expected outcomes were changed. Status banners also required deliberate
scroll framing. The reviewed scope is a narrated overview, not the original
40–45 minute exhaustive feature inventory. Other PDLC stories, lifecycle CLI
operations, and a fresh authoring call remain outside this cut.

Final export QA (2026-11-04):
`output/video/assembled-agent-detail-20261104-135205/engram-walkthrough.mp4`
is 417.64 seconds (6:58), 1920×1080 H.264 with AAC narration, selectable English
captions and 20 chapters. The earlier nine-minute estimate included a faulty
interrupted take. Its unfinalized tail produced an audio-only result scene;
that scene was replaced from the current UI and excluded from the original
manifest. The assembly now rejects missing video/audio streams and uses separate
decoders for joins. Strict full-export ffmpeg decode passed. Sampled final frames
at 253s and 343s visually confirm readable Northstar and PDLC passing Spanner
reports. Narration is synthesized locally, and captions use approximate sentence
timing. This is the overview review cut, not the exhaustive feature walkthrough.

### Framework-first editorial revision (2026-11-04)

User feedback: the video entered the workbench before explaining what the pack
framework contributes. Added a six-screen explanatory opening, with purpose and
pack composition before any domain example. One incident then connects contracts,
identity, mappings and retrieval to the operator workflow. Moved the recorded
handoff scene after both domain demonstrations and saved assistant story authoring.
The previous delivered cut is preserved.

Sources checked: current `core.pack.yaml`, `memory.pack.yaml`, `user.pack.yaml`,
`pdlc.pack.yaml`, the recorded Northstar draft and existing evaluation/activation
script guidance. The visual explains that dependencies and names are checked
across a bundle; it does not claim composition provides tenant isolation.
Expected questions remain evaluation material alongside the pack. Diagrams are
labelled explanatory. No new model calls, sandbox jobs or activation were needed
for this editorial revision.

Rendered checks: all six chapter links select the correct screen; every section
fits above the footer at 1920×1080. Inspected composition, domain-definition,
runtime and readiness screenshots. Exact narration is in the recorder, and
comprehension desk checks are appended to `docs/engram-video-narration.md`.

Revised export:
`output/video/engram-framework-walkthrough-20261104/engram-walkthrough.mp4`.
Duration 577.94s (9:38), 23 chapters, 1920×1080 video, synthetic narration and
selectable captions. Strict full-file decode passed. Caption bounds and ordering
passed; all 17 UI scenes occur once and Handoff is last. Inspected the final
UI transition and handoff frames, plus the six-screen opening render. Export
check metadata is saved beside the MP4 as `export-checks.json`. Recorder and
assembler lint checks passed. The full-feature recording remains outside this
review cut; saved assistant authoring is not a fresh model execution.

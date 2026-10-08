# Cleaned G03 — scoped Astra evidence review

No blocking findings in retained run `20261008-cloud-cleaned-g03-01`.

- All 28 checks pass: 23 input steps (17 unique accepted events, one duplicate, one conflict and four invalid requests) plus five final retrieval checks. Every input records five zero worker lags. The retained driver preserves actual authenticated TCP HTTP, real Spanner stores, all five worker loops, exact ledger/domain graph checks and retrieval provenance assertions.
- Independently comparing snapshots confirms the duplicate, conflict and four invalid requests leave persistent state unchanged. Declared-link and omitted-reference assertions remain intact.
- Each of four seeded final queries returns the eleven required main artifacts and fourteen declared edges, excluding forbidden unrelated-feature and unlinked artifacts. Both Alex's `changes_requested` review and Robin's `approved` review remain visible, alongside failure and success test runs. Both `RAN_AGAINST` edges retain `commit_sha: abc123`. The text-query oracle establishes expiry-requirement discovery only; its additional returned graph is not promoted into stronger coverage.
- Two real `pack_extraction_applied` outcomes retain three schema-rejected link proposals. Valid generated nodes were applied; this is evidence of extraction plus schema filtering, not acceptance of every LLM proposal. Generated ownership proof and the final graph snapshot remain recorded.
- All 189 recorded source hashes match archive members, current files and commit `13e9d12be28feee1d05d0325f67ff35466a70921`. The manifest's nonempty dirty-diff digest must not be described as a clean checkout, but the independent per-file comparison establishes unchanged archived code/helpers/fixtures. No weakened oracle was found.
- Cleanup removes seventeen events, 41 nodes and 61 edges, leaves all seven application tables empty and restores the original active core owner/binding/digest from epoch 38 to epoch 40. Shutdown errors are empty.

Scope remains the declared G03 private bound-app experiment with synthetic producers, actual configured extraction and explicit `serve_unevaluated`. It establishes no public dispatcher, raw adapter, historical migration or G04 result. The retained metrics-export permission error is outside the application assertions; successful monitoring export is not claimed.

Evidence/source inspection only. No code changes, tests, cloud calls or delegation performed.

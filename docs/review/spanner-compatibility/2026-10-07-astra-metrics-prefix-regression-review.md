# Metrics prefix regression review

2026-10-07 — Astra low, source and retained-evidence review; no tests/services/cloud executed.

**Approve the minimal fix. No blocking correctness or cardinality regression identified.** Installed FastAPI retains the original route object for included routers but carries the selected composed template in its effective route context. Preferring that context's `path_format` restores `/v1/context/{session_id}` without interpolating the actual session ID. Existing route/path fallbacks remain unchanged.

The strengthened metrics test first requires HTTP 200, then checks absence of the resolved ID label and presence of the full template label. Retained `20261007-local-unit-regression-03/pytest.txt` reports **30 passed, 6 warnings**. Adding `conflict: 0` to the import-summary expectation matches the earlier explicit outcome extension.

The fix intentionally couples to FastAPI's internal `scope['fastapi']['effective_route_context']` shape. Keep this focused integration regression when upgrading FastAPI; a future shape change could lose prefix fidelity even while the legacy fallback still returns a template. Existing raw-path fallback for unmatched requests remains a pre-existing cardinality limitation, not introduced or resolved by this change. No broader feature or full-suite completion claim is made.

# G07 runtime P2 recheck

**Verdict: original P2 resolved; no further blocking findings in the reviewed runtime scope.** Read-only recheck at `d379637`, including the generic date-time extension from `e545d72`, against the prior scoped A–D/catalog review. No repository edits or cloud calls.

`src/context_graph/domain/pack_contracts.py:51` permits only the known `date-time` format literal; the shape check at line 55 rejects it for non-string fields. `_date_time` at line 114 checks the bounded lexical subset, real calendar validity and UTC representability, converts normalization overflow into structured validation failure, and returns the original string. `_field_type` applies it after existing strict-string constraints and before the nullable union. The runtime and research rollback contracts now use `format: date-time` instead of the calendar regex.

Independent direct probes confirmed both original failures reject: `0001-01-01T00:00:00+01:00` and `9999-12-31T23:00:00-02:00`. Exact UTC bounds `0001-01-01T00:00:00Z` and `9999-12-31T23:59:59.999999Z` remain accepted with unchanged strings. Leap-day validity and trailing-newline rejection were also checked. Deployment tests independently assert canonical projection identities for UTC and representable offset year boundaries.

Validation: **233 passed** using `PYTHONPATH=src .venv/bin/python -m pytest -q` over `test_pack_payload_contracts.py`, the four A–D `test_g07_*` modules, `test_pdlc_payload_contracts.py` and `test_ontology_packs.py`. The prior runtime assessment otherwise stands: Request mapping/seeding, no-PR guard, skipped outcome, exact rollback action/reference evidence and late-fill guards, upgrade semantics, pack 5.0.0 and the unchanged 28-event catalog have no additional blocking findings.

This is **not cloud proof**. Harness behavior, real Spanner persistence, authenticated webhook execution, no-write fingerprints and final HTTP/catalog acceptance remain outside this recheck and require separate review/evidence.

---
schema_version: 1
artifact_id: REV-YYYYMMDD-NN
artifact_type: review
producer: challenger
run_id: <invocation id>
created_at: <UTC>
input_refs: [{artifact_id: E-..., file_id: ..., sha256: ...}, {artifact_id: <note or belief>, ...}]
outcome: ready | revise | insufficient_evidence
---
checked: <what was actually inspected: sources, tables, baselines, leakage, budget>
not_verified: <what remains unverified>
findings:
  - <attribution / baseline / leakage / alternative explanation / budget>
requested_corrections:
  - <protocol change>
watch_requests_filed: [WR-...]

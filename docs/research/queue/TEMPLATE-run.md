---
schema_version: 1
artifact_id: RUN-YYYYMMDD-NN
artifact_type: run_result
producer: executor
run_id: <invocation id>
created_at: <UTC>
input_refs: [{artifact_id: E-..., file_id: ..., sha256: ...}]   # the frozen spec actually executed
status: completed | failed | partial
---
manifest:
  dataset_id: <frozen id>
  code_version: <commit>
  config_hash: <sha256>
  scorer_version: <id>
  seeds: []
  started: <UTC>
  finished: <UTC>
outputs:
  - {name: raw_results.jsonl, file_id: ..., sha256: ...}
  - {name: per_item_scores.csv, file_id: ..., sha256: ...}
resources: {tokens: 0, wall_clock_s: 0, cost_usd: 0.0}
failures: []
deviations_from_spec: none | <list>

---
schema_version: 1
artifact_id: VER-YYYYMMDD-NN
artifact_type: verdict
producer: hypotheses
run_id: <invocation id>
input_refs: [{artifact_id: RUN-..., file_id: , sha256: }, {artifact_id: REV-..., file_id: , sha256: }]
experiment_id: E-YYYYMMDD-NN | H<n>
verdict: kill | promote | narrow-and-rerun | inconclusive
belief_revisions: [BR-...]
closed: YYYY-MM-DD
effect: "<point estimate> [<clustered interval>]"
cost_delta: "<tokens / latency / people-days>"
deviations_from_card: none | <list>
---
One paragraph of interpretation. No more.

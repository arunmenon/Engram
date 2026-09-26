---
schema_version: 1
artifact_id: PC-YYYYMMDD-NN
artifact_type: proposal
producer: triage
run_id: <invocation id>
idempotency_key: proposal:<claim cluster id>
created_at: <UTC>
input_refs: [{artifact_id: <note id>, file_id: <drive id>, sha256: <digest>}]
claim_cluster: <cluster id; ten posts about one result are one cluster>
source_posts: []
strength: paper-ablated | paper-single-benchmark | repo-pinned | vendor-benchmark | builder-report | opinion
pillar_primary: R1..R8
pillar_secondary: []
tags: {mechanism: [], workload: [], lifecycle_stage: [], evidence: {directness: , control: , independence: , reproducibility: , applicability: }}
beliefs_affected: [B..]
component: <ecosystem component>
decision_it_could_change: <one line>
cost: S | M | L
urgency: none
---
claim:
proposed experiment:
why it matters for us:

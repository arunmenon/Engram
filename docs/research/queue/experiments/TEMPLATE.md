---
schema_version: 1
artifact_id: E-YYYYMMDD-NN
artifact_type: experiment
producer: hypotheses
run_id: <invocation id>
idempotency_key: experiment:<card id>
from_card: PC-YYYYMMDD-NN
owner: T2 | T3 | T4 | T5
track: A | B | C
pillar_primary: R1..R8
beliefs_affected: [B..]
review_required: true | false
budget: {tokens: , cost_usd: , wall_clock_h: }
authorized_executor: <role>
outcomes: {positive: <action>, negative: <action>, inconclusive: <action>}
prior_attempts: []
dataset: <frozen dataset id>
status: queued | running | closed
start: YYYY-MM-DD
verdict_due: YYYY-MM-DD
---
claim:
arms:
metric:
predeclared margin:
sample size and power note:
kill criterion:
what a pass unlocks:
cost (runs, tokens, people-days):

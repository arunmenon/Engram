---
schema_version: 1
artifact_id: POLICY-v1.1
artifact_type: policy
producer: person:arun
run_id: desk-cto-policy-20260928-b
created_at: 2026-09-28T18:04:33Z
input_refs: []
supersedes: POLICY-v1 (kept as policy-v1-superseded.md)
idempotency_key: policy:v1.1
---
# Standing policy for autonomous runs

status: set
set_by: person:arun (CTO, in chat, 2026-09-28: "set it as drafted"; then "B or C" for the review gate)
set_on: 2026-09-28
source: engram-research docs/research/2026-09/research-loop-state.md section 6 (draft 0.1); v1.1 changes only the preconditions line

```yaml
policy_version: 1.1
authorised_executor: executor role on the Engram harness host only
preconditions: person `accepted` decision + spec with execution packet + challenger review `ready` only when a review_required_for trigger below applies (the spec's own review_required flag is advisory), unless the accepted decision carries review_override.waived true (the CTO accepted over the reviewer's objections; the run goes ahead and its verdict is provisional until a review says ready)
permitted_datasets: [public benchmarks listed in discovery-plan P3, seeded fixtures from T1, dogfood corpus tenants named by the CTO]
dogfood_tenants_named: []   # none named yet, so only public benchmarks and seeded fixtures are usable
datasets_forbidden: [anything from the design partner unless explicitly listed, anything containing secrets or personal data]
budget_per_run: {tokens: 2000000, cost_usd: 25, wall_clock_h: 2}
budget_per_week: {cost_usd: 150, runs: 12}
concurrency: 1
environments: [pinned harness commit, frozen evaluate(), no network except model endpoints and the bus]
review_required_for: [cost_usd > 10, beliefs_affected includes a firm or working belief, novelty claim, contradicts an open note, promotion to production shadow]
on_failure: write a runs/ bundle with status failed; never retry silently; never rerun without a new spec revision
never: [executor writes verdicts, executor modifies specs datasets or scorer, any run without a person's accepted]
```

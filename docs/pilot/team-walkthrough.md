# Engram controlled pilot: team walkthrough

**Use one branch: `feature/engram-memory-episodes`.** Foundation, goals, projection fixes, guide and pilot work are consolidated here. See the [three-week lineage audit](branch-lineage-2026-10-16.md); no other branch needs to be merged to use this work.

This pilot checks whether two tenants can send activity into Engram and retrieve the right knowledge with source evidence. Tenant A selects Core, User and Memory. Tenant B selects Core, PDLC and Memory. Both use real Spanner, the authenticated HTTP dispatcher and five ordinary worker loops per tenant. Model-dependent checks use actual `gpt-6-luna` responses.

Read the [visual architecture guide](../guide/engram-architecture.html) first. Pages 1–18 explain the machinery; pages 20–27 explain the pilot. The animations illustrate behavior; they are not live results.

## What a result means

An HTTP success establishes acceptance, not completed projection. The runner waits for applicable outputs, checks exact artifacts and source evidence, queries Engram's public read endpoints, and verifies worker progress and shutdown. A failed expectation remains failed in its original run directory. A later rerun does not rewrite that record.

The entry checkpoint passed 58 checks in [entry06](../review/spanner-compatibility/runs/pilot-1016-entry-06/results.json). It covers attributed User preferences, owner separation, PDLC declared records and model proposals, denied requests, tenant separation and retention of prior records. It is not full pilot acceptance. The broader [spectrum run](../review/spanner-compatibility/runs/pilot-1016-spectrum-01/results.json) has a separate verdict; inspect its `state`, failed checks, per-group results and limitations before sharing a completion claim.

Entry06 is historical evidence, not an exact checkout-only reproduction package: its manifest was captured with uncommitted harness/model-request changes, so its recorded Git revision alone is insufficient to reconstruct it. Do not advertise that commit as an exact replay. Spectrum01 was started from committed code; its source hashes match the pinned revision. The commands below run that improved suite with fresh Event identities, not a byte-identical replay of the earlier provider responses.

## Current continuation and remaining gates

Continuation04 is executing from source commit `797d261`, using the retained targets and the frozen continuation03 journey file. It is **not yet passed**. Continuation03 remains failed: its oracle wrongly required fresh model-proposal identities, despite content-hash reuse with exact new source evidence. Astra accepted the correction; each applicable source still requires persisted output, an exact evidence edge and a successful worker outcome.

The remaining broad stage contains 245 input submissions: incident38, PDLC catalog161, Memory22 across both tenants, User16 and summary8. Earlier planning and connected-query evidence is preserved separately. Submission count is not journey coverage or a completion percentage.

Even a broad-stage pass requires remaining boundary verdicts before full pilot acceptance: small read budgets/truncation; late Episode grouping and preserved history; dependency ordering; actual vector-search contribution; overlapping tenant identities/routing refusals; and documented extension/reproduction. Context selection, Entity ambiguity and automatic cross-session discovery need explicit limitation verdicts. Independent human reproduction cannot be claimed from an agent run. Historical migration, ANN load testing and hierarchy authorization remain separate scope.

## Journeys in the broader stage

| Tenant | Inputs | What the reads must show |
|---|---|---|
| A | Coding experience and learning interest | Declared Python experience; beginning Rust does not become expert proficiency |
| A | Incident versus design-review response preferences | Both attributed preferences with their distinct contexts; context selection remains a separate capability |
| A | Research, travel, work planning, household reminders and response-format conversations | The stated preference meaning and polarity, correct owner, exact source and no invented Memory commitment |
| A | Diagnostic prose containing no personal preference | No extracted preference or skill |
| Both | Explicit stated/inferred Beliefs, confirmation and correction | Current and historical assertions, exact sources and correction links |
| Both | Explicit Goals, completion, abandonment and replacement | Distinct lifecycle outcomes; replacement links and source evidence |
| B | PRD, requirements, versioned HLD/LLD and approval | Revision-specific planning links and approval evidence |
| B | Requirement through code, reviews, tests, release and deployment | Connected trace, failed and successful outcomes kept distinct, unrelated features excluded |
| B | Incident, affected deployment, corrective change and lesson | Exact incident relationships and evidence, no inferred relationship based only on timing |
| B | PDLC event catalog, skipped tests, rollbacks, requests and decisions | Expected typed state and links; duplicate/conflict/rejection behavior; checks at declared intermediate states |

The catalog stage uses normalized HTTP Event inputs, including independently authored GitHub-check payloads. It does not re-prove the native webhook route. It selects semantic/lifecycle/retry cases plus one malformed input per event contract; G07's exhaustive malformed-field matrix remains separate evidence. The full discovery catalog contains additional candidates: it must not be described as executed merely because these families ran.

## Reproduce on the retained assessment targets

Prerequisites must be satisfied before a write run:

- This branch at commit `797d261` for continuation04 (or the later recorded source revision for a later run); Python 3.12+, project dependencies and local embedding-model availability. Verify source hashes before execution as shown below.
- `gcloud` installed and authenticated with permission to impersonate `engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com`.
- Access to project `portiq-mvp`, instance `engram-experiment`, databases `engram-assess-1010a-pdlc` (A) and `engram-g07-target` (B). These are retained targets; do not reset or use unrelated databases.
- `OPENAI_API_KEY` supplied through your local secret mechanism. Never commit it. The account must have access to `gpt-6-luna`.
- No competing workers or operator on these targets. The runner checks their tenant bindings and owner epochs; do not bypass a mismatch by editing control rows.
- Current model-transition binding records, available [here](../review/spanner-compatibility/runs/pilot-1016-model-transition-01/). They pin which historical acceptance epochs are valid. This operator does not grant generic cross-version compatibility.
- Network access to Google Cloud and the model provider. The local dispatcher binds loopback; this is not a deployed remote service for an external cohort.

Check out the pinned revision in a separate clean clone/worktree; do not overwrite local changes. From that repository root:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev,embedding,spanner]'
export PYTHONPATH=src:scripts
```

Verify the execution sources against continuation04's manifest before a reproduction. The manifest itself is evidence added after the source commit, so obtain it from this branch's run directory:

```sh
.venv/bin/python - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('docs/review/spanner-compatibility/runs/pilot-1016-continuation-04/reproduction-manifest.json').read_text())
mismatches = [p for p, expected in manifest['source_sha256'].items()
              if hashlib.sha256(Path(p).read_bytes()).hexdigest() != expected]
assert not mismatches, mismatches
print('Recorded execution source hashes match')
PY
```

Choose a NEW alphanumeric/hyphen run ID and NEW output directories. The following names are examples; replace them if already present. Inspection reads the current baseline, including retained data:

```sh
.venv/bin/python scripts/engram_pilot_model_transition.py inspect \
  --binding-record docs/review/spanner-compatibility/runs/pilot-1016-model-transition-01 \
  --output docs/review/spanner-compatibility/runs/team-pilot-preflight-01

.venv/bin/python scripts/engram_pilot_first_run.py \
  --run-id team-pilot-01 \
  --predecessor docs/review/spanner-compatibility/runs/team-pilot-preflight-01 \
  --output docs/review/spanner-compatibility/runs/team-pilot-01 \
  --spectrum
```

The runner starts the authenticated API and workers, sends requests, collects responses, waits for outputs and stops cooperatively. It retains data. Do not kill it to accelerate shutdown while SDK work is in progress. The model has no artificial call/spend ceiling; normal request timeouts and output lengths still apply. Repeated consolidation can reuse successful text for identical inputs within that worker process, while graph/evidence writes and maintenance still execute.

For an initial smaller reproduction, omit `--spectrum`. That proves only the entry checkpoint. An independent developer should reproduce a journey from each tenant and a denied/cross-tenant probe before asserting independent reproducibility. Agent execution alone does not establish that milestone.

## Inspect and demonstrate the evidence

1. Open `fixtures.json`: these are the inputs and expected outputs frozen before ingestion.
2. Read `results.json`: show admission, exact material records, read responses, applicable worker outcomes and the final verdict. A model call returning is not a semantic pass.
3. Compare the before/after snapshots and derived-refresh evidence. Source Events and old Episode memberships must remain intact. Authorized Summary text/timestamps, Event importance and ordinary read bookkeeping may refresh.
4. Show both a positive answer and an exclusion: Alice versus Bob, Tenant A versus B, a linked PDLC artifact versus an unrelated feature.
5. Inspect actual extraction or summary text beside its source. A stored node and a test count do not establish useful model output.
6. Show retained failures, issue dispositions and limits. A local two-tenant run does not establish hierarchy authorization, production load behavior or external-team onboarding.

## Extend without changing engine code

Freeze the existing spectrum into JSON with a new run ID:

```sh
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from engram_pilot_spectrum import freeze
Path('team-journeys.json').write_text(json.dumps(freeze('team-extension-01'), indent=2))
PY
```

Add a group following an existing compatible group's format: `name`, `tenant` (`a` or `b`), ordered `steps`, `queries`, and `source_kind`. Each step provides a complete Event request, expected HTTP status, exact node properties and directed links, forbidden effects and independently authored source expectations. Queries declare required/forbidden IDs and can name an `after_scenario` checkpoint. Use fresh IDs for every run; do not derive expectations from the returned answer.

Pass that file with `--journey-file team-journeys.json` instead of `--spectrum`. Start from a new inspection baseline. Adding a journey does not authorize new packs, change tenant ownership or make unsupported behavior work. If it requires undocumented repair, record a reproducibility defect rather than editing the graph.

## Deliberate limits

Hierarchy-aware authorization (#49), ANN/load stress (#48), historical data migration, hot pack switching and forced-crash guarantees are separate work. Automatic prose-to-Belief/Goal inference is not claimed; this pilot uses explicit attributed Memory actions. Summary usefulness, ambiguous names, context selection and the complete candidate catalog need their own observed verdicts. Cloud Monitoring export previously returned 403; successful data-path checks do not prove observability export works.

# Engram pilot: team walkthrough and reproduction

The pilot asks whether a tenant's selected packs produce useful, source-backed knowledge through Engram's real write and read paths. Tenant A selects Core + User + Memory; Tenant B selects Core + PDLC + Memory. Core supplies Events and shared evidence, User extracts supported personal information, Memory supports explicit Beliefs/Goals and session Episodes, and PDLC supplies planning and delivery artifacts. Selecting a type does not by itself prove a producer or retrieval behavior works.

## What the engineering checkpoints establish

P01–P07 cover selected planning, code/delivery, incident, User, Memory lifecycle, Episode history and actual-model Summary stories. P08 adds bounded retrieval, trust, exact and wording queries and native Entity vector participation; descriptive Entity discovery without its name remains issue #83. P09 exercises colliding identifiers across tenants and refused requests. P10 proves delayed prerequisites, a real provider rejection followed by recovery, cooperative worker restart and stale-binding rejection. Every checkpoint's actual run, retained failures and limits are in [completion verification](completion-verification.md). Assertion counts are not journey coverage.

P11 passed the small reproduction below at source `d9db077`:69 checks, three created inputs,24 actual-model calls, zero final lag and clean shutdown. Astra accepted its evidence. Its source/import audit matched 183 source hashes and142 imported project modules. P12 assembles the [candidate-by-candidate coverage map](coverage-map.md) and educational guide. Neither a locally launched authenticated dispatcher nor an agent reproduction is an external team deployment or an independent human run.

## Prerequisites before running

Use the one canonical branch, `feature/engram-memory-episodes`. Choose the exact source commit recorded in the reproduction manifest or the reviewed P11 preparation commit. Create a clean detached worktree at that commit; do not overwrite local work. Evidence committed afterwards identifies the source actually executed.

You need:

- Python3.12 and the project dependencies, including `dev`, `embedding` and `spanner` extras. A fresh dependency installation is separate from using an existing environment. For a fresh install, `uv sync --frozen --extra dev --extra embedding --extra spanner` is the intended setup; the recorded P11 run states which environment was actually used.
- `gcloud` authenticated with permission to impersonate `engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com`; that service account needs the existing database permissions on project `portiq-mvp`, instance `engram-experiment`.
- Access to both retained assessment databases: A `engram-assess-1010a-pdlc`, B `engram-g07-target`. Their pack selections come from authenticated bindings, not their names. Do not reset them, change control rows or use another target to evade a failed precondition.
- `OPENAI_API_KEY` supplied through your secret mechanism with access to `gpt-6-luna`; never put it in a command log or repository. No artificial model-call or spend caps are added.
- Network access to Google Cloud, OpenAI and the embedding model, or its existing local cache. Available disk space for retained evidence, and permission to bind a loopback HTTP listener.
- No competing workers or operator on these targets. The runner checks current bindings, epochs and pending work. Stop on a mismatch; do not bypass the check.
- The committed model-transition records and exact P04 retained-negative proof. The runner loads these records; it must not turn whatever failures happen to be present into an allowlist.

This is an authenticated local public-dispatcher run with both databases and all storage ports on real Spanner. The development unevaluated-bundle override remains enabled. Cloud Monitoring export currently lacks permission; this does not validate monitoring export. The native webhook route is outside this run; inputs are normalized HTTP Events.

## Stakeholder demo sequence

1. Open the HTML guide at page20 for the two tenant configurations and the ordinary write/worker/read flow.
2. Use pages22–23 to choose a story. Read its recorded verdict and remaining boundary before opening the input/API details.
3. Open [completion verification](completion-verification.md) for that milestone: compare the frozen input and expected result with the actual public response and source evidence. Failed attempts stay linked beside the accepted checkpoint.
4. At page26, distinguish accepted, processed and acknowledged; then inspect P10 pending-before-restart and successful recovered evidence.
5. At page27, follow the published reproduction below and compare its base/extended fixtures. The extension adds one story without engine changes.
6. Finish with the [coverage map](coverage-map.md): partial catalog stories, semantic discovery #83, human repetition and deployment limits remain visible. Engineering acceptance does not erase them.

This walkthrough is delivered as a versioned artifact. Stakeholder attendance/acceptance and independent human repetition have their own statuses.

## Repeat the small technical proof

Run from the clean worktree root. Set `PILOT_PYTHON` to the absolute Python executable in your prepared environment. The recorded run may reuse a declared existing environment; import auditing below still requires every Engram module to come from this checkout. Set a **new** alphanumeric/hyphen `PILOT_RUN`; output directories and event identities must be fresh.

```sh
export PYTHONPATH=src:scripts
export PILOT_PYTHON=/absolute/path/to/environment/bin/python
export PILOT_RUN=pilot-p11-your-new-id
export PILOT_EVIDENCE=docs/review/spanner-compatibility/runs
"$PILOT_PYTHON" - <<'PY'
import json, os
from pathlib import Path
from engram_pilot_reproduction_fixtures import freeze, with_library_extension
run = os.environ['PILOT_RUN']
base = freeze(run)
extended = with_library_extension(base)
for suffix, data in [('base', base), ('extended', extended)]:
    target = Path('/private/tmp') / (run + '-' + suffix + '.json')
    with target.open('x') as f:
        json.dump(data, f, indent=2)
print('Frozen two original inputs and one additional library story')
PY
"$PILOT_PYTHON" scripts/engram_pilot_model_transition.py inspect \
  --binding-record docs/review/spanner-compatibility/runs/pilot-1016-model-transition-01 \
  --output "$PILOT_EVIDENCE/$PILOT_RUN-preflight"
"$PILOT_PYTHON" - <<'PY'
import asyncio, hashlib, importlib.metadata, json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
from engram_pilot_first_run import execute
root = Path.cwd().resolve()
run = os.environ['PILOT_RUN']
out = root / os.environ['PILOT_EVIDENCE'] / run
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
initial = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
# Only generated preflight evidence may exist; no hidden modified source is allowed.
assert all(line[3:].startswith(os.environ['PILOT_EVIDENCE'] + '/' + run + '-preflight')
           for line in initial.splitlines()), initial
args = SimpleNamespace(run_id=run, predecessor=out.with_name(run+'-preflight'),
    output=out, journey_file=Path('/private/tmp')/(run+'-extended.json'),
    journeys_only=True, spectrum=False,
    service_account='engram-experiment-sa@portiq-mvp.iam.gserviceaccount.com')
try:
    asyncio.run(execute(args))
finally:
    imported = []
    for name, module in sorted(sys.modules.items()):
        if not (name == 'context_graph' or name.startswith(('context_graph.', 'engram_'))):
            continue
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        assert path.is_relative_to(root), (name, str(path))
        relative = str(path.relative_to(root))
        committed = subprocess.check_output(['git', 'show', revision+':'+relative])
        assert path.read_bytes() == committed, relative
        imported.append(dict(module=name, path=relative,
                             sha256=hashlib.sha256(committed).hexdigest()))
    audit = dict(revision=revision, python=sys.version, executable=sys.executable,
        initial_status=initial, imported=imported,
        packages=sorted({(d.metadata['Name'], d.version) for d in importlib.metadata.distributions()}))
    if out.exists():
        (out/'checkout-import-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
PY
```

Do not treat a successful process exit alone as proof. Open `results.json`: all declared checks must pass, final worker lag must be zero, shutdown clean, and exact retained-negative delivery unchanged. Compare each manifest source hash with `git show <recorded-revision>:<path>` in a fresh process. Verify `checkout-import-audit.json` pins project imports to that checkout. Audit the base/extended JSON: the two original inputs must be unchanged and the only added story must be the library Change with its independently declared expected identity, title and source Event. Preserve failed runs as failed; use fresh IDs for a retry.

Run this reconciliation in a fresh Python process after the command above. It audits the recorded run, not a fresh model invocation:

```sh
"$PILOT_PYTHON" - <<'PY'
import hashlib, json, os, subprocess
from pathlib import Path
p = Path(os.environ['PILOT_EVIDENCE']) / os.environ['PILOT_RUN']
r = json.loads((p/'results.json').read_text())
assert r['state'] == 'passed-selected-journeys'
assert all(c['passed'] for c in r['checks'])
assert r['final_worker_lags'] == [0]*10 and not r['shutdown_errors']
assert not r.get('finalization_errors')
assert all(c['state'] == 'returned' and c['model'] == 'gpt-6-luna'
           for c in r['provider_calls'])
created = [q for q in r['requests'] if q['path'] == '/v1/events'
           and q['status'] == 201 and q['output']['status'] == 'created']
assert len(created) == 3
m = json.loads((p/'reproduction-manifest.json').read_text())
for name, expected in m['source_sha256'].items():
    raw = subprocess.check_output(['git','show',m['git_revision']+':'+name])
    assert hashlib.sha256(raw).hexdigest() == expected, name
a = json.loads((p/'checkout-import-audit.json').read_text())
assert a['revision'] == m['git_revision'] and a['imported']
for item in a['imported']:
    raw = subprocess.check_output(['git','show',a['revision']+':'+item['path']])
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['module']
base = json.loads((Path('/private/tmp')/(os.environ['PILOT_RUN']+'-base.json')).read_text())
extended = json.loads((Path('/private/tmp')/(os.environ['PILOT_RUN']+'-extended.json')).read_text())
assert [len(g['steps']) for g in base['groups']] == [1,1]
assert [len(g['steps']) for g in extended['groups']] == [2,1]
for before, after in zip(base['groups'], extended['groups'], strict=True):
    assert before['steps'] == after['steps'][:len(before['steps'])]
assert extended['groups'][0]['steps'][1]['scenario'] == 'json-extension-library'
print('Saved run, source/import hashes and unchanged base fixture reconciled')
PY
```

## What you should see and why

B runs first: its PR input becomes one typed Change, retrieved with accepted source evidence. An additional library PR becomes a distinct Change using the same engine and JSON runner. A then records an explicit Goal and retrieves it through the supported Memory/session read. That A query deliberately also supplies B's already-visible source ID: A must return its own Goal/source and exclude B's source and Change. A negative alone would be weak proof, so B's positive comes first.

All writes use authenticated HTTP `/v1/events`; reads use the public artifact or subgraph APIs. Normal workers consume the ledger and write through Spanner adapters. Direct database snapshots are inspection evidence, not a replacement ingestion or retrieval route. No direct graph insert, manual repair or engine modification is part of fixture extension.

## Boundaries for team review

Owner selection within a tenant is not hierarchy-aware authorization; #49 remains parked. Interleaved tenant requests with concurrent workers are not a simultaneous traffic/load benchmark. Named Entity ANN participation is not a general semantic-discovery or ANN-performance guarantee (#83 and #48). Explicit Memory actions are not automatic inference of Beliefs or Goals from prose. Model outputs need not be byte-identical between runs; identities, sources and declared semantic expectations must hold.

Keep separate verdicts for engineering verification, delivery of the stakeholder walkthrough, and an independent human/team repetition. Retained data and all failures stay available. Historical migration, forced-crash guarantees and external cohort deployment are outside this pilot.

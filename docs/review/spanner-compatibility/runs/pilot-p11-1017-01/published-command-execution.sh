set -eu
export PATH=/Users/arunmenon/google-cloud-sdk/bin:$PATH
export PYTHONPATH=src:scripts
export PILOT_PYTHON=/Users/arunmenon/projects/Engram-foundation-gate/.venv/bin/python
export PILOT_RUN=pilot-p11-1017-01
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

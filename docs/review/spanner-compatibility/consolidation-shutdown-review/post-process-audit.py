"""Read-only independent retention/public-evidence audit after the runner exits."""
import hashlib
import json

from engram_composition_assessment import INSTANCE, PROJECT, ROOT, token
from engram_composition_reuse import TARGET
from engram_experiment_support import durable_json, fingerprint, read_owner
from google.cloud import spanner
from google.oauth2.credentials import Credentials

run = ROOT / 'docs/review/spanner-compatibility/runs/consolidation-shutdown-1014-01'
record = json.loads((run / 'verification.json').read_text())
plan = json.loads((run / 'manifest.json').read_text())['fixtures']
assert record['state'] == 'passed' and not record['shutdown_errors']
assert all(item['passed'] for item in record['checks'])
hashes = json.loads((run / 'source-hashes.json').read_text())
changed = [name for name, digest in hashes.items()
           if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
assert not changed

def normalized(snapshot):
    return {table: sorted(json.dumps(row, sort_keys=True) for row in rows)
            for table, rows in snapshot.items()}

assert normalized(record['final_snapshot']) == normalized(record['retained_snapshot'])
assert record['final_no_late_write_fingerprints'][0] == record['final_no_late_write_fingerprints'][1]
for case in ['SS01', 'SS03', 'SS06', 'SS07']:
    sdk = record['scenarios'][case]['sdk_returned']
    assert sdk['active_calls'] == 0 and sdk['sdk_calls'] == sdk['returned_calls']
    assert sdk['gated_outcome'] == 'committed'
    assert len(sdk['summary_commits']) == 3
    assert {(entry['scope'], entry['summary_id']) for entry in sdk['summary_commits']} == set(plan['summaries'].items())
for case in ['SS04', 'SS05']:
    sdk = record['scenarios'][case]['sdk_returned']
    assert sdk['active_calls'] == 0 and not sdk['summary_commits']
    assert len(sdk['summary_rollbacks']) == 1
assert record['scenarios']['SS06']['subscription_fence_hits'] == 1
assert record['scenarios']['SS02']['stop_seconds'] < 3
assert not record['scenarios']['SS02']['sdk']['entered']

answer = record['requests'][-1]['answer']
assert record['requests'][-1]['route'] == '/v1/query/subgraph'
assert answer['meta']['truncated'] is False
for event in plan['events']:
    node = answer['nodes'][event['event_id']]
    assert node['node_type'] == 'Event'
    assert all(node['provenance'][key] == event[key] for key in ['event_id', 'agent_id', 'session_id', 'trace_id'])
    assert node['attributes']['event_type'] == event['event_type']
    assert node['attributes']['tool_name'] == event['tool_name']
    assert node['attributes']['keywords'] == ['observation', 'input', 'shutdown-tool']
ids = {event['event_id'] for event in plan['events']}
episode, summary = plan['episode'], plan['summaries']['episode']
expected_evidence = {(episode, kind, eid) for eid in ids for kind in ['CONTAINS', 'DERIVED_FROM']}
expected_evidence |= {(summary, 'SUMMARIZES', key) for key in ids | {episode}}
returned_edges = {(edge['source'], edge['edge_type'], edge['target']) for edge in answer['edges']}
assert {edge for edge in returned_edges if edge[0] in {episode, summary}} == expected_evidence
assert returned_edges <= {tuple(edge) for edge in plan['expected_edges']}
assert answer['nodes'][summary]['attributes']['content'] == plan['summary_provider']
export = run / 'previous-export.json'
proof = json.loads(export.with_suffix('.verified.json').read_text())
assert proof['verified'] and hashlib.sha256(export.read_bytes()).hexdigest() == proof['sha256']
retained = json.loads((run / 'retained.json').read_text())
client = spanner.Client(project=PROJECT, credentials=Credentials(token=token(impersonate=True)))
db = client.instance(INSTANCE).database(TARGET.rsplit('/', 1)[1])
owner, fp = read_owner(db), fingerprint(db)
result = dict(database=TARGET, owner=owner, fingerprints=fp,
              owner_matches=owner == retained['owner'], fingerprints_match=fp == retained['fingerprints'],
              source_hashes_checked=len(hashes), changed_sources=changed, assertions=len(record['checks']),
              snapshots_match=True, public_source_and_episode_evidence=True,
              per_cycle_sdk_commits_and_rollbacks=True, verified_export_sha256=proof['sha256'])
durable_json(run / 'post-process-recheck.json', result)
assert result['owner_matches'] and result['fingerprints_match']
print(json.dumps({key: value for key, value in result.items() if key not in ['owner', 'fingerprints']}))

"""Read-only live owner/fence and HTTP response-guard checks; no activation."""
import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
from google.cloud import spanner
from google.oauth2.credentials import Credentials

from engram_spanner_compat import load_credentials
from engram_spanner_tenant_control import durable_json, fingerprint
from engram_spanner_tenant_control_cases import read_owner
from context_graph.adapters.spanner.tenant_control import TenantFence, TenantFenceError, tenant_snapshot
from context_graph.api.tenant_responses import TenantResponseGuard
from context_graph.tenancy import Principal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/review/spanner-compatibility/runs/20261030-cloud-existing-tenant-assessment-01'

async def main():
    OUT.mkdir(parents=True, exist_ok=False)
    evidence = {'scope': 'One existing database; observed owner used as test fixture, not reconstructed runtime configuration. Real fence and HTTP guard; no dispatcher, worker loops or mutations.', 'checks': [], 'status': 'running'}
    durable_json(OUT / 'assessment.json', evidence)
    values = load_credentials(Path('/private/tmp/engram-spanner-token-env'))
    assert values['GOOGLE_CLOUD_PROJECT'] == 'portiq-mvp'
    assert values['SPANNER_INSTANCE_ID'] == 'engram-experiment'
    client = spanner.Client(project='portiq-mvp', credentials=Credentials(token=values['GOOGLE_OAUTH_ACCESS_TOKEN']))
    db = client.instance('engram-experiment').database('engram-compat-target')
    def record(name):
        evidence['checks'].append({'name': name, 'passed': True})
        durable_json(OUT / 'assessment.json', evidence)
    before = None
    try:
        before = await asyncio.to_thread(fingerprint, db)
        owner = await asyncio.to_thread(read_owner, db)
        assert len(owner) == 1 and owner[0][-1] == 'active'
        fence = TenantFence(*owner[0][:-1])
        evidence['owner'] = owner
        evidence['source_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(), ROOT/'src/context_graph/adapters/spanner/tenant_control.py', ROOT/'src/context_graph/api/tenant_responses.py']}
        def check_read(f):
            with tenant_snapshot(db, f) as snapshot:
                assert list(snapshot.execute_sql('SELECT 1')) == [[1]]
        await asyncio.to_thread(check_read, fence)
        record('matching_owner_real_snapshot_allowed')
        variants = {'wrong_tenant': replace(fence, tenant_id='unauthorized-assessment'), 'wrong_binding': replace(fence, binding_id='unauthorized-assessment'), 'stale_epoch': replace(fence, epoch=fence.epoch-1), 'wrong_bundle': replace(fence, bundle_digest='sha256:'+'0'*64), 'wrong_database': replace(fence, database_resource=fence.database_resource+'-wrong')}
        for name, invalid in variants.items():
            try:
                await asyncio.to_thread(check_read, invalid)
            except TenantFenceError:
                record(name+'_read_refused')
            else:
                raise AssertionError(name+' read allowed')
            for operation in ('admission', 'processing'):
                calls = []
                def callback(tx):
                    calls.append(True)  # deliberately no write, even on a broken guard
                try:
                    await asyncio.to_thread(invalid.run, db, callback, operation=operation)
                except TenantFenceError:
                    assert not calls
                    record(name+'_'+operation+'_callback_refused')
                else:
                    raise AssertionError(name+' callback allowed')
        for case, expected in [('valid',200),('no_principal',401),('foreign_principal',403),('stale_before',503),('stale_at_release',503)]:
            checks = []
            handler_calls = []
            async def active_check():
                checks.append(True)
                selected = variants['stale_epoch'] if case=='stale_before' or (case=='stale_at_release' and len(checks)==2) else fence
                await asyncio.to_thread(check_read, selected)
            async def endpoint(scope, receive, send):
                handler_calls.append(True)
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b'private-assessment-marker'})
            guard = TenantResponseGuard(endpoint,child=SimpleNamespace(state=SimpleNamespace(stores=SimpleNamespace(tenant_read_check=active_check))),binding=SimpleNamespace(tenant_id=fence.tenant_id))
            async def fixture(scope, receive, send):
                if case != 'no_principal':
                    scope['engram.principal']=Principal('test-fixture', 'foreign' if case=='foreign_principal' else fence.tenant_id, frozenset({'api'}))
                await guard(scope,receive,send)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=fixture),base_url='http://fixture') as http:
                response = await http.get('/probe')
            assert response.status_code == expected
            if expected != 200:
                assert b'private-assessment-marker' not in response.content
            if case in ('no_principal','foreign_principal','stale_before'):
                assert not handler_calls
            record('http_guard_'+case)
        assert await asyncio.to_thread(read_owner,db) == owner
        record('active_owner_unchanged')
        evidence['status']='passed'
    except BaseException as exc:
        evidence['status']='failed'
        evidence['error_type']=type(exc).__name__
        raise
    finally:
        if before is not None:
            after = await asyncio.to_thread(fingerprint,db)
            evidence['application_rows_unchanged'] = before == after
            evidence['before'] = before
            evidence['after'] = after
            if before != after:
                evidence['status']='failed'
        durable_json(OUT/'assessment.json',evidence)
        print(json.dumps({'status':evidence['status'],'checks':len(evidence['checks']),'rows_unchanged':evidence.get('application_rows_unchanged')}))

if __name__=='__main__':
    asyncio.run(main())

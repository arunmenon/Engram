"""Public dispatcher against two real databases; preserve A, own B fixtures only."""
import asyncio
import json
import secrets
from pathlib import Path
from unittest.mock import patch

import httpx
from google.cloud import spanner
from google.cloud.spanner_v1 import KeySet
from google.oauth2.credentials import Credentials

from context_graph.api.tenants import create_tenant_app
from context_graph.tenancy import TenantBinding, TenantCatalog, CredentialGrant, Principal
from context_graph.settings import Settings
from context_graph.domain.pack_bundle import resolve_bundle
from context_graph.ontology.loader import load_registry
from context_graph.adapters.spanner.tenant_control import TenantFence
from engram_spanner_compat import load_credentials
from engram_spanner_tenant_control import durable_json, fingerprint
from engram_spanner_tenant_control_cases import read_owner

OUT = Path('docs/review/spanner-compatibility/runs/20261030-two-tenant-dispatch-01')

async def main():
    OUT.mkdir(parents=True, exist_ok=False)
    evidence={'scope':'Public factory, real child lifespan/stores/routes, in-process HTTP transport, real Spanner. Optional model/embedding constructors disabled; no worker loops or live activation.', 'status':'running','checks':[]}
    def record(name):
        evidence['checks'].append(name);durable_json(OUT/'result.json',evidence)
    durable_json(OUT/'result.json',evidence)
    values=load_credentials(Path('/private/tmp/engram-spanner-token-env'))
    original=spanner.Client
    def client(*args,**kwargs):
        kwargs['credentials']=Credentials(token=values['GOOGLE_OAUTH_ACCESS_TOKEN'])
        return original(*args,**kwargs)
    sdk=client(project='portiq-mvp')
    a=sdk.instance('engram-experiment').database('engram-compat-target')
    b=sdk.instance('engram-experiment').database('engram-tenant-b-20261030')
    before=await asyncio.to_thread(fingerprint,a)
    owner=await asyncio.to_thread(read_owner,a)
    bundle=resolve_bundle(load_registry(['pdlc'],[Path('/private/tmp/engram-g05-packs')],builtin_packs=[]))
    settings=Settings.model_validate_json(Path('/private/tmp/engram-new-settings.json').read_text())
    ba=TenantBinding('compat-control','compat-control-binding',owner[0][3],'tenant-control-conformance-v1',settings.model_dump_json(),bundle)
    assert list(TenantFence.from_binding(ba)._identity())==owner[0][:-1]
    settings_b=settings.model_copy(deep=True);settings_b.spanner.database=b.database_id
    bb=TenantBinding('tenant-b-20261030','binding-b-20261030',1,'tenant-control-conformance-v1',settings_b.model_dump_json(),bundle)
    assert not any(x['count'] for x in (await asyncio.to_thread(fingerprint,b)).values())
    evidence['bindings']=[{'tenant':x.tenant_id,'database':x.database_resource,'digest':x.bundle_digest,'epoch':x.epoch} for x in (ba,bb)]
    durable_json(OUT/'result.json',evidence)
    await asyncio.to_thread(TenantFence.from_binding(bb).bootstrap,b)
    record('B_empty_database_ownership_bootstrapped')
    def fixture():
        with a.snapshot(multi_use=True) as snap:
            docs=list(snap.execute_sql('SELECT event_id, document FROM Events'))
            nodes=list(snap.execute_sql("SELECT node_id FROM GraphNodes WHERE label = 'Change'"))
        selected=next((eid,dict(doc)) for eid,doc in docs if doc.get('event_type')=='pdlc.change.created')
        return selected,nodes[0][0]
    (event_id,document),seed=await asyncio.to_thread(fixture)
    evidence['owned_B_event_id']=event_id
    durable_json(OUT/'result.json',evidence)
    tokens=[secrets.token_urlsafe(32),secrets.token_urlsafe(32)]
    catalog=TenantCatalog((ba,bb),tuple(CredentialGrant.from_token(Principal('credential-'+str(i),binding.tenant_id,frozenset({'api'}),'demo.query'),tokens[i]) for i,binding in enumerate((ba,bb))))
    gateway=create_tenant_app(catalog)
    started=False
    try:
        with patch('google.cloud.spanner.Client',client), patch('context_graph.adapters.embedding.service.SentenceTransformerEmbedder',return_value=None), patch('context_graph.adapters.llm.client.LLMExtractionClient',return_value=None):
            await gateway._start();started=True
        record('public_factory_two_real_child_lifespans_started')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway),base_url='http://test',timeout=40) as http:
            headers=[{'Authorization':'Bearer '+t} for t in tokens]
            query={'query':'show this change','seed_node_ids':[seed],'max_depth':1,'max_nodes':10,'include_untrusted':True}
            ra,rb=await asyncio.gather(*(http.post('/v1/query/artifacts',headers=h,json=query) for h in headers))
            evidence['retrieval_statuses']=[ra.status_code,rb.status_code]
            assert ra.status_code==rb.status_code==200,(ra.text,rb.text)
            assert seed in ra.json()['nodes'] and seed not in rb.json()['nodes']
            record('A_artifact_visible_only_with_A_credential')
            for h in ({}, {'Authorization':'Bearer invalid'}, {**headers[1],'X-Tenant-ID':ba.tenant_id}):
                r=await http.post('/v1/query/artifacts',headers=h,json=query)
                assert r.status_code==401
            record('missing_invalid_and_cross_tenant_credentials_refused')
            event={k:v for k,v in document.items() if k in ('event_id','event_type','occurred_at','session_id','agent_id','trace_id','payload_ref','payload','parent_event_id','tool_name','schema_version')}
            from datetime import datetime, UTC
            event['occurred_at']=datetime.now(UTC).isoformat();event['agent_id']='dispatcher-test';event['payload']['title']='Tenant B isolated marker'
            r=await http.post('/v1/events',headers=headers[1],json=event)
            evidence['append_status']=r.status_code
            if r.status_code!=201:evidence['append_error']=r.json()
            assert r.status_code==201,r.text
            def get_document(db):
                with db.snapshot() as snap:
                    return dict(list(snap.read('Events',['document'],KeySet(keys=[[event_id]])))[0][0])
            da,db=await asyncio.gather(*(asyncio.to_thread(get_document,d) for d in (a,b)))
            assert db['payload']['title']=='Tenant B isolated marker'
            assert da['payload'].get('title')!='Tenant B isolated marker'
            record('colliding_event_id_appended_to_B_without_changing_A')
            r=await http.post('/v1/events',headers={**headers[1],'X-Tenant-ID':ba.tenant_id},json=event)
            assert r.status_code==401
            record('cross_tenant_write_hint_refused')
            r=await http.get('/v1/context/test?cursor=foreign',headers=headers[1]);assert r.status_code==400
            r=await http.post('/v1/events/import',headers=headers[1],content='');assert r.status_code==503
            r=await http.post('/v1/webhooks/github',headers=headers[1],content='');assert r.status_code==503
            record('unsupported_cursor_import_webhook_paths_refused')
        evidence['status']='passed'
    except BaseException as exc:
        evidence['status']='failed';evidence['error']=type(exc).__name__+': '+str(exc)[:700]
        raise
    finally:
        if started:await gateway._stop()
        def cleanup(tx):tx.delete('Events',KeySet(keys=[[event_id]]))
        await asyncio.to_thread(TenantFence.from_binding(bb).run,b,cleanup,operation='processing')
        evidence['A_rows_unchanged']=before==await asyncio.to_thread(fingerprint,a)
        evidence['A_owner_unchanged']=owner==await asyncio.to_thread(read_owner,a)
        evidence['B_counts_after_cleanup']={k:v['count'] for k,v in (await asyncio.to_thread(fingerprint,b)).items()}
        if not evidence['A_rows_unchanged'] or not evidence['A_owner_unchanged']:evidence['status']='failed'
        durable_json(OUT/'result.json',evidence)
        print(json.dumps({'status':evidence['status'],'checks':len(evidence['checks']),'A_preserved':evidence['A_rows_unchanged']}))

if __name__=='__main__':asyncio.run(main())

"""Remaining bounded compatibility assertions over Engram's real Spanner stores."""
from __future__ import annotations
import asyncio,gzip,json,os
from datetime import UTC,datetime,timedelta
import httpx
from engram_spanner_compat import configure
from engram_spanner_compat_remaining import event,wait_until


async def ingress(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    await run.reset(database,values);configure(values)
    os.environ.update(CG_INGEST_BATCH_MAX_EVENTS='3',CG_INGEST_IMPORT_MAX_EVENTS='6',CG_INGEST_IMPORT_BATCH_SIZE='2')
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://compat') as client:
        stores=app.state.stores
        async def boundaries():
            before=await stores.event_log.stream_length()
            empty=await client.post('/v1/events/batch',json={'events':[]})
            large=await client.post('/v1/events/batch',json={'events':[event('limit') for _ in range(4)]})
            a,b=event('batch-boundary'),event('batch-boundary')
            conflicting={**a,'payload':{'content':'should never replace first payload'}}
            maximum=await client.post('/v1/events/batch',json={'events':[a,conflicting,b]})
            invalid=event('batch-invalid');invalid.pop('agent_id')
            mixed=await client.post('/v1/events/batch',json={'events':[event('batch-mixed'),invalid,event('batch-invalid-id',event_id='not-a-uuid')]})
            docs=await stores.event_log.get_documents([a['event_id'],b['event_id']])
            receipt={'configured_max_events':3,'empty_status':empty.status_code,'over_max_status':large.status_code,'max_status':maximum.status_code,'max':maximum.json(),'mixed':mixed.json(),'first_payload_preserved':docs[0]['payload']==a['payload'],'ledger_delta':await stores.event_log.stream_length()-before}
            (run.directory/'batch-boundaries.json').write_text(json.dumps(receipt,indent=2))
            assert empty.status_code==large.status_code==422 and maximum.status_code==mixed.status_code==201,receipt
            assert [r['status'] for r in maximum.json()['results']]==['created','duplicate','created'],receipt
            assert maximum.json()['accepted']==3 and mixed.json()['accepted']==1 and mixed.json()['rejected']==2,receipt
            assert [r['index'] for r in mixed.json()['errors']]==[1,2] and receipt['ledger_delta']==3 and receipt['first_payload_preserved'],receipt
            return receipt
        await run.check('configured_batch_empty_max_over_max_mixed_indices_and_conflicts',['ING-02'],boundaries)
        async def pack_refusal():
            row=event('bad-pack-batch',event_type='pdlc.change.created',payload={'number':7})
            response=await client.post('/v1/events/batch',json={'events':[row]})
            receipt={'status':response.status_code,'response':response.json(),'document':(await stores.event_log.get_documents([row['event_id']]))[0]}
            (run.directory/'batch-invalid-pack-payload.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==422 and receipt['document'] is None,'batch accepts pack payload without required repo (#4)'
            return receipt
        await run.check('batch_rejects_missing_pack_key_before_append',['ING-02'],pack_refusal)
        async def import_order():
            base=datetime.now(UTC)-timedelta(days=100)
            rows=[event('import-order',occurred_at=(base+timedelta(seconds=i)).isoformat()) for i in (30,10,10,20)]
            lines=[json.dumps(rows[0]),'not-json',json.dumps(rows[1]),json.dumps(rows[2]),json.dumps(rows[3]),json.dumps(rows[0])]
            response=await client.post('/v1/events/import',content='\n'.join(lines)+'\n',headers={'content-type':'application/x-ndjson'})
            results=[json.loads(line) for line in response.text.splitlines()];summary=results[-1]['summary']
            valid=[r for r in results[:-1] if r['status']!='rejected'];doc=await stores.event_log.get_documents([r['event_id'] for r in rows])
            empty=await client.post('/v1/events/import',content='\n \n')
            before=await stores.event_log.stream_length()
            over=await client.post('/v1/events/import',content='\n'.join(json.dumps(event('over-import')) for _ in range(7)))
            receipt={'configured_max':6,'response_status':response.status_code,'outcomes':results,'empty_status':empty.status_code,'over_max_status':over.status_code,'over_limit_wrote_rows':await stores.event_log.stream_length()-before}
            (run.directory/'import-order-malformed-limits.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and summary['created']==4 and summary['duplicate']==summary['rejected']==1,receipt
            assert [r['index'] for r in valid]==[2,3,4,0,5],receipt
            assert valid[-1]['global_position']==valid[-2]['global_position'] and all(doc),receipt
            assert empty.status_code==422 and over.status_code==413 and not receipt['over_limit_wrote_rows'],receipt
            return receipt
        await run.check('historical_import_malformed_line_exact_limit_and_occurrence_ties',['ING-05'],import_order)
        async def import_partial():
            rows=[event('import-partial') for _ in range(5)];original=stores.event_log.append_batch_outcomes;calls=0
            async def fault(*a,**kw):
                nonlocal calls
                calls+=1
                if calls==2:raise RuntimeError('synthetic second import store-call failure')
                return await original(*a,**kw)
            stores.event_log.append_batch_outcomes=fault
            body='\n'.join(json.dumps(row) for row in rows)+'\n'
            try:first=await client.post('/v1/events/import?order=input',content=body)
            finally:stores.event_log.append_batch_outcomes=original
            retry=await client.post('/v1/events/import?order=input',content=body)
            first_lines=[json.loads(line) for line in first.text.splitlines()];retry_lines=[json.loads(line) for line in retry.text.splitlines()]
            receipt={'first_status':first.status_code,'first':first_lines,'retry_status':retry.status_code,'retry':retry_lines,'store_calls_before_stop':calls,'fault':'synthetic second store call; first real Spanner commit retained'}
            (run.directory/'import-partial-error-retry.json').write_text(json.dumps(receipt,indent=2))
            assert first.status_code==retry.status_code==200 and calls==2,receipt
            assert [r['status'] for r in first_lines[:-1]]==['created','created','failed','failed','failed'],receipt
            assert [r['index'] for r in first_lines[:-1]]==list(range(5)),receipt
            assert [r['status'] for r in retry_lines[:-1]]==['duplicate','duplicate','created','created','created'],receipt
            assert all(await stores.event_log.get_documents([r['event_id'] for r in rows])),receipt
            return receipt
        await run.check('streamed_import_committed_prefix_failure_stops_and_safe_retry',['ING-05'],import_partial)
        async def import_input():
            base=datetime.now(UTC)-timedelta(days=2)
            rows=[event('input-order',occurred_at=(base+timedelta(seconds=i)).isoformat()) for i in (30,10,20)]
            response=await client.post('/v1/events/import?order=input',content='\n'.join(json.dumps(r) for r in rows))
            lines=[json.loads(line) for line in response.text.splitlines()]
            receipt={'status':response.status_code,'lines':lines}
            (run.directory/'import-explicit-input-order.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and [r['index'] for r in lines[:-1]]==[0,1,2],receipt
            assert [r['global_position'] for r in lines[:-1]]==sorted(r['global_position'] for r in lines[:-1]),receipt
            return receipt
        await run.check('explicit_input_import_preserves_input_not_occurrence_order',['ING-05'],import_input)
        async def bytes_limits():
            original=app.state.settings.ingest.max_body_bytes;app.state.settings.ingest.max_body_bytes=2000
            row=event('body-size',payload={'content':'a'*3000});body=json.dumps(row).encode();before=await stores.event_log.stream_length()
            try:
                plain=await client.post('/v1/events',content=body)
                zipped=await client.post('/v1/events',content=gzip.compress(body),headers={'content-encoding':'gzip'})
            finally:app.state.settings.ingest.max_body_bytes=original
            receipt={'plain':plain.status_code,'compressed':zipped.status_code,'decoded_bytes':len(body),'compressed_bytes':len(gzip.compress(body)),'ledger_delta':await stores.event_log.stream_length()-before}
            (run.directory/'encoded-decoded-body-limits.json').write_text(json.dumps(receipt,indent=2))
            assert plain.status_code==zipped.status_code==413 and not receipt['ledger_delta'],receipt
            return receipt
        await run.check('encoded_and_decoded_payload_size_limits_prevent_append',['OPS-02','ING-03'],bytes_limits)


async def context_cases(run,database,values,credentials):
    import time
    from context_graph.api.app import create_app,lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();rows={};base=datetime.now(UTC)-timedelta(minutes=5)
        for session,times in [('context-ties',[0]*5),('context-distinct',list(range(5)))]:
            rows[session]=[event(session,occurred_at=(base+timedelta(seconds=offset)).isoformat()) for offset in times]
            response=await client.post('/v1/events/batch',json={'events':rows[session]});assert response.status_code==201,response.text
        worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'context-cases'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await worker.ensure_group();task=asyncio.create_task(worker.run())
        try:
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,60)
        finally:worker.stop();await asyncio.wait_for(task,20)
        for session in rows:
            async def pages(session=session):
                ids=[r['event_id'] for r in rows[session]];refs=[NodeRef('Event',key,'event_id') for key in ids]
                before=await stores.graph.get_nodes(refs);seen=[];responses=[];cursor=None;repeated=False
                for _ in range(6):
                    params={'max_nodes':2}
                    if cursor:params['cursor']=cursor
                    response=await client.get('/v1/context/'+session,params=params);assert response.status_code==200,response.text
                    body=response.json();responses.append(body);page=list(body['nodes'])
                    if set(page)&set(seen):repeated=True;break
                    seen.extend(page)
                    if not body['pagination']['has_more']:break
                    next_cursor=body['pagination']['cursor']
                    if next_cursor==cursor:repeated=True;break
                    cursor=next_cursor
                after=await stores.graph.get_nodes(refs)
                missing=await client.get('/v1/context/context-does-not-exist')
                receipt={'session':session,'pages':responses,'seen':seen,'expected_ids':ids,'repeated':repeated,'before_counts':{ref.key:p.get('access_count') for ref,p in before.items()},'after_counts':{ref.key:p.get('access_count') for ref,p in after.items()},'missing_response':missing.json()}
                (run.directory/(session+'-pages.json')).write_text(json.dumps(receipt,indent=2))
                assert not repeated and set(seen)==set(ids) and len(seen)==5,'context cursor duplicates/omits events across occurrence times'
                assert all(after[ref]['access_count']==before[ref]['access_count']+1 for ref in refs),receipt
                assert missing.status_code==200 and not missing.json()['nodes'],receipt
                return receipt
            await run.check(session+'_pagination_access_and_missing',['MEM-01','MEM-05'],pages)
        async def budget():
            engine=app.state.retrieval;original_timeout=engine._query_timeout_s;engine._query_timeout_s=0.03
            original_query=stores.graph._query;calls=0
            async def delayed(*args,**kwargs):
                nonlocal calls
                calls+=1;await asyncio.sleep(0.12)
                return await original_query(*args,**kwargs)
            stores.graph._query=delayed;started=time.monotonic()
            try:response=await asyncio.wait_for(client.get('/v1/context/context-ties',params={'max_nodes':2}),3)
            finally:stores.graph._query=original_query;engine._query_timeout_s=original_timeout
            elapsed=time.monotonic()-started
            receipt={'configured_query_timeout_seconds':0.03,'synthetic_delay_per_actual_SQL_call':0.12,'calls':calls,'elapsed':elapsed,'HTTP_status':response.status_code,'response':response.json(),'scope':'synthetic read delay around unchanged real Spanner SQL; no cloud outage claimed'}
            (run.directory/'context-query-budget.json').write_text(json.dumps(receipt,indent=2))
            assert elapsed<0.12,'context forwards timeout_s to a port that ignores it; native reads exceed the budget'
            return receipt
        await run.check('context_enforces_graph_read_time_budget',['MEM-01','MEM-05'],budget)


async def consolidation_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.consolidation import ConsolidationConsumer
    from engram_spanner_compat_remaining import graph_counts
    await run.reset(database,values);configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();settings.decay.reflection_threshold=20
        base=datetime.now(UTC)-timedelta(hours=2)
        rows=[event('cons-completion',occurred_at=(base+timedelta(minutes=n)).isoformat()) for n in (0,1,40,41)]
        for row in rows[:3]:assert (await client.post('/v1/events',json=row)).status_code==201
        worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'cons-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await worker.ensure_group();task=asyncio.create_task(worker.run())
        async def drain():
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,60)
        try:
            await drain()
            cons=ConsolidationConsumer(stores.subscription(settings.consumer.group_consolidation,'cons-cases'),stores.event_log,stores.graph,settings)
            async def threshold_repeats():
                await cons._run_consolidation_cycle_guarded(source='below-threshold')
                below=await graph_counts(database)
                assert below['nodes'].get('Summary',0)==0,below
                assert (await client.post('/v1/events',json=rows[3])).status_code==201
                await drain()
                await cons.process_message('manual-fixture',{'message_type':'consolidation_trigger'})
                first=await graph_counts(database)
                await cons._run_consolidation_cycle_guarded(source='repeat')
                second=await graph_counts(database)
                evidence=[e for e in second['edges'] if e[1]=='SUMMARIZES']
                receipt={'below':below,'first':first,'second':second,'summary_evidence_edges':evidence,'trigger':'actual public process_message; timer already separately covered'}
                (run.directory/'consolidation-threshold-repeat.json').write_text(json.dumps(receipt,indent=2))
                assert first['nodes'].get('Summary')==second['nodes'].get('Summary')==4,receipt
                assert len(evidence)==12 and set(e[2] for e in evidence)==set(r['event_id'] for r in rows),receipt
                return receipt
            await run.check('consolidation_threshold_manual_trigger_episodes_repeated_ids_and_evidence',['CONS-01'],threshold_repeats)
            async def overlap():
                original=cons._run_consolidation_cycle;entered=asyncio.Event();release=asyncio.Event();calls=0
                async def gated():
                    nonlocal calls
                    calls+=1;entered.set();await release.wait();await original()
                cons._run_consolidation_cycle=gated
                task=asyncio.create_task(cons._run_consolidation_cycle_guarded(source='overlap-first'))
                try:
                    await asyncio.wait_for(entered.wait(),5)
                    await asyncio.wait_for(cons._run_consolidation_cycle_guarded(source='overlap-second'),1)
                finally:
                    release.set();await asyncio.wait_for(task,60);cons._run_consolidation_cycle=original
                receipt={'actual_cycles':calls,'locked_after':cons._consolidation_lock.locked(),'scope':'one worker lock; no distributed lock guarantee'}
                assert calls==1 and not receipt['locked_after'],receipt
                return receipt
            await run.check('consolidation_same_worker_overlap_guard',['CONS-01'],overlap)
            async def provider_failure():
                class Provider:
                    calls=0
                    async def generate_text(self,prompt):
                        self.calls+=1
                        raise RuntimeError('synthetic summarization provider outage')
                provider=Provider();cons._llm_client=provider;writes=[];original=stores.graph.write_summary_with_edges
                async def observe(**kwargs):
                    writes.append(kwargs['summary_id']);return await original(**kwargs)
                stores.graph.write_summary_with_edges=observe
                try:
                    await cons._run_consolidation_cycle_guarded(source='provider-failure')
                    failed_writes=list(writes);unlocked=not cons._consolidation_lock.locked()
                    cons._llm_client=None
                    await cons._run_consolidation_cycle_guarded(source='next-cycle-recovery')
                finally:stores.graph.write_summary_with_edges=original;cons._llm_client=None
                receipt={'provider_calls':provider.calls,'writes_during_failure':failed_writes,'writes_next_cycle':writes,'lock_released_after_failure':unlocked,'scope':'failure is logged, no provider fallback; later actual cycle recovers; no new delivery-retry guarantee'}
                (run.directory/'consolidation-provider-failure-recovery.json').write_text(json.dumps(receipt,indent=2))
                assert provider.calls==1 and not failed_writes and unlocked and len(writes)==4,receipt
                return receipt
            await run.check('consolidation_provider_failure_releases_lock_and_next_cycle_recovers',['CONS-01'],provider_failure)
        finally:worker.stop();await asyncio.wait_for(task,20)


async def evaluation_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.ontology.versioning import EvalPending,record_state,STATE_REF
    await run.reset(database,values);configure(values,'pdlc,crm');app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://compat') as client:
        stores=app.state.stores;registry=app.state.ontology
        intent=next(name for name,item in registry.intents.items() if item.pack=='pdlc')
        async def cache_and_gate():
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':['pdlc']})
            cache=EvalPending(stores.graph,registry,0.08);app.state.eval_pending=cache
            pending=await cache.packs();refused=await client.post('/v1/query/artifacts',json={'query':'compat missing artifact','intent':intent})
            auto=await client.post('/v1/query/artifacts',json={'query':'compat missing artifact'})
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':[]})
            cache._ttl_s=60
            stale=await cache.packs()
            cache._ttl_s=0.08;await asyncio.sleep(0.1)
            clear=await cache.packs();admitted=await client.post('/v1/query/artifacts',json={'query':'compat missing artifact','intent':intent})
            original=stores.graph.get_nodes;fault_calls=0
            async def fault(refs,*a,**kw):
                nonlocal fault_calls
                if STATE_REF in refs:
                    fault_calls+=1;raise RuntimeError('synthetic ontology state read failure')
                return await original(refs,*a,**kw)
            stores.graph.get_nodes=fault
            initial_error=None
            try:
                cache._ttl_s=0
                kept=await cache.packs()
                try:await EvalPending(stores.graph,registry,0).packs()
                except RuntimeError as exc:initial_error=type(exc).__name__
            finally:stores.graph.get_nodes=original
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':['pdlc']})
            recovered=await cache.packs()
            receipt={'intent':intent,'pending':sorted(pending),'explicit_pending_status':refused.status_code,'auto_status':auto.status_code,'auto_pending_metadata':auto.json().get('meta',{}).get('eval_pending'),'stale_within_TTL':sorted(stale),'clear_after_TTL':sorted(clear),'explicit_clear_status':admitted.status_code,'read_error_retains_last':sorted(kept),'first_read_error':initial_error,'synthetic_fault_calls':fault_calls,'recovered_pending':sorted(recovered),'scope':'fixture state transitions, real Spanner reads/writes; successful actual evaluation separately recorded'}
            (run.directory/'evaluation-cache-and-admission.json').write_text(json.dumps(receipt,indent=2))
            assert pending==stale==recovered==frozenset({'pdlc'}) and not clear and not kept,receipt
            assert refused.status_code==409 and auto.status_code==admitted.status_code==200 and initial_error=='RuntimeError',receipt
            assert 'pdlc' in receipt['auto_pending_metadata'],receipt
            return receipt
        await run.check('evaluation_pending_explicit409_auto_metadata_TTL_read_error_and_recovery',['ART-05','ONT-01'],cache_and_gate)
        async def composition():
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':['pdlc','crm']})
            app.state.eval_pending=EvalPending(stores.graph,registry,0)
            pending_responses={};admitted_responses={}
            for pack in ('pdlc','crm'):
                pack_intent=next(name for name,item in registry.intents.items() if item.pack==pack)
                response=await client.post('/v1/query/artifacts',json={'query':'compat missing artifact','intent':pack_intent})
                pending_responses[pack]={'intent':pack_intent,'status':response.status_code}
            status=await client.get('/v1/ontology');body=status.json()
            unknown=await client.post('/v1/query/artifacts',json={'query':'compat','intent':'not-an-intent'})
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':[]})
            for pack,item in pending_responses.items():
                response=await client.post('/v1/query/artifacts',json={'query':'compat missing artifact','intent':item['intent']})
                admitted_responses[pack]=response.status_code
            receipt={'pending_intents':pending_responses,'cleared_intents':admitted_responses,'unknown_intent_status':unknown.status_code,'ontology_status':body,'scope':'loaded combined pack namespaces and weight definitions; fixture pending transitions; quality covered by independent competency fixtures'}
            (run.directory/'combined-pack-gate-and-status.json').write_text(json.dumps(receipt,indent=2))
            assert all(x['status']==409 for x in pending_responses.values()) and all(x==200 for x in admitted_responses.values()),receipt
            assert unknown.status_code==422 and status.status_code==200,receipt
            for name,item in registry.intents.items():
                assert body['intent_definitions'][name]['weights']==dict(item.weights) and body['intent_definitions'][name]['pack']==item.pack,receipt
            return {'pending_intents':pending_responses,'cleared_intents':admitted_responses,'status_route':status.status_code,'weight_and_namespace_definitions':len(registry.intents)}
        await run.check('combined_PDLC_CRM_pending_admission_namespace_weights_and_status',['ART-05','ONT-01'],composition)
        async def record_modes():
            from pathlib import Path
            from context_graph.ontology.__main__ import evaluate_graph
            from context_graph.ontology.versioning import read_state
            from engram_spanner_compat import ROOT
            empty=run.directory/'empty-eval-sets';empty.mkdir()
            await record_state(stores.graph,registry,applied='compat-fixture',extra={'eval_pending':[]})
            before=await read_state(stores.graph)
            missing=await evaluate_graph(app.state.settings,stores.graph,registry,[empty],record=False)
            after_no_record=await read_state(stores.graph)
            failing=await evaluate_graph(app.state.settings,stores.graph,registry,[ROOT/'tests/fixtures/ontology',ROOT/'tests/fixtures/packs/crm'],record=True)
            after_record=await read_state(stores.graph)
            receipt={'missing_sets':[r.as_dict() for r in missing],'failing_empty_graph_sets':[r.as_dict() for r in failing],'no_record_preserves_state':before.properties==after_no_record.properties,'recorded_pending':after_record.properties.get('eval_pending'),'scope':'real empty graph deliberately fails existing competency sets; successful evaluate --record gate separately tested on populated PDLC/CRM fixtures'}
            (run.directory/'evaluation-missing-failing-record-modes.json').write_text(json.dumps(receipt,indent=2))
            assert len(missing)==2 and all(r.problem and not r.passed for r in missing),receipt
            assert len(failing)==2 and all(not r.passed for r in failing),receipt
            assert receipt['no_record_preserves_state'] and set(receipt['recorded_pending'])=={'pdlc','crm'},receipt
            return receipt
        await run.check('missing_failing_evaluation_sets_record_and_no_record_modes',['ONT-01'],record_modes,timeout_seconds=180)



async def extraction_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.settings import Settings
    from context_graph.adapters.llm.client import LLMExtractionClient
    from context_graph.worker.extraction import ExtractionConsumer
    from engram_spanner_compat_remaining import graph_counts
    await run.reset(database,values);configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();llm=LLMExtractionClient(max_retries=0)
        output={'mode':'invalid-json'};calls=[]
        async def model(prompt):
            calls.append({'mode':output['mode'],'prompt_chars':len(prompt)})
            if output['mode']=='outage':raise RuntimeError('synthetic extraction provider outage')
            if output['mode']=='invalid-json':return 'not-json'
            if output['mode']=='invalid-items':return json.dumps({'entities':[{'name':None,'entity_type':{},'confidence':'bad'}],'preferences':[{'category':None}],'persona':None})
            if output['mode']=='valid-entity':return json.dumps({'entities':[{'name':output['entity_name'],'entity_type':'tool','confidence':0.9,'source_quote':output['entity_name']}]})
            return '{}'
        llm._call_llm=model
        worker=ExtractionConsumer(stores.subscription(settings.consumer.group_extraction,'extract-boundaries'),stores.event_log,llm,settings,graph_store=stores.graph,user_store=stores.graph)
        await worker.ensure_group();task=asyncio.create_task(worker.run());rows=[]
        async def drain():
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,60)
        try:
            for mode in ('invalid-json','invalid-items','outage'):
                async def case(mode=mode):
                    output['mode']=mode;session='extract-'+mode;before_calls=len(calls)
                    for kind in ('observation.input','system.session_end'):
                        row=event(session,event_type=kind);rows.append(row)
                        assert (await client.post('/v1/events',json=row)).status_code==201
                    await drain();counts=await graph_counts(database)
                    receipt={'mode':mode,'provider_calls':len(calls)-before_calls,'counts':counts,'pending':await worker._subscription.delivery_counts(100),'scope':'actual LLMExtractionClient validation/fallback, scripted provider only; rejected output ACKs by existing contract'}
                    (run.directory/('extraction-'+mode+'.json')).write_text(json.dumps(receipt,indent=2))
                    assert receipt['provider_calls']==1 and not counts['nodes'] and not receipt['pending'],receipt
                    return receipt
                await run.check('extraction_'+mode+'_no_invalid_writes_and_ACK',['EXT-01'],case)
            async def mid():
                output['mode']='empty-valid';worker._mid_session_interval=2;before_calls=len(calls)
                for _ in range(2):
                    row=event('extract-mid');rows.append(row)
                    assert (await client.post('/v1/events',json=row)).status_code==201
                    await drain()
                receipt={'provider_calls':len(calls)-before_calls,'turn_count':worker._session_turn_counts.get('extract-mid'),'ledger_documents':len([x for x in await stores.event_log.get_documents([r['event_id'] for r in rows]) if x]),'pending':await worker._subscription.delivery_counts(100)}
                assert receipt['provider_calls']==1 and receipt['turn_count']==2 and receipt['ledger_documents']==8 and not receipt['pending'],receipt
                return receipt
            await run.check('extraction_mid_session_interval_collects_real_ledger_docs',['EXT-01'],mid)
            async def resolution():
                from context_graph.ports.pack_graph import NodeRef,NodeWrite
                from context_graph.worker.projection import ProjectionConsumer
                from context_graph.ontology.runtime import configured_projector
                # Pause extraction so the explicit dependency is established before reads.
                worker.stop();await asyncio.wait_for(task,20)
                proj=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'entity-resolution-proj'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
                await proj.ensure_group();proj_task=asyncio.create_task(proj.run())
                source_ids=[]
                try:
                    for name in ('github','gh'):
                        session='resolution-'+name
                        local=[event(session,payload={'content':'I use '+name+' for reviews'}),event(session,event_type='system.session_end',payload={'content':'I use '+name+' for reviews'})]
                        for row in local:
                            assert (await client.post('/v1/events',json=row)).status_code==201
                            source_ids.append(row['event_id'])
                        async def ready():return not await proj._subscription.lag() and not await proj._subscription.delivery_counts(100)
                        await wait_until(ready,60)
                        output.update(mode='valid-entity',entity_name=name)
                        await worker.process_message('direct-stored-end',{'event_id':local[-1]['event_id']})
                    counts=await graph_counts(database);entities=await stores.graph.get_entities(limit=20)
                    refs=[e for e in counts['edges'] if e[1]=='REFERENCES']
                    assert len(entities)==1 and entities[0]['name']=='github' and set(e[0] for e in refs)==set(source_ids),{'entities':entities,'references':refs}
                    canonical=NodeRef('Entity','entity:github','entity_id');members=[NodeRef('Entity','entity:github-alias-'+str(i),'entity_id') for i in range(3)]
                    await stores.graph.upsert_nodes([NodeWrite(ref,{'name':ref.key,'entity_type':'tool'}) for ref in members])
                    ids=[canonical.key]+[ref.key for ref in members]
                    await stores.graph.consolidate_entity_cluster(ids,canonical.key)
                    await stores.graph.consolidate_entity_cluster(ids,canonical.key)
                    await stores.graph.consolidate_entity_cluster([],canonical.key)
                    final=await graph_counts(database);same=[e for e in final['edges'] if e[1]=='SAME_AS']
                    receipt={'resolved_entities_before_cluster':entities,'source_reference_edges':refs,'cluster_members':ids,'cluster_edges':same,'scope':'actual extraction exact/alias MERGE plus native cluster public operation; repeated cluster writes idempotent; semantic model resolution not claimed'}
                    (run.directory/'entity-resolution-and-cluster.json').write_text(json.dumps(receipt,indent=2))
                    assert len(same)==3 and all(e[2]==canonical.key for e in same) and not any(e[0]==e[2] for e in same),receipt
                    return receipt
                finally:proj.stop();await asyncio.wait_for(proj_task,20)
            await run.check('validated_entity_alias_resolution_references_and_repeated_cluster_writes',['EXT-01','CONS-02'],resolution)

        finally:worker.stop();await asyncio.wait_for(task,20)


async def workload_cases(run,database,values,credentials):
    import time
    from context_graph.api.app import create_app,lifespan
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values);first=create_app();second=create_app()
    async with lifespan(first),lifespan(second),httpx.AsyncClient(transport=httpx.ASGITransport(app=first),base_url='http://first') as a,httpx.AsyncClient(transport=httpx.ASGITransport(app=second),base_url='http://second') as b:
        settings=Settings();stores=first.state.stores;rows=[event('load-'+str(i%3)) for i in range(24)]
        worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'load-worker'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await worker.ensure_group();task=asyncio.create_task(worker.run())
        async def measured():
            started=time.monotonic();r=await a.post('/v1/events/batch',json={'events':rows});assert r.status_code==201,r.text
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,90);drain=time.monotonic()-started
            samples=[]
            async def get(client,replica,session,phase):
                start=time.monotonic();response=await client.get('/v1/context/'+session,params={'max_nodes':10});elapsed=time.monotonic()-start
                assert response.status_code==200,response.text
                expected={row['event_id'] for row in rows if row['session_id']==session};body=response.json()
                assert set(body['nodes'])==expected and not body['pagination']['has_more'],body
                samples.append({'API_instance':replica,'session':session,'phase':phase,'seconds':elapsed,'status':response.status_code,'nodes':len(body['nodes'])})
            await asyncio.gather(get(a,'a','load-0','first_context_call'),get(b,'b','load-1','first_context_call'))
            for n in range(12):await asyncio.gather(get(a,'a','load-'+str(n%3),'warm'),get(b,'b','load-'+str((n+1)%3),'warm'))
            def quantile(xs,q):
                xs=sorted(xs);index=(len(xs)-1)*q;lo=int(index);hi=min(lo+1,len(xs)-1);return xs[lo]+(xs[hi]-xs[lo])*(index-lo)
            warm=[row['seconds'] for row in samples if row['phase']=='warm']
            receipt={'events':24,'sessions':3,'API_instances':2,'same_OS_process':True,'max_concurrent_requests':2,'batch_to_projection_drain_seconds':drain,'warm_context_seconds':{f'p{q}':quantile(warm,q/100) for q in (50,95,99)},'samples':samples,'projection_lag':await worker._subscription.lag(),'projection_pending':await worker._subscription.delivery_counts(100),'scope':'actual independent SDK-backed app lifespans, no network proxy; first call vs warm, not a restarted server cold-start benchmark; no SLO claimed'}
            (run.directory/'bounded-workload-latencies.json').write_text(json.dumps(receipt,indent=2))
            assert len(samples)==26 and not receipt['projection_lag'] and not receipt['projection_pending'],receipt
            return receipt
        try:await run.check('two_API_instances_bounded_context_workload_and_backlog_drain',['OPS-05'],measured,timeout_seconds=180)
        finally:worker.stop();await asyncio.wait_for(task,20)


async def pack_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.domain.pack_extraction import extraction_profiles
    from context_graph.worker.pack_extraction import PackExtractionConsumer,ModelUnavailableError
    from engram_spanner_compat_remaining import graph_counts
    await run.reset(database,values);configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();projector=configured_projector(settings.ontology)
        profiles=extraction_profiles(projector.registry,max_nodes=10,max_links=10,max_text_chars=2000)
        answer={'value':'[]'};calls=0
        class Model:
            async def generate_text(self,prompt):
                nonlocal calls
                calls+=1;return answer['value']
        worker=PackExtractionConsumer(stores.subscription(settings.consumer.group_pack_extraction,'pack-output-boundaries'),stores.event_log,stores.graph,profiles,projector,Model(),settings)
        await worker.ensure_group();task=asyncio.create_task(worker.run())
        async def drain():
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,60)
        try:
            for name,text in [('list-answer','[]'),('nonlist-nodes','{"nodes":{},"links":"bad"}'),('invalid-fields',json.dumps({'nodes':[{'ref':'n1','type':'Decision','statement':{'invalid':'object'},'confidence':0.8},{'ref':'n2','type':'Decision','statement':'bad confidence','confidence':'high'},{'ref':'n3','type':'Change','repo':'x','number':7,'confidence':0.9},{'ref':'n4','type':'Decision','confidence':0.8}],'links':[{'type':'SAME_AS','from':'n1','to':'n1','confidence':0.9}]}))]:
                async def invalid(name=name,text=text):
                    answer['value']=text;start=calls;row=event('pack-invalid-'+name,payload={'content':'Evaluate invalid proposal '+name})
                    assert (await client.post('/v1/events',json=row)).status_code==201
                    await drain();counts=await graph_counts(database)
                    receipt={'answer_shape':name,'model_calls':calls-start,'counts':counts,'pending':await worker._subscription.delivery_counts(100)}
                    assert receipt['model_calls']==1 and not counts['nodes'] and not counts['edges'] and not receipt['pending'],receipt
                    return receipt
                await run.check('pack_'+name+'_refused_without_writes_ACK',['PEXT-01'],invalid)
            async def no_answer():
                worker.stop();await asyncio.wait_for(task,20)
                row=event('pack-no-answer',payload={'content':'Proposal provider returns no answer'})
                assert (await client.post('/v1/events',json=row)).status_code==201
                answer['value']=None;error=None;before=await graph_counts(database)
                try:await worker.process_message('direct-no-answer',{'event_id':row['event_id']})
                except ModelUnavailableError as exc:error=type(exc).__name__
                receipt={'error_type':error,'before':before,'graph':await graph_counts(database),'scope':'actual stored event public process_message rejects no-answer; full delivery live retry remains failed #14'}
                assert error=='ModelUnavailableError' and receipt['graph']==before,receipt
                return receipt
            await run.check('pack_no_model_answer_raises_for_retry_without_writes',['PEXT-01'],no_answer)
        finally:worker.stop();await asyncio.wait_for(task,20)


async def retention_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.settings import Settings
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef,NodeWrite,EdgeWrite
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.consolidation import ConsolidationConsumer
    from engram_spanner_compat_remaining import graph_counts
    await run.reset(database,values);configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();rows=[event('retention-completion',occurred_at=(datetime.now(UTC)-timedelta(hours=h)).isoformat()) for h in (0,0,0,2,26,100)]
        assert (await client.post('/v1/events/batch',json={'events':rows})).status_code==201
        proj=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'retention-proj'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await proj.ensure_group();task=asyncio.create_task(proj.run())
        try:
            async def ready():return not await proj._subscription.lag() and not await proj._subscription.delivery_counts(100)
            await wait_until(ready,60)
        finally:proj.stop();await asyncio.wait_for(task,20)
        refs=[NodeRef('Event',r['event_id'],'event_id') for r in rows]
        await stores.graph.upsert_nodes([NodeWrite(ref,{'importance_score':1 if n==4 else 10,'access_count':0 if n==4 else 10}) for n,ref in enumerate(refs)])
        await stores.graph.upsert_edges([EdgeWrite('SIMILAR_TO',refs[3],refs[n],{'similarity_score':score}) for n,score in enumerate((0.2,0.3,0.95))])
        for retained_settings in (settings.retention,app.state.settings.retention):
            retained_settings.hot_hours=1;retained_settings.warm_hours=24;retained_settings.cold_hours=48
            retained_settings.cold_min_importance=3;retained_settings.cold_min_access_count=1;retained_settings.warm_min_similarity_score=0.7
        async def warm_api():
            before=await graph_counts(database)
            dry=await client.post('/v1/admin/prune',json={'tier':'warm','dry_run':True})
            after_dry=await graph_counts(database)
            live=await client.post('/v1/admin/prune',json={'tier':'warm','dry_run':False})
            after=await graph_counts(database)
            receipt={'dry_status':dry.status_code,'dry':dry.json(),'live_status':live.status_code,'live':live.json(),'before_edges':before['edges'],'after_edges':after['edges'],'dry_preserves_graph':before==after_dry,'expected_low_similarity_edges':2,'scope':'actual edge similarity properties, no invented Event-level similarity property'}
            (run.directory/'warm-prune-api.json').write_text(json.dumps(receipt,indent=2))
            assert dry.status_code==live.status_code==200 and receipt['dry_preserves_graph'],receipt
            assert dry.json()['pruned_edges']==live.json()['pruned_edges']==2,'warm API prune ignores eligible real SIMILAR_TO edge scores'
            return receipt
        await run.check('warm_API_dry_and_live_counts_follow_actual_edge_scores',['LIFE-03'],warm_api)
        async def forgetting():
            # Preserve cold nodes so the distinct archive-deletion stage has a real candidate.
            settings.retention.cold_min_importance=0;settings.retention.cold_min_access_count=0
            cons=ConsolidationConsumer(stores.subscription(settings.consumer.group_consolidation,'retention-cases'),stores.event_log,stores.graph,settings)
            calls=[];original=stores.graph.delete_archive_events
            async def observed(event_ids):
                count=await original(event_ids=event_ids);calls.append({'ids':event_ids,'count':count});return count
            stores.graph.delete_archive_events=observed
            try:await cons._run_forgetting()
            finally:stores.graph.delete_archive_events=original
            nodes=await stores.graph.get_nodes(refs);counts=await graph_counts(database)
            dry=await client.post('/v1/admin/prune',json={'tier':'cold','dry_run':True})
            still=await stores.graph.get_nodes(refs)
            live=await client.post('/v1/admin/prune',json={'tier':'cold','dry_run':False})
            final=await stores.graph.get_nodes(refs)
            receipt={'archive_deletion_calls':calls,'after_worker_nodes':list(r.key for r in nodes),'similarity_edges_after_worker':[e for e in counts['edges'] if e[1]=='SIMILAR_TO'],'cold_dry':dry.json(),'cold_live':live.json(),'dry_preserves_nodes':nodes==still,'final_event_ids':[r.key for r in final],'ledger_documents_retained':all(await stores.event_log.get_documents([r['event_id'] for r in rows]))}
            (run.directory/'nonzero-archive-and-cold-prune.json').write_text(json.dumps(receipt,indent=2))
            assert calls==[{'ids':[refs[5].key],'count':1}] and refs[5] not in nodes and refs[4] in nodes,receipt
            assert len(receipt['similarity_edges_after_worker'])==1 and dry.json()['pruned_nodes']==live.json()['pruned_nodes']==1,receipt
            assert receipt['dry_preserves_nodes'] and refs[4] not in final and len(final)==4 and receipt['ledger_documents_retained'],receipt
            return receipt
        await run.check('actual_worker_nonzero_archive_graph_deletion_then_API_cold_dry_live',['LIFE-03','CONS-02'],forgetting)

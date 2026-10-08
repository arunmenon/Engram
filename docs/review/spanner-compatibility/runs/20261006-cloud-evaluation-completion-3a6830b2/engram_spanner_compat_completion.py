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
    await run.reset(database,values);configure(values);app=create_app()
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

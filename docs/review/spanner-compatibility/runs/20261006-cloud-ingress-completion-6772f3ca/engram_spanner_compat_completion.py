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
            mixed=await client.post('/v1/events/batch',json={'events':[event('batch-mixed'),invalid,event('batch-unknown',event_type='not.declared')]})
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

"""Focused pack projection/extraction journeys over real Spanner stores."""
from __future__ import annotations
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os

import httpx
from engram_spanner_compat import configure
from engram_spanner_compat_remaining import event, graph_counts, wait_until


async def pack_cases(run, database, values, credentials):
    from context_graph.api.app import create_app, lifespan
    from context_graph.domain.pack_extraction import extraction_profiles
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.pack_extraction import PackExtractionConsumer
    await run.reset(database, values)
    configure(values)
    os.environ.update(CG_ONTOLOGY_TRUSTED_SOURCES="compat-resume", CG_ONTOLOGY_LOOKUP_LIMIT="2")
    app=create_app()
    async with lifespan(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),base_url="http://compat") as client:
        stores=app.state.stores; settings=Settings(); projector=configured_projector(settings.ontology)
        async def drain(worker):
            await worker.ensure_group()
            task=asyncio.create_task(worker.run())
            try:
                async def ready():
                    return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,60)
            finally:
                worker.stop(); await asyncio.wait_for(task,20)
        async def project():
            worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,"pack-cases"),
                                      stores.event_log,stores.graph,settings,projector,pack_lookup_limit=2)
            await drain(worker)
        async def send(kind,payload,**fields):
            row=event("pack-cases",event_type=kind,payload=payload,**fields)
            response=await client.post("/v1/events",json=row)
            assert response.status_code == 201,response.text
            return row
        async def latest():
            base=datetime.now(UTC)-timedelta(hours=2)
            common={"service":"payments","environment":"prod","artifact_id":"app:1.2","repo":"acme/app","change_numbers":[]}
            for minute in (30,10,20):
                await send("pdlc.service.deployed",common,occurred_at=(base+timedelta(minutes=minute)).isoformat())
            await send("pdlc.incident.detected",{**common,"incident_id":"INC-boundary","severity":"high"},
                       occurred_at=(base+timedelta(minutes=40)).isoformat())
            await project()
            edges=(await graph_counts(database))["edges"]
            actual=[edge for edge in edges if edge[1]=="OCCURRED_ON"]
            expected=f"Deployment:prod|app:1.2|{(base+timedelta(minutes=30)).isoformat()}"
            receipt={"limit":2,"candidate_count":3,"expected_latest":expected,"edges":actual}
            (run.directory / "latest-unprefixed.json").write_text(json.dumps(receipt,indent=2))
            assert actual == [["Incident:INC-boundary","OCCURRED_ON",expected]],receipt
            return receipt
        await run.check("pack_latest_lookup_exceeds_limit_out_of_occurrence_order",["PROJ-03"],latest)

        async def prefixes():
            await stores.graph.upsert_nodes([NodeWrite(NodeRef("Component","Component:"+name),
                                                     {"catalog_name":name,"repo":"acme/app","path_prefixes":[name+"/"]})
                                            for name in ("a","b","c")])
            await send("pdlc.change.merged",{"repo":"acme/app","number":42,"body":"", "files":["c/test.py"]})
            await project()
            actual=[edge for edge in (await graph_counts(database))["edges"] if edge[1]=="TOUCHES"]
            receipt={"setup":"three catalog Components via public graph port", "limit":2,
                     "expected":[["Change:acme/app|42","TOUCHES","Component:c"]],"actual":actual}
            (run.directory / "component-prefix-limit.json").write_text(json.dumps(receipt,indent=2))
            assert receipt["actual"] == receipt["expected"], "matching Component outside capped candidates silently omitted"
            return receipt
        await run.check("pack_component_prefix_match_beyond_lookup_limit",["PROJ-03"],prefixes)

        async def provenance():
            created=await send("pdlc.change.created",{"repo":"acme/app","number":7,"title":"review evidence"})
            await project()
            reviewed=await send("pdlc.change.reviewed",{"repo":"acme/app","number":7,"review_id":"r-proof","verdict":"approved"})
            await project()
            ref=NodeRef("Change","Change:acme/app|7")
            nodes=await stores.graph.get_nodes([ref]); assert nodes[ref]["status"] == "reviewed"
            edges=[edge for edge in (await graph_counts(database))["edges"] if edge[0]==ref.key and edge[1]=="DERIVED_FROM"]
            receipt={"created_event":created["event_id"],"review_event":reviewed["event_id"],"change":nodes[ref],"direct_evidence":edges}
            (run.directory / "review-transition-evidence.json").write_text(json.dumps(receipt,indent=2))
            assert [ref.key,"DERIVED_FROM",reviewed["event_id"]] in edges, "review state changed without direct event evidence"
            return receipt
        await run.check("review_lifecycle_transition_has_direct_provenance",["PROJ-04"],provenance)

        async def extraction_first():
            statement="The experiment requires verified evidence"
            row=await send("observation.input",{"content":statement})
            class Model:
                async def generate_text(self,prompt):
                    return json.dumps({"nodes":[{"ref":"n1","type":"Decision","statement":statement,"confidence":0.9}],"links":[]})
            profiles=extraction_profiles(projector.registry,max_nodes=5,max_links=5,max_text_chars=2000)
            worker=PackExtractionConsumer(stores.subscription(settings.consumer.group_pack_extraction,"pack-cases-extraction"),
                                          stores.event_log,stores.graph,profiles,projector,Model(),settings)
            await drain(worker)
            key="Decision:"+hashlib.sha256(statement.encode()).hexdigest()
            assert (await stores.graph.get_nodes([NodeRef("Decision",key)])).get(NodeRef("Decision",key))
            before=await graph_counts(database)
            await project()
            after=await graph_counts(database)
            evidence=[key,"DERIVED_FROM",row["event_id"]]
            receipt={"event_id":row["event_id"],"decision":key,"before_projection":before,"after_projection":after,
                     "extraction_pending":await worker._subscription.delivery_counts(100)}
            (run.directory / "pack-extraction-before-projection.json").write_text(json.dumps(receipt,indent=2))
            assert evidence in after["edges"], "pack extraction acknowledged before Event creation; evidence never repaired"
            return receipt
        await run.check("pack_extraction_first_preserves_source_evidence_after_projection",["PEXT-02","EXT-03"],extraction_first)


async def maintenance(run, database, values, credentials):
    """Actual consolidation timer, with observers around unchanged cloud methods."""
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef, NodeWrite, EdgeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.consolidation import ConsolidationConsumer
    await run.reset(database, values)
    configure(values)
    app=create_app()
    async with lifespan(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://compat") as client:
        stores=app.state.stores; settings=Settings()
        settings.decay.reflection_threshold=1
        settings.decay.reconsolidation_interval_hours=0.0003
        settings.retention.cold_min_importance=10
        settings.retention.cold_min_access_count=100
        rows=[]
        for age in (0,0,0,0,2,10,40):
            row=event("maintenance",occurred_at=(datetime.now(UTC)-timedelta(days=age)).isoformat(),importance_hint=1)
            response=await client.post("/v1/events",json=row)
            assert response.status_code==201,response.text
            rows.append(row)
        proj=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,"maintenance-projection"),
                                stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await proj.ensure_group(); task=asyncio.create_task(proj.run())
        try:
            async def ready():
                return not await proj._subscription.lag() and not await proj._subscription.delivery_counts(100)
            await wait_until(ready,60)
        finally:
            proj.stop(); await asyncio.wait_for(task,20)
        event_refs=[NodeRef("Event",row["event_id"],"event_id") for row in rows]
        linked=NodeRef("Entity","entity:maintenance-linked","entity_id")
        orphan=NodeRef("Entity","entity:maintenance-orphan","entity_id")
        await stores.graph.upsert_nodes([NodeWrite(linked,{"name":"linked","entity_type":"technology"}),
                                       NodeWrite(orphan,{"name":"orphan","entity_type":"technology"})])
        await stores.graph.upsert_edges([EdgeWrite("REFERENCES",event_refs[0],linked),
                                        EdgeWrite("SIMILAR_TO",event_refs[4],event_refs[0],{"similarity_score":0.2}),
                                        EdgeWrite("SIMILAR_TO",event_refs[4],event_refs[1],{"similarity_score":0.95})])
        stages=[]; restore={}
        methods=("update_importance_from_centrality","delete_edges_by_type_and_age","delete_cold_events",
                 "get_archive_event_ids","delete_archive_events","delete_orphan_nodes")
        for name in methods:
            original=getattr(stores.graph,name); restore[name]=original
            def make_observer(original,name):
                async def observed(*args,**kwargs):
                    result=await original(*args,**kwargs)
                    record={"operation":name,"result":result}
                    if name=="update_importance_from_centrality":
                        record["event_importance"]={ref.key:props.get("importance_score") for ref,props in (await stores.graph.get_nodes(event_refs)).items()}
                    stages.append(record)
                    return result
                return observed
            setattr(stores.graph,name,make_observer(original,name))
        worker=ConsolidationConsumer(stores.subscription(settings.consumer.group_consolidation,"maintenance-timer"),
                                    stores.event_log,stores.graph,settings)
        finished=asyncio.Event(); cycle_errors=[]; actual_cycle=worker._run_consolidation_cycle
        async def observed_cycle():
            try:
                await actual_cycle()
            except Exception as exc:
                cycle_errors.append({"type":type(exc).__name__,"message":str(exc)[:1000]})
                raise
            finally:
                worker.stop(); finished.set()
        worker._run_consolidation_cycle=observed_cycle
        async def cycle():
            await worker.ensure_group(); task=asyncio.create_task(worker.run())
            try:
                await asyncio.wait_for(finished.wait(),90)
            finally:
                worker.stop(); await asyncio.wait_for(task,20)
                for name,original in restore.items():setattr(stores.graph,name,original)
            nodes=await stores.graph.get_nodes(event_refs+[linked,orphan])
            counts=await graph_counts(database)
            documents=await stores.event_log.get_documents([row["event_id"] for row in rows])
            receipt={"events":rows,"stages":stages,"cycle_errors":cycle_errors,"after":counts,
                     "surviving_ids":[ref.key for ref in nodes],"documents_present":len(documents),
                     "consumer_pending":await worker._subscription.delivery_counts(100),
                     "settings":{"cold_min_importance":10,"cold_min_access_count":100,"threshold":1},
                     "scope":"one actual timer cycle; no model or alternate storage; observing wrappers only"}
            (run.directory / "maintenance-cycle.json").write_text(json.dumps(receipt,indent=2,default=str))
            assert not cycle_errors,cycle_errors
            assert counts["nodes"].get("Summary",0)>=3,counts
            assert all(ref in nodes for ref in event_refs[:5]),receipt
            assert all(ref not in nodes for ref in event_refs[5:]),receipt
            assert linked in nodes and orphan not in nodes,receipt
            assert [rows[4]["event_id"],"SIMILAR_TO",rows[0]["event_id"]] not in counts["edges"]
            assert [rows[4]["event_id"],"SIMILAR_TO",rows[1]["event_id"]] in counts["edges"]
            centrality=next(stage for stage in stages if stage["operation"]=="update_importance_from_centrality")
            assert centrality["result"]>=5 and max(centrality["event_importance"].values())>=6,centrality
            assert len(documents)==7 and all(documents),receipt
            assert not receipt["consumer_pending"],receipt
            return receipt
        await run.check("full_consolidation_timer_centrality_forgetting_orphans_housekeeping",["CONS-01","CONS-02","LIFE-03"],cycle,timeout_seconds=110)


async def commit_cases(run,database,values,credentials):
    """API idempotence/commit split/partial failure against the real ledger."""
    from context_graph.api.app import create_app, lifespan
    from context_graph.adapters.spanner.commits import CommitBudget
    await run.reset(database,values); configure(values)
    os.environ.update(CG_SPANNER_COMMIT_MAX_MUTATIONS="66",CG_SPANNER_COMMIT_MAX_BYTES="2048")
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://compat") as client:
        stores=app.state.stores
        async def simultaneous():
            row=event("commit-duplicates")
            variants=[{**row,"payload":{"content":f"winner candidate {i}"}} for i in range(6)]
            responses=await asyncio.gather(*(client.post("/v1/events",json=variant) for variant in variants))
            bodies=[r.json() for r in responses]
            document=(await stores.event_log.get_documents([row["event_id"]]))[0]
            receipt={"statuses":[r.status_code for r in responses],"responses":bodies,"stored_payload":document["payload"]}
            (run.directory / "simultaneous-dedup.json").write_text(json.dumps(receipt,indent=2))
            assert all(r.status_code==201 for r in responses),receipt
            assert sum(body["status"]=="created" for body in bodies)==1,receipt
            assert len({body["global_position"] for body in bodies})==1,receipt
            winner=next(i for i,body in enumerate(bodies) if body["status"]=="created")
            assert document["payload"]==variants[winner]["payload"],receipt
            assert await stores.event_log.stream_length()==1,receipt
            return receipt
        await run.check("simultaneous_duplicate_different_payload_first_write_wins",["ING-01","LED-02","SUB-04"],simultaneous)

        async def partial():
            rows=[event("commit-split",payload={"content":f"chunk row {i}"}) for i in range(11)]
            original=stores.event_log._append_chunk_sync; calls=[]
            def fail_third(entries):
                calls.append(len(entries))
                if len(calls)==3:raise RuntimeError("synthetic third commit chunk unavailable")
                return original(entries)
            stores.event_log._append_chunk_sync=fail_third
            try:
                response=await client.post("/v1/events/batch",json={"events":rows})
            finally:stores.event_log._append_chunk_sync=original
            first_length=await stores.event_log.stream_length()
            retried=await client.post("/v1/events/batch",json={"events":rows})
            docs=await stores.event_log.get_documents([row["event_id"] for row in rows])
            receipt={"budget":{"mutations":66,"bytes":2048},"attempted_chunk_sizes":calls,
                     "first_status":response.status_code,"first_response":response.json(),"first_ledger_length":first_length,
                     "retry_status":retried.status_code,"retry":retried.json(),"final_length":await stores.event_log.stream_length(),
                     "documents":len(docs),"fault":"synthetic failure before third real commit; prior two real commits retained"}
            (run.directory / "commit-partial-retry.json").write_text(json.dumps(receipt,indent=2))
            assert calls==[2,2,2],receipt
            assert response.status_code==201 and response.json()["accepted"]==4 and response.json()["rejected"]==7,receipt
            assert first_length==5,receipt
            assert retried.status_code==201 and retried.json()["accepted"]==11,receipt
            assert len(docs)==11 and all(docs) and receipt["final_length"]==12,receipt
            assert all(doc["payload"]==row["payload"] for doc,row in zip(docs,rows)),receipt
            return receipt
        await run.check("exact_two_row_commit_budget_partial_failure_retry",["ING-02","OPS-04","LED-02"],partial)

        async def oversized():
            row=event("oversize-row",payload={"content":"bounded large item "*200})
            response=await client.post("/v1/events",json=row)
            doc=(await stores.event_log.get_documents([row["event_id"]]))[0]
            receipt={"configured_budget_bytes":2048,"payload_bytes":len(json.dumps(row["payload"]).encode()),
                     "status":response.status_code,"response":response.json(),"document_preserved":doc is not None and doc["payload"]==row["payload"],
                     "contract":"an item exceeding configured estimate is delegated to Spanner in a single transaction; not a hard API ceiling"}
            (run.directory / "single-over-budget-item.json").write_text(json.dumps(receipt,indent=2))
            assert response.status_code==201 and receipt["document_preserved"],receipt
            return receipt
        await run.check("single_over_configured_byte_budget_delegated_to_service",["OPS-04"],oversized)


async def pack_policy(run,database,values,credentials):
    from context_graph.api.app import create_app, lifespan
    from context_graph.domain.pack_extraction import extraction_profiles
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.pack_extraction import PackExtractionConsumer
    await run.reset(database,values); configure(values)
    os.environ["CG_ONTOLOGY_TRUSTED_SOURCES"]="signed-only"
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://compat") as client:
        stores=app.state.stores; settings=Settings(); projector=configured_projector(settings.ontology)
        profiles=extraction_profiles(projector.registry,max_nodes=1,max_links=1,max_text_chars=2000)
        async def drain(worker):
            await worker.ensure_group(); task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,60)
            finally:worker.stop(); await asyncio.wait_for(task,20)
        answers={}
        class Model:
            async def generate_text(self,prompt):
                for text,answer in answers.items():
                    if text in prompt:return answer
                return '{"nodes":[],"links":[]}'
        async def process(statement,answer):
            row=event("pack-policy",payload={"content":statement})
            response=await client.post("/v1/events",json=row);assert response.status_code==201,response.text
            await drain(ProjectionConsumer(stores.subscription(settings.consumer.group_projection,"policy-projection"),stores.event_log,stores.graph,settings,projector))
            answers[statement]=answer
            worker=PackExtractionConsumer(stores.subscription(settings.consumer.group_pack_extraction,"policy-extraction"),stores.event_log,stores.graph,profiles,projector,Model(),settings)
            await drain(worker)
            return row,await graph_counts(database)
        def ref(text):return NodeRef("Decision","Decision:"+hashlib.sha256(text.encode()).hexdigest())
        async def invalid():
            before=await graph_counts(database)
            row,after=await process("invalid-json-policy-marker","this is not a JSON answer")
            receipt={"event_id":row["event_id"],"before":before,"after":after,"contract":"invalid model JSON acknowledged with no proposed node"}
            (run.directory / "invalid-extraction-answer.json").write_text(json.dumps(receipt,indent=2))
            assert not after["nodes"].get("Decision",0),receipt
            return receipt
        await run.check("pack_invalid_model_JSON_acknowledged_without_proposal",["PEXT-01"],invalid)
        async def bounded():
            statement="bounded-policy-marker decision one"; second="bounded decision two"
            answer=json.dumps({"nodes":[{"ref":"n1","type":"Decision","statement":statement,"confidence":1,"source_trust":"trusted"},
                                         {"ref":"n2","type":"Decision","statement":second,"confidence":1}],
                               "links":[{"type":"IMPLEMENTS","from":"n1","to":"missing-target","confidence":1}]})
            row,counts=await process(statement,answer)
            refs=[ref(statement),ref(second)]; nodes=await stores.graph.get_nodes(refs)
            receipt={"event_id":row["event_id"],"nodes":{r.key:p for r,p in nodes.items()},"graph":counts,
                     "bounds":{"nodes":1,"links":1},"expected_trust":"untrusted","expected_confidence":0.8}
            (run.directory / "bounded-proposal-confidence-trust.json").write_text(json.dumps(receipt,indent=2))
            assert refs[0] in nodes and refs[1] not in nodes,receipt
            assert nodes[refs[0]]["confidence"]==0.8 and nodes[refs[0]]["source_trust"]=="untrusted",receipt
            assert [refs[0].key,"DERIVED_FROM",row["event_id"]] in counts["edges"],receipt
            assert not any(e[1]=="IMPLEMENTS" for e in counts["edges"]),receipt
            return receipt
        await run.check("pack_bounded_proposal_confidence_trust_and_unknown_link",["PEXT-01","PEXT-02"],bounded)
        async def preserve():
            statement="human-authored-policy-marker decision"; target=ref(statement)
            expected={"statement":statement,"rationale":"Reviewed by a human","status":"accepted","confidence":1.0,"source_trust":"trusted"}
            await stores.graph.upsert_nodes([NodeWrite(target,expected)])
            row,counts=await process(statement,json.dumps({"nodes":[{"ref":"n1","type":"Decision","statement":statement,"rationale":"LLM replacement","confidence":0.1}],"links":[]}))
            node=(await stores.graph.get_nodes([target]))[target]
            receipt={"expected":expected,"actual":node,"event_id":row["event_id"],"graph":counts}
            (run.directory / "authoritative-proposal-preservation.json").write_text(json.dumps(receipt,indent=2))
            assert all(node[k]==v for k,v in expected.items()),receipt
            assert [target.key,"DERIVED_FROM",row["event_id"]] in counts["edges"],receipt
            return receipt
        await run.check("pack_proposal_preserves_existing_authoritative_properties",["PEXT-02"],preserve)


async def keyword_features(run,database,values,credentials):
    import math
    from context_graph.api.app import create_app, lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef, NodeWrite
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values);os.environ['CG_PPR_ENABLED']='true'
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();rows=[]
        for session,text in [('keyword-a','Python café refund-retries'),('keyword-a','PYTHON café refund-retries'),('keyword-b','Python café refund-retries'),('keyword-b','Unrelated astronomy')]:
            row=event(session,payload={'content':text});rows.append(row)
            response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
        worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'keyword-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
        await worker.ensure_group();task=asyncio.create_task(worker.run())
        try:
            async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
            await wait_until(ready,60)
        finally:worker.stop();await asyncio.wait_for(task,20)
        async def native():
            receipts=[]
            for text,session,expected in [('python',None,rows[:3]),('PYTHON','keyword-a',rows[:2]),('café',None,rows[:3]),('refund-retries',None,rows[:3]),('notpresentxyz',None,[]),('',None,[])]:
                hits=await stores.keyword_index.search(text,session_id=session,limit=10)
                record={'query':text,'session':session,'hits':[{'id':h.id,'rank':h.rank,'score':h.score} for h in hits],'expected_ids':[r['event_id'] for r in expected]}
                receipts.append(record)
                (run.directory / 'native-keyword-boundaries.json').write_text(json.dumps(receipts,indent=2))
                assert {h.id for h in hits}=={r['event_id'] for r in expected},record
                assert all(math.isfinite(h.score) and 0<=h.score<=1 for h in hits),record
                assert [h.rank for h in hits]==list(range(len(hits))),record
            return receipts
        await run.check('native_keyword_case_unicode_punctuation_empty_and_session_filter',['SEARCH-01'],native)
        engine=app.state.retrieval
        async def keyword_only():
            original=engine._get_graph_seeds;embed=engine._embedding_service
            async def no_graph(*a,**kw):return []
            engine._get_graph_seeds=no_graph;engine._embedding_service=None
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','session_id':'keyword-a','max_nodes':10})
            finally:engine._get_graph_seeds=original;engine._embedding_service=embed
            receipt={'status':response.status_code,'body':response.json(),'controls':'graph seeds explicitly empty; embedding disabled; real native keyword index remains active'}
            (run.directory / 'keyword-only-subgraph.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and {r['event_id'] for r in rows[:2]}<=set(response.json()['nodes']),receipt
            assert not any(r['event_id'] in response.json()['nodes'] for r in rows[2:]),receipt
            return receipt
        await run.check('keyword_only_API_hydration_and_session_isolation',['MEM-03','SEARCH-01'],keyword_only)
        async def enabled_features():
            for index,row in enumerate(rows[:2]):
                embedding=([1.0,0.0] if index==0 else [0.8,0.6])+[0.0]*382
                await stores.graph.upsert_nodes([NodeWrite(NodeRef('Event',row['event_id'],'event_id'),{'embedding':embedding})])
            calls={'embeddings':[],'hyde':0,'MMR':0,'PPR':0}
            class Embed:
                async def embed_text(self,text):calls['embeddings'].append(text);return [1.0]+[0.0]*383
            class LLM:
                async def generate_text(self,prompt):calls['hyde']+=1;return 'Python café storage'
            original_embed,original_llm=engine._embedding_service,engine._llm_client
            original_mmr,original_ppr=engine._apply_mmr,engine._apply_ppr
            def mmr(*a,**kw):calls['MMR']+=1;return original_mmr(*a,**kw)
            def ppr(*a,**kw):calls['PPR']+=1;return original_ppr(*a,**kw)
            engine._embedding_service=Embed();engine._llm_client=LLM();engine._apply_mmr=mmr;engine._apply_ppr=ppr
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','session_id':'keyword-a','use_hyde':True,'max_nodes':10})
            finally:engine._embedding_service=original_embed;engine._llm_client=original_llm;engine._apply_mmr=original_mmr;engine._apply_ppr=original_ppr
            receipt={'calls':calls,'status':response.status_code,'body':response.json(),'scope':'scripted HyDE/query embedding; real graph, ANN and keyword ports; bounded feature smoke, not ranking quality benchmark'}
            (run.directory / 'enabled-retrieval-features.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and response.json()['nodes'],receipt
            assert calls['hyde']==calls['MMR']==calls['PPR']==1 and 'Python café storage' in calls['embeddings'][0],receipt
            assert engine._ppr_settings.enabled,receipt
            assert all(math.isfinite(n['scores']['decay_score']) for n in response.json()['nodes'].values()),receipt
            return receipt
        await run.check('PPR_MMR_HyDE_RRF_decay_enabled_API_smoke',['MEM-04'],enabled_features)
        async def degradation():
            original_search=stores.keyword_index.search;original_llm=engine._llm_client;original_timeout=engine._hyde_hot_path_timeout
            class Slow:
                async def generate_text(self,prompt):await asyncio.sleep(1);return 'late'
            async def failing_keyword(*a,**kw):raise RuntimeError('synthetic keyword channel failure')
            stores.keyword_index.search=failing_keyword;engine._llm_client=Slow();engine._hyde_hot_path_timeout=0.05
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','session_id':'keyword-a','use_hyde':True,'max_nodes':10})
            finally:stores.keyword_index.search=original_search;engine._llm_client=original_llm;engine._hyde_hot_path_timeout=original_timeout
            receipt={'status':response.status_code,'body':response.json(),'faults':'synthetic keyword failure and 50ms model timeout; actual graph channel retained'}
            (run.directory / 'retrieval-channel-degradation.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and {r['event_id'] for r in rows[:2]}<=set(response.json()['nodes']),receipt
            return receipt
        await run.check('keyword_failure_HyDE_timeout_graph_fallback',['MEM-03','MEM-04'],degradation)

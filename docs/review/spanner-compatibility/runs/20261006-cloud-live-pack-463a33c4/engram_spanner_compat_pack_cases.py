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
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','agent_id':'compat-resume','session_id':'keyword-a','max_nodes':10})
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
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','agent_id':'compat-resume','session_id':'keyword-a','use_hyde':True,'max_nodes':10})
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
            try:response=await client.post('/v1/query/subgraph',json={'query':'Python','agent_id':'compat-resume','session_id':'keyword-a','use_hyde':True,'max_nodes':10})
            finally:stores.keyword_index.search=original_search;engine._llm_client=original_llm;engine._hyde_hot_path_timeout=original_timeout
            receipt={'status':response.status_code,'body':response.json(),'faults':'synthetic keyword failure and 50ms model timeout; actual graph channel retained'}
            (run.directory / 'retrieval-channel-degradation.json').write_text(json.dumps(receipt,indent=2))
            assert response.status_code==200 and {r['event_id'] for r in rows[:2]}<=set(response.json()['nodes']),receipt
            return receipt
        await run.check('keyword_failure_HyDE_timeout_graph_fallback',['MEM-03','MEM-04'],degradation)


async def subscriptions(run,database,values,credentials):
    import time,zlib
    from context_graph.api.app import create_app,lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values)
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();sessions={}
        for number in range(1000):
            name=f'all-shards-{number}';sessions.setdefault(zlib.crc32(name.encode())%16,name)
            if len(sessions)==16:break
        assert len(sessions)==16
        rows=[event(sessions[shard]) for shard in sorted(sessions)]
        workers=[];tasks=[]
        for group in ('compat-shards-A','compat-shards-B'):
            worker=ProjectionConsumer(stores.subscription(group,group),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
            await worker.ensure_group();workers.append(worker);tasks.append(asyncio.create_task(worker.run()))
        async def independent():
            try:
                response=await client.post('/v1/events/batch',json={'events':rows});assert response.status_code==201,response.text
                async def ready():
                    return all([not await w._subscription.lag() and not await w._subscription.delivery_counts(100) for w in workers])
                await wait_until(ready,60)
            finally:
                for w in workers:w.stop()
                await asyncio.wait_for(asyncio.gather(*tasks),20)
            def shard_counts():
                with database.snapshot() as snap:return dict(snap.execute_sql('SELECT shard, COUNT(*) FROM Events GROUP BY shard'))
            actual=await asyncio.to_thread(shard_counts);counts=await graph_counts(database)
            receipt={'shards':actual,'graph':counts,'group_counters':{w._subscription.group_name:{'unread':await w._subscription.lag(),'pending':await w._subscription.delivery_counts(100)} for w in workers},
                     'workers':'two actual independent projection groups, both begun before ingress'}
            (run.directory / 'all-shards-independent-groups.json').write_text(json.dumps(receipt,indent=2))
            assert actual=={i:1 for i in range(16)},receipt
            assert counts['nodes'].get('Event')==16,receipt
            return receipt
        await run.check('all_sixteen_shards_two_independent_actual_workers',['SUB-01'],independent)
        async def late_pages():
            late=stores.subscription('compat-late','late-owner');await late.ensure_group()
            before=await late.lag();deliveries=await late.read_new(100,0)
            after=await late.lag();pending=await late.delivery_counts(100)
            pages=[];cursor=None
            while True:
                page=await late.read_pending(3,after=cursor)
                if not page:break
                pages.extend(d.position for d in page);cursor=page[-1].position
            await late.ack(*(d.position for d in deliveries[:3]))
            partial=await late.delivery_counts(100)
            await late.dead_letter(deliveries[3],delivery_count=2)
            await late.ack(*(d.position for d in deliveries[4:]))
            def dlq_rows():
                with database.snapshot() as snap:return list(snap.execute_sql("SELECT COUNT(*) FROM ConsumerDeadLetters WHERE group_name='compat-late'"))
            receipt={'unread_before':before,'unread_after_delivery':after,'pending_before_ACK':len(pending),
                     'paged_positions':pages,'pending_after_partial_ACK':len(partial),
                     'pending_after_DLQ_ACK':await late.delivery_counts(100),'DLQ_count':await asyncio.to_thread(dlq_rows)}
            (run.directory / 'late-group-pages-ACK-DLQ.json').write_text(json.dumps(receipt,indent=2))
            assert before==16 and after==0 and len(pending)==16 and len(partial)==13,receipt
            assert len(pages)==len(set(pages))==16 and set(pages)==set(pending),receipt
            assert not receipt['pending_after_DLQ_ACK'] and receipt['DLQ_count']==[[1]],receipt
            return receipt
        await run.check('late_group_history_pending_pages_partial_ACK_and_DLQ',['SUB-01','SUB-02'],late_pages)
        async def blocking():
            sub=stores.subscription('compat-wakeup','wakeup');await sub.ensure_group()
            existing=await sub.read_new(100,0);await sub.ack(*(d.position for d in existing))
            started=time.monotonic();waiting=asyncio.create_task(sub.read_new(1,3000));await asyncio.sleep(0.1)
            row=event('blocking-wakeup');response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
            try:delivered=await asyncio.wait_for(waiting,5)
            finally:
                if not waiting.done():waiting.cancel();await asyncio.gather(waiting,return_exceptions=True)
            receipt={'wait_seconds':round(time.monotonic()-started,3),'event_id':row['event_id'],'delivered_ids':[d.fields['event_id'] for d in delivered]}
            if delivered:await sub.ack(*(d.position for d in delivered))
            (run.directory / 'blocking-wakeup.json').write_text(json.dumps(receipt,indent=2))
            assert receipt['delivered_ids']==[row['event_id']],receipt
            return receipt
        await run.check('blocking_subscription_wakes_for_new_API_event',['SUB-01'],blocking)
        async def uncertain():
            from google.api_core.exceptions import ServiceUnavailable
            original=stores.event_log._append_chunk_sync
            def committed_then_lost(entries):
                original(entries)
                raise ServiceUnavailable('synthetic lost response after confirmed real commit')
            row=event('uncertain-commit')
            stores.event_log._append_chunk_sync=committed_then_lost
            try:first=await client.post('/v1/events',json=row)
            finally:stores.event_log._append_chunk_sync=original
            retry=await client.post('/v1/events',json=row)
            docs=await stores.event_log.get_documents([row['event_id']])
            receipt={'first_status':first.status_code,'retry_status':retry.status_code,'retry':retry.json(),
                     'document_preserved':docs[0] is not None and docs[0]['payload']==row['payload'],
                     'fault':'synthetic lost commit response; actual prior Spanner write retained'}
            (run.directory / 'uncertain-commit-retry.json').write_text(json.dumps(receipt,indent=2))
            assert first.status_code==503 and retry.status_code==201 and retry.json()['status']=='duplicate',receipt
            assert receipt['document_preserved'] and await stores.event_log.stream_length()==18,receipt
            return receipt
        await run.check('uncertain_commit_API_retry_duplicate_preserves_payload',['ING-04','OPS-04'],uncertain)


async def webhook_handlers(run,database,values,credentials):
    import copy,hmac
    from context_graph.api.app import create_app,lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values)
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();cases=[];now=datetime.now(UTC).isoformat()
        base={'repository':{'full_name':'acme/compat'}}
        for i,(action,merged,kind) in enumerate([('opened',False,'created'),('reopened',False,'created'),('edited',False,'updated'),('synchronize',False,'updated'),('closed',True,'merged'),('closed',False,'abandoned')]):
            payload={**base,'action':action,'pull_request':{'number':i+1,'title':'compat','body':'','head':{'sha':'abc'},'merged':merged,'merge_commit_sha':'abc',**{field:now for field in ('created_at','updated_at','merged_at','closed_at')}}}
            cases.append(('github','pull_request',payload,'pdlc.change.'+kind,{}))
        for i,verdict in enumerate(('approved','changes_requested','commented')):
            cases.append(('github','pull_request_review',{**base,'action':'submitted','pull_request':{'number':1},'review':{'id':i+1,'state':verdict,'submitted_at':now}},'pdlc.change.reviewed',{'verdict':verdict}))
        outcomes={'success':'success','failure':'failure','cancelled':'cancel','timed_out':'error','action_required':'error','startup_failure':'error','stale':'error','skipped':'skipped','neutral':'skipped','unexpected':'error'}
        for i,(conclusion,outcome) in enumerate(outcomes.items()):
            cases.append(('github','check_run',{**base,'action':'completed','check_run':{'id':i+1,'name':'unit','head_sha':'abc','completed_at':now,'conclusion':conclusion,'pull_requests':[{'number':1}]}},'pdlc.testcaserun.'+('skipped' if outcome=='skipped' else 'finished'),{'outcome':outcome}))
        cases.append(('github','release',{**base,'action':'published','release':{'tag_name':'v1','body':'Breaking change #1 /pull/2','published_at':now}},'pdlc.release.published',{'version':'v1','has_breaking':True}))
        cases.append(('github','deployment_status',{**base,'deployment_status':{'state':'success','created_at':now},'deployment':{'environment':'prod','sha':'abc'}},'pdlc.service.deployed',{'service':'acme/compat','environment':'prod'}))
        for i,action in enumerate(('opened','edited','reopened','labeled','unlabeled','assigned','unassigned','closed')):
            issue={'number':100+i,'title':'issue compat','state':'closed' if action=='closed' else 'open','labels':[{'name':'bug'}],'updated_at':now,'state_reason':'not_planned' if action=='closed' else None}
            kind='created' if action=='opened' else 'closed' if action=='closed' else 'updated'
            cases.append(('github','issues',{**base,'action':action,'issue':issue},'pdlc.ticket.'+kind,{'work_type':'bug','status':"Won't Do" if action=='closed' else 'To Do'}))
        for i,(hook,status,kind) in enumerate([('jira:issue_created','To Do','created'),('jira:issue_updated','In Progress','updated'),('jira:issue_updated','Done','closed'),('jira:issue_updated','Closed','updated'),('jira:issue_updated',"Won't Do",'closed')]):
            cases.append(('jira','',{ 'webhookEvent':hook,'timestamp':int(datetime.now(UTC).timestamp()*1000),'issue':{'key':f'CP-{i+1}','fields':{'summary':'Jira compat','project':{'key':'CP'},'status':{'name':status},'issuetype':{'name':'Bug'},'parent':{'key':'CP-0'}}}},'pdlc.ticket.'+kind,{'tracker':'jira','work_type':'bug','parent_key':'CP-0','status':status}))
        for i,(source_type,mapped) in enumerate([('Epic','epic'),('Story','story'),('Task','task'),('Sub-task','task'),('Subtask','task'),('Change','production_change'),('Custom type','task')]):
            cases.append(('jira','',{'webhookEvent':'jira:issue_created','issue':{'key':f'TYPE-{i}','fields':{'summary':'Type mapping','status':{'name':'To Do'},'issuetype':{'name':source_type}}}},'pdlc.ticket.created',{'work_type':mapped,'tracker':'jira','status':'To Do'}))
        cases.extend([('github','ping',base,None,{}),('github','pull_request',{**base,'action':'assigned'},None,{}),('github','issues',{**base,'action':'opened','issue':{'pull_request':{'url':'x'}}},None,{}),('jira','',{'webhookEvent':'jira:issue_created','issue':{'fields':{}}},None,{}),('jira','',{'webhookEvent':'jira:issue_deleted','issue':{'key':'CP-9'}},None,{})])
        receipts=[];ids=[]
        async def signed(source,kind,payload,delivery):
            body=json.dumps(payload,separators=(',',':')).encode();signature='sha256='+hmac.new(b'compat-test-secret',body,hashlib.sha256).hexdigest()
            headers={'content-type':'application/json',('x-hub-signature-256' if source=='github' else 'x-hub-signature'):signature}
            if source=='github':headers.update({'x-github-event':kind,'x-github-delivery':delivery})
            else:headers['x-atlassian-webhook-identifier']=delivery
            return await client.post('/v1/webhooks/'+source,content=body,headers=headers)
        async def translate_all():
            for index,(source,kind,payload,expected,fields) in enumerate(cases):
                response=await signed(source,kind,payload,f'case-{index}')
                assert response.status_code==202,response.text
                event_ids=response.json()['event_ids'];assert len(event_ids)==int(expected is not None),(index,response.text)
                docs=await stores.event_log.get_documents(event_ids) if event_ids else []
                receipt={'index':index,'source':source,'kind':kind,'action':payload.get('action',payload.get('webhookEvent')),'expected_type':expected,'documents':docs}
                receipts.append(receipt);ids.extend(event_ids)
                (run.directory / 'webhook-handler-mappings.json').write_text(json.dumps(receipts,indent=2))
                for doc in docs:
                    assert doc['event_type']==expected,receipt
                    assert all(doc['payload'].get(k)==v for k,v in fields.items()),receipt
                    if kind=='pull_request' and expected in ('pdlc.change.created','pdlc.change.merged'):assert doc['payload']['files']==[],receipt
            return {'cases':len(cases),'events':len(ids),'receipts':'webhook-handler-mappings.json'}
        await run.check('signed_GitHub_Jira_all_supported_handlers_actions_and_ignored',['HOOK-01','HOOK-02'],translate_all)
        async def redelivery():
            source,kind,payload,_,_=cases[0]
            same=await signed(source,kind,payload,'different-delivery-header')
            changed=copy.deepcopy(payload);changed['pull_request']['title']='changed signed body'
            other=await signed(source,kind,changed,'case-0')
            receipt={'original_ids':ids[:1],'same_body_new_delivery':same.json(),'changed_body_same_delivery':other.json()}
            (run.directory / 'webhook-redelivery-body-identity.json').write_text(json.dumps(receipt,indent=2))
            assert same.status_code==other.status_code==202 and same.json()['event_ids']==ids[:1],receipt
            assert other.json()['event_ids']!=ids[:1],receipt
            assert await stores.event_log.stream_length()==len(ids)+1,receipt
            return receipt
        await run.check('signed_body_dedup_independent_of_delivery_ID',['HOOK-03','ING-04'],redelivery)
        async def project_all():
            worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'webhook-handler-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,100)
            finally:worker.stop();await asyncio.wait_for(task,20)
            counts=await graph_counts(database)
            (run.directory / 'webhook-projection.json').write_text(json.dumps(counts,indent=2))
            assert counts['nodes'].get('Event')==len(ids)+1,counts
            return counts
        await run.check('all_webhook_normalized_events_actual_projection',['HOOK-01','HOOK-02','APP-02'],project_all,timeout_seconds=115)


async def enrichment_cases(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.domain.scoring import compute_relevance_score
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.errors import UnavailableError
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.enrichment import EnrichmentConsumer
    configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings()
        async def drain(worker):
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,45)
            finally:worker.stop();await asyncio.wait_for(task,20)
        for mode in ('disabled','provider_failure','short_vector','zero_vector','storage_failure'):
            async def scenario(mode=mode):
                await run.reset(database,values)
                row=event('enrichment-'+mode,tool_name=mode,importance_hint=7)
                response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
                await drain(ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'embedding-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology)))
                class Model:
                    async def embed_text(self,text):
                        if mode=='provider_failure':raise RuntimeError('synthetic embedding provider outage')
                        if mode=='short_vector':return [1.0,0.0,0.0]
                        if mode=='zero_vector':return [0.0]*384
                        return [1.0]+[0.0]*383
                worker=EnrichmentConsumer(stores.subscription(settings.consumer.group_enrichment,'embedding-cases'),stores.event_log,stores.graph,settings,None if mode=='disabled' else Model())
                if mode=='storage_failure':
                    original=stores.graph.store_event_embedding
                    async def fault(*a,**kw):raise UnavailableError('synthetic embedding storage write failure')
                    stores.graph.store_event_embedding=fault
                    await worker.ensure_group();task=asyncio.create_task(worker.run())
                    try:
                        async def pending():return bool(await worker._subscription.delivery_counts(100))
                        await wait_until(pending,45);await asyncio.sleep(1)
                        stores.graph.store_event_embedding=original
                        await asyncio.sleep(3)
                        pending_after=await worker._subscription.delivery_counts(100)
                    finally:
                        stores.graph.store_event_embedding=original;worker.stop();await asyncio.wait_for(task,20)
                else:
                    await drain(worker);pending_after=await worker._subscription.delivery_counts(100)
                target=NodeRef('Event',row['event_id'],'event_id');node=(await stores.graph.get_nodes([target]))[target]
                receipt={'mode':mode,'node':node,'pending':pending_after,'provider':'synthetic fixture','real_cloud_keywords_write':True}
                if mode in ('short_vector','zero_vector'):receipt['query_relevance']=compute_relevance_score([1.0]+[0.0]*383,node['embedding'])
                (run.directory / (mode+'-enrichment.json')).write_text(json.dumps(receipt,indent=2))
                assert node['importance_score']==7 and mode in node['keywords'],receipt
                if mode in ('disabled','provider_failure'):assert not node.get('embedding'),receipt
                if mode=='short_vector':assert len(node['embedding'])==3 and receipt['query_relevance']==0.5,receipt
                if mode=='zero_vector':assert len(node['embedding'])==384 and receipt['query_relevance']==0.5,receipt
                assert not pending_after,'removed storage failure is not retried during normal worker execution (#14)'
                return receipt
            await run.check('enrichment_'+mode,['ENR-02']+(['SUB-02'] if mode=='storage_failure' else []),scenario,timeout_seconds=90)


async def archive_restore(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.adapters.fs.archive import FilesystemArchiveStore
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database,values);configure(values);app=create_app()
    archive=FilesystemArchiveStore(run.directory / 'archive')
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings()
        old=event('archive-old',occurred_at=(datetime.now(UTC)-timedelta(days=100)).isoformat(),importance_hint=1,payload={'content':'Restore archived payload','nested':{'weight':0.125}})
        fresh=event('archive-fresh',payload={'content':'Keep this fresh payload'})
        for row in (old,fresh):
            response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
        async def project():
            worker=ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'archive-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology))
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,60)
            finally:worker.stop();await asyncio.wait_for(task,20)
        await project()
        async def archive_failure():
            original=archive.archive_events
            async def fault(*a,**kw):raise OSError('synthetic archive write failure')
            archive.archive_events=fault
            try:counts=await stores.event_log.expire(90,archive_store=archive)
            finally:archive.archive_events=original
            documents=await stores.event_log.get_documents([old['event_id'],fresh['event_id']])
            receipt={'expired':counts,'documents_preserved':all(documents),'archives':await archive.list_archives(),'fault':'synthetic FS archive failure; real Spanner expiry path'}
            (run.directory / 'archive-failure-preserves-documents.json').write_text(json.dumps(receipt,indent=2))
            assert counts==(0,0) and all(documents) and not receipt['archives'],receipt
            return receipt
        await run.check('archive_failure_preserves_Spanner_documents',['LIFE-02'],archive_failure)
        async def roundtrip():
            counts=await stores.event_log.expire(90,archive_store=archive)
            archives=await archive.list_archives(limit=10);assert len(archives)==1,archives
            restored=await archive.restore_archive(archives[0]['archive_id'])
            docs=await stores.event_log.get_documents([old['event_id'],fresh['event_id']])
            trim=await stores.event_log.trim(7,[settings.consumer.group_projection])
            housekeeping=await stores.event_log.housekeep(90,168)
            prune=await client.post('/v1/admin/prune',json={'tier':'cold','dry_run':False})
            assert prune.status_code==200,prune.text
            before=await stores.graph.get_nodes([NodeRef('Event',old['event_id'],'event_id')]);assert not before,before
            body='\n'.join(json.dumps(doc) for doc in restored)+'\n'
            imported=await client.post('/v1/events/import',content=body,headers={'content-type':'application/x-ndjson'})
            assert imported.status_code==200,imported.text
            await project()
            after=await stores.event_log.get_documents([old['event_id'],fresh['event_id']])
            graph=await stores.graph.get_nodes([NodeRef('Event',old['event_id'],'event_id')])
            receipt={'expiry':counts,'archives':archives,'archive_documents':restored,'expired_old_document':docs[0],
                     'fresh_kept':docs[1] is not None,'trimmed':trim,'housekeeping':housekeeping,'prune':prune.json(),
                     'import_response':imported.text,'restored_payload':after[0]['payload'] if after[0] else None,
                     'restored_graph_event':bool(graph),'scope':'FS archive recovery via supported ArchiveStore and admin import, then actual projection; no configured GCS target'}
            (run.directory / 'archive-import-recovery.json').write_text(json.dumps(receipt,indent=2))
            assert counts==(1,1) and docs[0] is None and docs[1] is not None,receipt
            assert len(restored)==1 and restored[0]['payload']==old['payload'],receipt
            assert after[0] is not None and after[0]['payload']==old['payload'] and after[1]['payload']==fresh['payload'] and graph,receipt
            return receipt
        await run.check('FS_archive_list_restore_admin_import_and_projection_recovery',['LIFE-02','LIFE-01','ING-05'],roundtrip,timeout_seconds=110)
    await archive.close()


async def ordering_races(run,database,values,credentials):
    from uuid import uuid4
    from context_graph.api.app import create_app,lifespan
    from context_graph.ontology.runtime import configured_projector
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.enrichment import EnrichmentConsumer
    configure(values);app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings()
        async def drain(worker):
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,45)
            finally:worker.stop();await asyncio.wait_for(task,20)
        async def project():
            await drain(ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'races-projection'),stores.event_log,stores.graph,settings,configured_projector(settings.ontology)))
        async def send(row):
            response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
        async def enrich_first():
            await run.reset(database,values)
            row=event('enrichment-first',tool_name='race-tool',importance_hint=7);await send(row)
            class Embed:
                async def embed_text(self,text):return [1.0]+[0.0]*383
            worker=EnrichmentConsumer(stores.subscription(settings.consumer.group_enrichment,'races-enrichment'),stores.event_log,stores.graph,settings,Embed())
            await drain(worker)
            pending_before=await worker._subscription.delivery_counts(100)
            await project()
            ref=NodeRef('Event',row['event_id'],'event_id');node=(await stores.graph.get_nodes([ref]))[ref]
            receipt={'event_id':row['event_id'],'node':node,'enrichment_pending_before_projection':pending_before,
                     'expected_keywords':['observation','input','race-tool'],'expected_embedding_dims':384,
                     'scope':'actual enrichment consumes/ACKs before actual projection; no fake storage'}
            (run.directory / 'enrichment-before-projection.json').write_text(json.dumps(receipt,indent=2))
            assert node['keywords']==receipt['expected_keywords'] and len(node['embedding'])==384,receipt
            return receipt
        await run.check('enrichment_first_preserves_keywords_and_embedding_after_projection',['ENR-01','EXT-03'],enrich_first)
        async def parent_later():
            await run.reset(database,values)
            parent=event('parent-later',event_id=str(uuid4()))
            child=event('parent-later',parent_event_id=parent['event_id'])
            await send(child);await project()
            before=await graph_counts(database)
            await send(parent);await project()
            after=await graph_counts(database)
            expected=[child['event_id'],'CAUSED_BY',parent['event_id']]
            receipt={'child':child,'parent':parent,'before_parent':before,'after_parent':after,'expected':expected,
                     'scope':'child and referenced parent accepted/projected in separate flushes; later endpoint arrival'}
            (run.directory / 'causal-parent-later.json').write_text(json.dumps(receipt,indent=2))
            assert expected in after['edges'],'late causal parent leaves acknowledged child permanently unlinked'
            return receipt
        await run.check('late_causal_parent_repairs_acknowledged_child_edge',['PROJ-01','LED-02'],parent_later)


async def live_pack(run,database,values,credentials):
    from context_graph.api.app import create_app,lifespan
    from context_graph.adapters.llm.client import LLMExtractionClient
    from context_graph.domain.pack_extraction import extraction_profiles
    from context_graph.ontology.runtime import configured_projector
    from context_graph.settings import Settings
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.worker.pack_extraction import PackExtractionConsumer
    await run.reset(database,values);configure(values)
    if not os.environ.get('OPENAI_API_KEY'):raise RuntimeError('configured live provider credential absent; no replacement identity created')
    app=create_app()
    async with lifespan(app),httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://compat') as client:
        stores=app.state.stores;settings=Settings();projector=configured_projector(settings.ontology)
        row=event('live-pack',payload={'content':'Decision: use Spanner native graph to store compatibility evidence, because durable graph relationships are required.'})
        response=await client.post('/v1/events',json=row);assert response.status_code==201,response.text
        async def drain(worker):
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                async def ready():return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(ready,60)
            finally:worker.stop();await asyncio.wait_for(task,20)
        await drain(ProjectionConsumer(stores.subscription(settings.consumer.group_projection,'live-projection'),stores.event_log,stores.graph,settings,projector))
        llm=LLMExtractionClient(model_id=settings.llm.model_id,temperature=settings.llm.temperature,max_tokens=256,timeout=30,max_retries=0)
        calls=[];done=asyncio.Event();original=llm.generate_text
        async def observed(prompt):
            if calls:raise RuntimeError('live smoke call budget exceeded')
            calls.append({'model':settings.llm.model_id,'max_output_tokens':256,'retries':0,'timeout_seconds':30})
            try:
                answer=await original(prompt)
                calls[-1]['answer']=answer
                return answer
            finally:done.set()
        llm.generate_text=observed
        profiles=extraction_profiles(projector.registry,max_nodes=1,max_links=1,max_text_chars=1000)
        worker=PackExtractionConsumer(stores.subscription(settings.consumer.group_pack_extraction,'live-pack-extraction'),stores.event_log,stores.graph,profiles,projector,llm,settings)
        async def scenario():
            await worker.ensure_group();task=asyncio.create_task(worker.run())
            try:
                await asyncio.wait_for(done.wait(),45)
                await asyncio.sleep(1)
            finally:worker.stop();await asyncio.wait_for(task,20)
            counts=await graph_counts(database);pending=await worker._subscription.delivery_counts(100)
            receipt={'calls':calls,'event_id':row['event_id'],'graph':counts,'pending':pending,
                     'scope':'one bounded real configured-model call through Engram PackExtractionConsumer; actual Spanner ledger/graph; local embeddings verified separately; no backend substitution'}
            (run.directory / 'live-pack-extraction.json').write_text(json.dumps(receipt,indent=2))
            assert len(calls)==1 and calls[0].get('answer'),receipt
            assert counts['nodes'].get('Decision',0)==1 and any(e[1]=='DERIVED_FROM' and e[2]==row['event_id'] for e in counts['edges']),receipt
            assert not pending,receipt
            return receipt
        await run.check('real_configured_LLM_pack_proposal_persisted_with_Spanner_evidence',['APP-05','PEXT-01'],scenario,timeout_seconds=80)

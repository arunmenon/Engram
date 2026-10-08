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
            assert len(documents)==7,receipt
            assert not receipt["consumer_pending"],receipt
            return receipt
        await run.check("full_consolidation_timer_centrality_forgetting_orphans_housekeeping",["CONS-01","CONS-02","LIFE-03"],cycle,timeout_seconds=110)

"""Further tracked real-Spanner journeys; no alternate storage runners."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from engram_spanner_compat import ROOT, configure


def event(session="resume", **changes):
    result = dict(event_id=str(uuid4()), event_type="observation.input",
                  occurred_at=datetime.now(UTC).isoformat(), session_id=session,
                  agent_id="compat-resume", trace_id=session, payload_ref="compat:resume",
                  payload={"content": "Spanner recovery evidence"})
    result.update(changes)
    return result


async def wait_until(predicate, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.2)
    raise TimeoutError(f"tracked condition did not complete within {seconds}s")


class Processes:
    """Own every spawned process and retain cleanup receipts, including failures."""
    def __init__(self, run, credentials):
        self.run = run
        self.processes = {}
        self.logs = {}
        self.receipts = []
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.api_key, self.admin_key = uuid4().hex, uuid4().hex
        self.environment = {**os.environ,
                            "ENGRAM_COMPAT_CREDENTIAL_FILE": str(credentials),
                            "ENGRAM_COMPAT_API_PORT": str(self.port),
                            "CG_AUTH_API_KEY": self.api_key, "CG_AUTH_ADMIN_KEY": self.admin_key,
                            "CG_CONSUMER_CLAIM_IDLE_MS": "500",
                            "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}:{ROOT / 'scripts'}", "PYTHONUNBUFFERED": "1"}
        bootstrap = ROOT / "scripts/engram_spanner_process_bootstrap.py"
        (run.directory / "process-bootstrap.py").write_text(bootstrap.read_text())
        self.bootstrap = bootstrap
        self.client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{self.port}",
                                      headers={"Authorization": "Bearer " + self.api_key}, timeout=30)

    def start(self, name, mode="projection", fault=None, gate=None):
        env = {**self.environment, "ENGRAM_COMPAT_PROCESS": mode,
               "ENGRAM_COMPAT_CONSUMER": name}
        if fault:
            env.update(ENGRAM_COMPAT_FAULT=fault,
                       ENGRAM_COMPAT_FAULT_MARKER=str(self.run.directory / f"{name}.marker"))
        if gate:
            env["ENGRAM_COMPAT_READ_GATE"] = str(gate)
        self.logs[name] = (self.run.directory / f"{name}.log").open("w")
        snapshot = self.run.directory / f"{name}-bootstrap.py"
        snapshot.write_bytes(self.bootstrap.read_bytes())
        (self.run.directory / f"{name}-launch.json").write_text(json.dumps({
            "mode": mode, "consumer": name, "fault": fault, "read_gate": str(gate) if gate else None,
            "auth_mode": env.get("ENGRAM_COMPAT_AUTH", "token"),
            "bootstrap_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "claim_idle_ms": env.get("CG_CONSUMER_CLAIM_IDLE_MS")}, indent=2))
        self.processes[name] = subprocess.Popen([sys.executable, str(snapshot)],
                                              cwd=ROOT, env=env, stdout=self.logs[name],
                                              stderr=self.logs[name])

    async def api(self):
        self.start("api", "api")
        async def ready():
            if self.processes["api"].poll() is not None:
                raise RuntimeError("owned API process exited")
            try:
                return (await self.client.get("/v1/health")).status_code == 200
            except httpx.ConnectError:
                return False
        await wait_until(ready)

    async def stop(self, name, kill=False):
        process = self.processes.pop(name)
        if process.poll() is None:
            process.kill() if kill else process.terminate()
            try:
                await asyncio.to_thread(process.wait, 10)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, 10)
        self.logs.pop(name).close()
        self.receipts.append({"name": name, "pid": process.pid, "exit_code": process.returncode,
                              "requested_kill": kill})

    async def close(self):
        for name in list(self.processes):
            await self.stop(name)
        await self.client.aclose()
        (self.run.directory / "process-cleanup.json").write_text(json.dumps(self.receipts, indent=2))


async def graph_counts(database):
    def read():
        with database.snapshot(multi_use=True) as snap:
            return {"nodes": dict(snap.execute_sql("SELECT label, COUNT(*) FROM GraphNodes GROUP BY label")),
                    "edges": list(snap.execute_sql("SELECT src_id, edge_type, dst_id FROM GraphEdges"))}
    return await asyncio.to_thread(read)


async def recovery(run, database, values, credentials):
    """Real process kills, plus explicitly synthetic fault boundaries on real ports."""
    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings
    configure(values)
    os.environ["CG_CONSUMER_CLAIM_IDLE_MS"] = "500"
    settings = Settings()
    stores = await open_stores(settings)
    try:
        for fault in ("before_graph", "before_ack", "transient_once", "permanent_once"):
            await run.reset(database, values)
            owned = Processes(run, credentials)
            try:
                await owned.api()
                data = event("resume-" + fault)
                response = await owned.client.post("/v1/events", json=data)
                assert response.status_code == 201, response.text
                name = "fault-" + fault
                owned.start(name, fault=fault)
                async def marked():
                    if owned.processes[name].poll() is not None:
                        raise RuntimeError("fault worker exited before boundary")
                    return (run.directory / f"{name}.marker").exists()
                await wait_until(marked)
                original_sub = stores.subscription(settings.consumer.group_projection, name)
                position = response.json()["global_position"]

                async def scenario():
                    if fault in ("before_graph", "before_ack"):
                        counts = await graph_counts(database)
                        expected = 0 if fault == "before_graph" else 1
                        assert counts["nodes"].get("Event", 0) == expected, counts
                        assert position in await original_sub.delivery_counts(100)
                        await owned.stop(name, kill=True)
                        await asyncio.sleep(0.7)
                        resumed = "resumed-" + fault
                        owned.start(resumed)
                        probe = stores.subscription(settings.consumer.group_projection, resumed)
                        async def recovered():
                            ready = "pending_drain_completed" in (run.directory / f"{resumed}.log").read_text()
                            return ready and not await probe.lag() and not await probe.delivery_counts(100)
                        await wait_until(recovered)
                    elif fault == "transient_once":
                        async def recovered():
                            return not await original_sub.lag() and not await original_sub.delivery_counts(100)
                        await wait_until(recovered)
                    else:
                        # Once the injected failure is removed, a live worker should retry it.
                        await asyncio.sleep(4)
                        pending = await original_sub.delivery_counts(100)
                        counts = await graph_counts(database)
                        (run.directory / "live-retry-after-fault.json").write_text(
                            json.dumps({"pending": pending, "counts": counts}, indent=2))
                        assert not pending and counts["nodes"].get("Event", 0) == 1, (
                            "removed one-shot non-transient failure remains pending until restart")
                    counts = await graph_counts(database)
                    assert counts["nodes"].get("Event", 0) == 1, counts
                    assert not await original_sub.dead_letters(), "healthy recovery must not dead-letter"
                    lineage = await owned.client.get(f"/v1/nodes/{data['event_id']}/lineage")
                    assert lineage.status_code == 200, lineage.text
                    return {"fault": fault, "synthetic_boundary": True, "counts": counts,
                            "lineage": lineage.json(), "dead_letters": await original_sub.dead_letters()}
                await run.check("process_recovery_" + fault, ["SUB-02", "SUB-03", "OPS-03"], scenario)
            finally:
                await owned.close()
                (run.directory / f"{fault}-cleanup.json").write_text(json.dumps(owned.receipts, indent=2))
    finally:
        await stores.close()


async def combined(run, database, values, credentials):
    """Two real independent packs, imported CRM plus signed PDLC, and HTTP evidence."""
    from tests.unit import test_pack_toy_end_to_end as crm, test_pdlc_end_to_end as pdlc
    from context_graph.adapters.registry import open_stores
    from context_graph.ontology.__main__ import evaluate_graph
    from context_graph.ontology.runtime import configured_projector
    from context_graph.settings import Settings
    await run.reset(database, values)
    configure(values, "pdlc,crm")
    os.environ.update(CG_WEBHOOK_GITHUB_SECRET=pdlc.SECRET, CG_WEBHOOK_JIRA_SECRET=pdlc.SECRET)
    stores = await open_stores(Settings())
    owned = Processes(run, credentials)
    try:
        await owned.api()
        async def ingest():
            body = b"\n".join(json.dumps(e).encode() for e in crm._events())
            response = await owned.client.post("/v1/events/import", content=body,
                                              headers={"Authorization": "Bearer " + owned.admin_key})
            assert response.status_code == 200, response.text
            summary = json.loads(response.text.splitlines()[-1])["summary"]
            assert summary["created"] == len(crm.HISTORY), summary
            for index, (source, kind, fixture) in enumerate(pdlc.DELIVERIES):
                body = (pdlc.FIXTURES / f"{fixture}.json").read_bytes()
                headers = pdlc._headers(source, kind, body, f"combined-{index}")
                response = await owned.client.post(f"/v1/webhooks/{source}", content=body, headers=headers)
                assert response.status_code == 202, response.text
            return {"CRM_import": summary, "PDLC_signed_deliveries": len(pdlc.DELIVERIES)}
        await run.check("combined_CRM_import_and_signed_PDLC", ["ING-05", "APP-03", "APP-04"], ingest)
        owned.start("combined-projection")
        settings = Settings()
        probe = stores.subscription(settings.consumer.group_projection, "combined-projection")
        async def drain():
            async def ready():
                return ("pending_drain_completed" in (run.directory / "combined-projection.log").read_text()
                        and not await probe.lag() and not await probe.delivery_counts(100))
            await wait_until(ready, 90)
            assert await stores.event_log.stream_length() == 19
            return await graph_counts(database)
        await run.check("combined_pack_process_projection", ["APP-04", "PROJ-02", "BOOT-01"], drain)
        async def evaluate():
            registry = configured_projector(settings.ontology).registry
            before = await owned.client.post("/v1/query/artifacts", json={"query": "Acme pipeline", "intent": "pipeline"})
            assert before.status_code == 409, before.text
            reports = await evaluate_graph(settings, stores.graph, registry,
                                           [crm.CRM, pdlc.EVAL_SETS], record=True)
            result = [r.as_dict() for r in reports]
            (run.directory / "combined-evaluation.json").write_text(json.dumps(result, indent=2))
            assert len(reports) == 2 and all(r.passed for r in reports), result
            await crm._check_questions(owned.client)
            await pdlc._check_queries(owned.client)
            context = await owned.client.get("/v1/context/crm:import")
            assert context.status_code == 200 and context.json()["nodes"], context.text
            return {"reports": result, "both_domain_HTTP_questions": "passed", "memory_context": "passed"}
        await run.check("combined_pack_gates_and_HTTP_questions", ["APP-04", "ART-05", "ART-02", "APP-02"], evaluate)
    finally:
        await owned.close()
        await stores.close()


async def concurrency(run, database, values, credentials):
    """Controlled two-replica schedule and multi-page orphan restart on real Spanner."""
    from context_graph.adapters.registry import open_stores
    from context_graph.settings import Settings
    configure(values)
    os.environ.update(CG_CONSUMER_CLAIM_IDLE_MS="500", CG_CONSUMER_PROJECTION_BATCH_SIZE="3")
    settings = Settings()
    stores = await open_stores(settings)
    try:
        await run.reset(database, values)
        owned = Processes(run, credentials)
        try:
            await owned.api()
            async def replicas():
                rows = [event("same-session") for _ in range(3)]
                for index, row in enumerate(rows):
                    if index:
                        row["parent_event_id"] = rows[index - 1]["event_id"]
                a, b = run.directory / "replica-a-gate", run.directory / "replica-b-gate"
                async def send(row):
                    response = await owned.client.post("/v1/events", json=row)
                    assert response.status_code == 201, response.text
                async def projected(n):
                    async def done():
                        return (await graph_counts(database))["nodes"].get("Event", 0) == n
                    await wait_until(done)
                    # Ensure writes AND ACK have completed before another startup can claim.
                    for name in owned.processes:
                        if name != "api":
                            probe = stores.subscription(settings.consumer.group_projection, name)
                            async def acked():
                                return not await probe.delivery_counts(100)
                            await wait_until(acked)
                await send(rows[0]); owned.start("replica-a", gate=a)
                await projected(1)
                await send(rows[1]); owned.start("replica-b", gate=b)
                await projected(2)
                await send(rows[2]); Path(str(a) + ".open").write_text("resume")
                await projected(3)
                actual = await graph_counts(database)
                expected = {(rows[1]["event_id"], "FOLLOWS", rows[0]["event_id"]),
                            (rows[2]["event_id"], "FOLLOWS", rows[1]["event_id"])}
                observed = {tuple(edge) for edge in actual["edges"] if edge[1] == "FOLLOWS"}
                receipt = {"schedule": "A event1, B event2, A event3; both processes alive",
                           "expected": sorted(expected), "actual": sorted(observed),
                           "all_edges": actual["edges"]}
                (run.directory / "replica-lineage.json").write_text(json.dumps(receipt, indent=2))
                assert observed == expected, "same-session FOLLOWS skips another replica's predecessor"
                return receipt
            await run.check("two_replica_same_session_lineage", ["SUB-04", "PROJ-01", "LED-02"], replicas)
        finally:
            await owned.close()
            (run.directory / "replicas-cleanup.json").write_text(json.dumps(owned.receipts, indent=2))
        await run.reset(database, values)
        owned = Processes(run, credentials)
        try:
            await owned.api()
            async def orphan_pages():
                rows = [event("orphan-pages") for _ in range(15)]
                response = await owned.client.post("/v1/events/batch", json={"events": rows})
                assert response.status_code == 201 and response.json()["accepted"] == 15, response.text
                orphan = stores.subscription(settings.consumer.group_projection, "dead-setup-consumer")
                await orphan.ensure_group()
                delivered = await orphan.read_new(15, 0)
                assert len(delivered) == 15
                assert len(await orphan.delivery_counts(100)) == 15
                await asyncio.sleep(0.7)
                owned.start("page-recovery")
                probe = stores.subscription(settings.consumer.group_projection, "page-recovery")
                async def drained():
                    ready = "pending_drain_completed" in (run.directory / "page-recovery.log").read_text()
                    return ready and not await probe.lag() and not await probe.delivery_counts(100)
                await wait_until(drained, 75)
                actual = await graph_counts(database)
                assert actual["nodes"].get("Event", 0) == 15, actual
                assert len([edge for edge in actual["edges"] if edge[1] == "FOLLOWS"]) == 14
                assert not await probe.dead_letters()
                return {"prefilled_deliveries": 15, "worker_batch_size": 3,
                        "setup": "API ingestion; public read_new seeds abandoned deliveries",
                        "node_count": 15, "follows_count": 14, "unread": 0, "pending": 0}
            await run.check("orphan_recovery_multiple_pending_pages", ["SUB-01", "SUB-03", "PROJ-01"], orphan_pages)
        finally:
            await owned.close()
            (run.directory / "orphan-pages-cleanup.json").write_text(json.dumps(owned.receipts, indent=2))
    finally:
        await stores.close()


async def startup(run, database, values, credentials, modes=None):
    """Read-only ordinary ADC and negative token/database/dimension handshakes."""
    for mode in modes or ("adc", "invalid_token", "missing_database", "dimension_mismatch"):
        configure(values)
        private = None
        path = credentials
        if mode == "invalid_token":
            private = Path("/private/tmp") / f"{run.id}-invalid-token-env"
            private.write_text("\n".join(f"{key}={value}" for key, value in
                                        {**values, "GOOGLE_OAUTH_ACCESS_TOKEN": "compat-invalid-token"}.items()))
            private.chmod(0o600)
            path = private
        owned = Processes(run, path)
        if mode == "adc":
            owned.environment["ENGRAM_COMPAT_AUTH"] = "adc"
        if mode == "missing_database":
            owned.environment["CG_SPANNER_DATABASE"] = "engram-compat-intentionally-missing"
        if mode == "dimension_mismatch":
            owned.environment["CG_SPANNER_EMBEDDING_DIMENSIONS"] = "3"
        try:
            async def handshake():
                owned.start("api", "api")
                deadline = time.monotonic() + 40
                served = False
                while time.monotonic() < deadline:
                    if owned.processes["api"].poll() is not None:
                        break
                    try:
                        if (await owned.client.get("/v1/health")).status_code == 200:
                            served = True
                            break
                    except httpx.ConnectError:
                        pass
                    await asyncio.sleep(0.2)
                log = (run.directory / "api.log").read_text(errors="replace")
                (run.directory / f"{mode}-startup.log").write_text(log)
                observation = {"mode": mode, "served_health": served,
                               "exit_code": owned.processes["api"].poll(),
                               "writes": 0, "database_creation": False}
                if mode == "dimension_mismatch":
                    from context_graph.adapters.registry import open_stores
                    from context_graph.settings import Settings
                    await asyncio.to_thread(database.reload)
                    observation["configured_embedding_dimensions"] = 3
                    observation["existing_schema_ddl"] = list(database.ddl_statements)
                    candidate = Settings()
                    candidate.spanner.embedding_dimensions = 3
                    wrong = await open_stores(candidate)
                    try:
                        try:
                            await wrong.vector_index.nearest([1.0, 0.0, 0.0], top_k=1)
                            observation["native_query_error"] = None
                        except Exception as exc:
                            observation["native_query_error"] = {"type": type(exc).__name__,
                                                                 "message": str(exc)}
                    finally:
                        await wrong.close()
                (run.directory / f"{mode}-startup.json").write_text(json.dumps(observation, indent=2))
                if mode == "adc":
                    if not served and "DefaultCredentialsError" in log:
                        raise RuntimeError("ordinary ADC unavailable in this environment; token bootstrap distinct")
                    assert served, "ordinary ADC startup failed; inspect retained log"
                else:
                    assert not served, f"{mode} was accepted and served healthy"
                    assert owned.processes["api"].poll() is not None, "negative startup did not fail within deadline"
                    if mode == "invalid_token":
                        assert "Unauthenticated" in log or "UNAUTHENTICATED" in log, log[-700:]
                return observation
            await run.check("startup_" + mode,
                            ["BOOT-02" if mode in ("adc", "invalid_token") else "BOOT-03", "OPS-03"],
                            handshake, timeout_seconds=60)
            if mode == "adc" and "ordinary ADC unavailable" in run.checks[-1].get("error", ""):
                run.checks[-1]["verdict"] = "blocked"
        finally:
            await owned.close()
            (run.directory / f"{mode}-cleanup.json").write_text(json.dumps(owned.receipts, indent=2))
            if private:
                private.unlink(missing_ok=True)


async def endpoints(run, database, values, credentials):
    """API pagination/channel checks and native vector contract diagnostics."""
    from context_graph.api.app import create_app, lifespan
    from context_graph.domain.models import EntityNode, EntityType
    from context_graph.ontology.runtime import configured_projector
    from context_graph.worker.projection import ProjectionConsumer
    from context_graph.settings import Settings
    await run.reset(database, values)
    configure(values)
    app = create_app()
    async with lifespan(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://compat"
    ) as client:
        stores = app.state.stores
        settings = Settings()
        stamp = datetime.now(UTC).isoformat()
        rows = [event("tied-context", occurred_at=stamp,
                      payload={"content": f"Spanner migration {i} नमस्ते", "nested": [None, True, 0.125]})
                for i in range(7)]
        for index in range(1, len(rows)):
            rows[index]["parent_event_id"] = rows[index-1]["event_id"]
        async def ingest():
            response = await client.post("/v1/events/batch", json={"events": rows})
            assert response.status_code == 201 and response.json()["accepted"] == 7
            worker = ProjectionConsumer(stores.subscription(settings.consumer.group_projection, "endpoint-worker"),
                                        stores.event_log, stores.graph, settings,
                                        configured_projector(settings.ontology))
            await worker.ensure_group()
            task = asyncio.create_task(worker.run())
            try:
                async def drained():
                    return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                await wait_until(drained)
            finally:
                worker.stop()
                await asyncio.wait_for(task, 20)
            docs = await stores.event_log.get_documents([row["event_id"] for row in rows])
            assert [d["payload"] for d in docs] == [row["payload"] for row in rows]
            return {"tied_occurrence_events": 7, "lossless_nested_JSON": True}
        await run.check("tied_event_projection_and_JSON", ["LED-01", "PROJ-01", "ING-02"], ingest)

        async def context():
            missing = await client.get("/v1/context/no-such-session")
            assert missing.status_code == 200 and not missing.json()["nodes"]
            seen = set(); cursor = None; pages = []
            for _ in range(8):
                params = {"max_nodes": 2}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get("/v1/context/tied-context", params=params)
                assert response.status_code == 200, response.text
                body = response.json(); ids = set(body["nodes"])
                assert len(ids) <= 2 and not (seen & ids), "pagination repeats a tied event"
                seen |= ids; pages.append(body)
                cursor = body["pagination"]["cursor"]
                if not body["pagination"]["has_more"]:
                    break
                assert cursor
            (run.directory / "context-pages.json").write_text(json.dumps(pages, indent=2))
            assert seen == {row["event_id"] for row in rows}, "context pagination misses tied events"
            for params in ({"max_nodes": 0}, {"max_nodes": 501}, {"max_depth": 11}):
                assert (await client.get("/v1/context/tied-context", params=params)).status_code == 422
            return {"pages": len(pages), "unique_events": len(seen), "empty_and_bounds": "passed"}
        await run.check("context_tied_keyset_pages_empty_and_bounds", ["MEM-01", "MEM-05"], context)

        async def lineage():
            missing = await client.get("/v1/nodes/missing/lineage")
            assert missing.status_code == 200 and not missing.json()["nodes"]
            result = await client.get(f"/v1/nodes/{rows[-1]['event_id']}/lineage",
                                      params={"max_depth": 10, "max_nodes": 3})
            assert result.status_code == 200, result.text
            body = result.json()
            (run.directory / "bounded-lineage.json").write_text(json.dumps(body, indent=2))
            assert len(body["nodes"]) <= 3, "lineage max_nodes does not bound unique nodes"
            assert body["nodes"], "known causal chain is empty"
            assert (await client.get(f"/v1/nodes/{rows[-1]['event_id']}/lineage",
                                     params={"max_depth": 11})).status_code == 422
            return body
        await run.check("lineage_node_depth_bounds_and_missing", ["MEM-02", "MEM-05"], lineage)

        async def lineage_pages():
            seen = set(); cursor = None; pages = []
            for _ in range(8):
                params = {"max_depth": 10, "max_nodes": 2}
                if cursor:
                    params["cursor"] = cursor
                response = await client.get(f"/v1/nodes/{rows[-1]['event_id']}/lineage", params=params)
                assert response.status_code == 200, response.text
                body = response.json(); pages.append(body); seen |= set(body["nodes"])
                if not body["pagination"]["has_more"]:
                    break
                next_cursor = body["pagination"]["cursor"]
                assert next_cursor and next_cursor != cursor
                cursor = next_cursor
            (run.directory / "lineage-pages.json").write_text(json.dumps(pages, indent=2))
            assert seen == {row["event_id"] for row in rows}, "lineage pagination ends before visiting the full causal chain"
            return {"pages": len(pages), "unique_nodes": len(seen)}
        await run.check("lineage_pages_complete_causal_chain", ["MEM-02", "MEM-05"], lineage_pages)

        async def vector_contract():
            from context_graph.domain.models import Edge, EdgeType
            vector = [1.0] + [0.0]*383
            pairs = [("self", vector), ("near", [0.8,0.6]+[0.0]*382),
                     ("orthogonal", [0.0,1.0]+[0.0]*382), ("opposite", [-1.0]+[0.0]*383)]
            for name, embedding in pairs:
                await stores.graph.merge_entity_node(EntityNode(
                    entity_id="entity:compat-"+name, name=name, entity_type=EntityType.CONCEPT,
                    first_seen=datetime.now(UTC), last_seen=datetime.now(UTC), embedding=embedding))
            await stores.graph.create_edges_batch([
                Edge(source=rows[0]["event_id"], target="entity:compat-self", edge_type=EdgeType.REFERENCES),
                Edge(source=rows[1]["event_id"], target="entity:compat-near", edge_type=EdgeType.REFERENCES)])
            hits = await stores.vector_index.nearest(vector, top_k=2, threshold=0.75)
            result = [{"id": h.id, "score": h.score, "rank": h.rank} for h in hits]
            (run.directory / "native-vector-topk.json").write_text(json.dumps(result, indent=2))
            assert [h.id for h in hits] == ["entity:compat-self", "entity:compat-near"], result
            assert all(0 <= h.score <= 1 for h in hits)
            assert len(await stores.vector_index.nearest(vector, top_k=4, threshold=0.99)) == 1
            return {"native_force_index": True, "seed_setup": "four public graph-port Entity writes",
                    "dimensions": 384, "topk": result, "threshold": "passed"}
        await run.check("native_ANN_multivector_topk_threshold", ["SEARCH-02"], vector_contract)

        async def channels():
            engine = app.state.retrieval
            embed, keyword, vector_index = engine._embedding_service, engine._keyword_index, engine._vector_index
            class FixedEmbedding:
                async def embed_text(self, text):
                    return [1.0]+[0.0]*383
            answers = {}
            try:
                for mode in ("graph", "keyword", "vector", "combined"):
                    engine._embedding_service = FixedEmbedding() if mode in ("vector", "combined") else None
                    engine._keyword_index = keyword if mode in ("keyword", "combined") else None
                    engine._vector_index = vector_index if mode in ("vector", "combined") else None
                    payload = dict(query="Spanner migration", session_id="tied-context", agent_id="compat",
                                   max_nodes=10, max_depth=2)
                    if mode == "graph":
                        payload["seed_nodes"] = [rows[0]["event_id"]]
                    if mode in ("keyword", "vector"):
                        payload["session_id"] = "missing-graph-session"
                    response = await client.post("/v1/query/subgraph", json=payload)
                    assert response.status_code == 200, response.text
                    body = response.json(); answers[mode] = body
                    (run.directory / "retrieval-channels.json").write_text(json.dumps(answers, indent=2))
                    # Keyword-only uses the real session filter; the absent session is intentionally empty.
                    if mode != "keyword":
                        assert body["nodes"], f"{mode} channel returned no nodes"
                    if mode == "vector":
                        assert body["meta"]["retrieval_channels"].get("vector", 0)>0
                (run.directory / "retrieval-channels.json").write_text(json.dumps(answers, indent=2))
                return {mode: answer["meta"]["retrieval_channels"] for mode, answer in answers.items()}
            finally:
                engine._embedding_service, engine._keyword_index, engine._vector_index = embed, keyword, vector_index
        await run.check("HTTP_graph_vector_combined_and_empty_keyword_filter", ["MEM-03", "SEARCH-01", "SEARCH-02"], channels)

        async def feedback_failure():
            from context_graph.ports.pack_graph import NodeRef
            graph = stores.graph
            refs = [NodeRef("Event", row["event_id"], "event_id") for row in rows[:2]]
            before_nodes = await graph.get_nodes(refs)
            before_log = await stores.event_log.stream_length()
            original = graph.adjust_node_importance
            calls = 0
            async def injected(**kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    from context_graph.ports.errors import UnavailableError
                    raise UnavailableError("controlled second feedback write failure")
                return await original(**kwargs)
            graph.adjust_node_importance = injected
            payload = {"query_id": "resume-partial-feedback", "session_id": "tied-context",
                       "helpful_node_ids": [row["event_id"] for row in rows[:2]], "irrelevant_node_ids": []}
            try:
                first = await client.post("/v1/feedback", json=payload)
            finally:
                graph.adjust_node_importance = original
            after_first = await graph.get_nodes(refs)
            assert first.status_code == 500 and await stores.event_log.stream_length() == before_log+1
            retry = await client.post("/v1/feedback", json=payload)
            assert retry.status_code == 201 and await stores.event_log.stream_length() == before_log+2
            after_retry = await graph.get_nodes(refs)
            result = {"fault": "synthetic second importance adjustment", "first_status": first.status_code,
                      "retry_status": retry.status_code, "ledger_audit_delta": 2,
                      "before": [before_nodes[r] for r in refs],
                      "after_failure": [after_first[r] for r in refs],
                      "after_retry": [after_retry[r] for r in refs],
                      "semantics": "partial graph update survives500; retry is a new audit and repeats updates"}
            (run.directory / "feedback-partial-failure.json").write_text(json.dumps(result, indent=2))
            return result
        await run.check("feedback_ledger_success_graph_partial_failure_retry_semantics", ["FB-02"], feedback_failure)


async def vector_isolation(run, database, values, credentials):
    """Retain the populated endpoint fixture; isolate graph/keyword seed channels."""
    from context_graph.api.app import create_app, lifespan
    configure(values)
    app = create_app()
    async with lifespan(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://compat"
    ) as client:
        async def scenario():
            engine = app.state.retrieval
            original_seed = engine._get_graph_seeds
            original_embed, original_keyword = engine._embedding_service, engine._keyword_index
            class FixedEmbedding:
                async def embed_text(self, text):
                    return [1.0]+[0.0]*383
            async def no_graph_seeds(*args, **kwargs):
                return []
            persisted = await graph_counts(database)
            assert any(edge[1:] == ["REFERENCES", "entity:compat-self"] for edge in persisted["edges"])
            engine._embedding_service = FixedEmbedding()
            engine._keyword_index = None
            engine._get_graph_seeds = no_graph_seeds
            try:
                response = await client.post("/v1/query/subgraph", json=dict(
                    query="Spanner migration", session_id="tied-context", agent_id="compat", max_nodes=10))
                assert response.status_code == 200, response.text
                body = response.json()
                receipt = {"setup": "same existing session; graph seed stage returns empty; keyword disabled; real ANN",
                           "persisted": persisted, "response": body}
                (run.directory / "vector-only-existing-session.json").write_text(json.dumps(receipt, indent=2))
                assert body["meta"]["retrieval_channels"].get("vector", 0)>0
                assert body["nodes"], "native ANN entity hits and reference evidence are discarded by vector-only API retrieval"
                return receipt
            finally:
                engine._get_graph_seeds = original_seed
                engine._embedding_service, engine._keyword_index = original_embed, original_keyword
        await run.check("HTTP_vector_only_existing_session_with_reference_evidence", ["MEM-03", "SEARCH-02"], scenario)


async def upgrade_failures(run, database, values, credentials):
    """Actual pack reconcile and two-Spanner rebuild, with explicit fault/expiry setup."""
    import tempfile
    from tests.unit import test_pack_versioning as fixture
    from context_graph.adapters.registry import open_stores
    from context_graph.api.app import create_app, lifespan
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.ontology.versioning import reconcile, read_state, OntologyChangeRefusedError
    from context_graph.ontology.__main__ import run_rebuild
    from context_graph.settings import Settings
    from context_graph.ports.pack_graph import NodeRef
    from context_graph.worker.projection import ProjectionConsumer
    await run.reset(database, values)
    configure(values, "demo")
    with tempfile.TemporaryDirectory(prefix="engram-compat-demo-") as directory:
        path = Path(directory)
        (path / "demo.pack.yaml").write_text(fixture.DEMO)
        (run.directory / "demo-v1.pack.yaml").write_text(fixture.DEMO)
        os.environ["CG_ONTOLOGY_PACK_DIRS"] = str(path)
        app = create_app()
        async with lifespan(app), httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://compat"
        ) as client:
            stores = app.state.stores; settings = Settings()
            trusted = frozenset(settings.ontology.trusted_sources)
            projector = PackProjector(app.state.ontology, trusted)
            def variant(**replacements):
                demo = next(pack for pack in fixture._registry(**replacements).packs if pack.name == "demo")
                return OntologyRegistry([pack for pack in app.state.ontology.packs if pack.name != "demo"]+[demo])
            ref = NodeRef("Ticket", "Ticket:jira|1")
            async def initial():
                row = event("demo-upgrade", event_type="demo.ticket.opened",
                            occurred_at=(datetime.now(UTC)-timedelta(days=100)).isoformat(),
                            payload={"tracker":"jira", "number":1, "title":"old title", "summary":"new title"})
                response = await client.post("/v1/events/import", content=json.dumps(row).encode())
                assert response.status_code == 200 and json.loads(response.text.splitlines()[-1])["summary"]["created"] == 1
                plan = await reconcile(stores.graph, stores.event_log, projector,
                                       allow_breaking=False, batch_size=10, lookup_limit=100)
                assert plan.kind == "initial"
                worker = ProjectionConsumer(stores.subscription(settings.consumer.group_projection,"upgrade"),
                                            stores.event_log, stores.graph, settings, projector)
                await worker.ensure_group(); task=asyncio.create_task(worker.run())
                try:
                    async def drained():
                        return not await worker._subscription.lag() and not await worker._subscription.delivery_counts(100)
                    await wait_until(drained)
                finally:
                    worker.stop(); await asyncio.wait_for(task,20)
                nodes = await stores.graph.get_nodes([ref])
                assert nodes[ref]["title"] == "old title", nodes
                return {"initial_kind":plan.kind,"historical_API_import":True,"ticket":nodes[ref]}
            await run.check("custom_pack_initial_import_projection", ["ONT-02","PROJ-02","ING-05"],initial)

            additive = variant(**{"version: 1.0.0":"version: 1.1.0",
                                            "sha: string}":"sha: string, author: string}"})
            async def additions_and_refusals():
                plan=await reconcile(stores.graph, stores.event_log, PackProjector(additive, trusted),
                                     allow_breaking=False,batch_size=10,lookup_limit=100)
                assert plan.kind == "additive"
                refusals=[]
                for registry in [variant(**{"set: {title: $.title}":"set: {title: $.summary}"}),
                                 variant(**{"version: 1.0.0":"version: 1.2.0", "number: int":"number: string"})]:
                    try:
                        await reconcile(stores.graph,stores.event_log,PackProjector(registry, trusted),
                                        allow_breaking=False,batch_size=10,lookup_limit=100)
                    except OntologyChangeRefusedError as exc:
                        refusals.append(str(exc))
                    else:
                        raise AssertionError("unbumped/downgraded or breaking version was not refused")
                assert (await read_state(stores.graph)).version == additive.version
                return {"additive":plan.as_dict(),"refusals":refusals}
            await run.check("additive_upgrade_and_version_breaking_refusals",["ONT-02"],additions_and_refusals)

            mapping=variant(**{"version: 1.0.0":"version: 1.2.0",
                                         "sha: string}":"sha: string, author: string}",
                                         "set: {title: $.title}":"set: {title: $.summary}"})
            async def mapping_retry():
                original=stores.graph.upsert_nodes
                async def fail_ticket(writes):
                    if any(write.ref.label == "Ticket" for write in writes):
                        raise ValueError("controlled replay projection-write failure")
                    return await original(writes)
                stores.graph.upsert_nodes=fail_ticket
                try:
                    first=await reconcile(stores.graph,stores.event_log,PackProjector(mapping, trusted),
                                          allow_breaking=False,batch_size=10,lookup_limit=100)
                finally:
                    stores.graph.upsert_nodes=original
                state=await read_state(stores.graph)
                second=await reconcile(stores.graph,stores.event_log,PackProjector(mapping, trusted),
                                       allow_breaking=False,batch_size=10,lookup_limit=100)
                nodes=await stores.graph.get_nodes([ref])
                receipt={"first":first.as_dict(),"second":second.as_dict(),"state":state.properties,
                         "ticket":nodes[ref],"fault":"synthetic Ticket replay write; removed before retry"}
                (run.directory / "mapping-failure-retry.json").write_text(json.dumps(receipt,indent=2))
                assert nodes[ref]["title"] == "new title", "failed mapping replay recorded complete; retry does not repair"
                return receipt
            await run.check("mapping_replay_failure_retries_after_fault_removed",["ONT-02"],mapping_retry)

            async def refuse_target():
                candidate=settings.model_copy(update={"spanner":settings.spanner.model_copy(update={"database":"engram-compat-target"})})
                assert os.environ.get("ENGRAM_COMPAT_TARGET_DATABASE") == "engram-compat-target"
                target=await open_stores(candidate)
                try:
                    before=await graph_counts(target.event_log.database)
                    assert sum(before["nodes"].values())>0, "target-refusal fixture must be populated"
                    code=await run_rebuild(settings,candidate,[],skip_gate=False,force=False)
                    after=await graph_counts(target.event_log.database)
                    assert code != 0 and before==after, "incompatible live target was not preserved/refused"
                    return {"exit_code":code,"before":before,"after":after}
                finally:
                    await target.close()
            await run.check("rebuild_refuses_populated_incompatible_target",["ONT-03"],refuse_target)

            async def missing_rebuild():
                assert os.environ.get("ENGRAM_COMPAT_TARGET_DATABASE") == "engram-compat-target"
                candidate=settings.model_copy(update={"spanner":settings.spanner.model_copy(update={"database":"engram-compat-target"})})
                target=await open_stores(candidate)
                try:
                    db=target.event_log.database
                    assert db.database_id == "engram-compat-target" and values["GOOGLE_CLOUD_PROJECT"]=="portiq-mvp" and values["SPANNER_INSTANCE_ID"]=="engram-experiment"
                    from engram_spanner_compat import TABLES
                    for table in TABLES:
                        changed=await asyncio.to_thread(db.execute_partitioned_dml,f"DELETE FROM {table} WHERE TRUE")
                        run.resets.append({"database":"engram-compat-target","table":table,"rows":changed})
                finally:
                    await target.close()
                expired, archived=await stores.event_log.expire(1)
                assert expired==1 and archived==0
                assert await stores.event_log.stream_length()==1
                code=await run_rebuild(settings,candidate,[],skip_gate=False,force=False)
                target=await open_stores(candidate)
                try:
                    state=await read_state(target.graph)
                    receipt={"source_document_expired_via_public_port":expired,"source_ledger":1,
                             "exit_code":code,"target_state":state.properties if state else None,
                             "target_counts":await graph_counts(target.event_log.database)}
                    (run.directory / "missing-document-rebuild.json").write_text(json.dumps(receipt,indent=2))
                    assert code != 0, "rebuild with missing historical document falsely returns success"
                    return receipt
                finally:
                    await target.close()
            await run.check("real_target_rebuild_missing_document_fails_closed",["ONT-03","LIFE-02"],missing_rebuild)


async def shutdown(run, database, values, credentials):
    """Observe real API lifecycle SDK cleanup; manually close owned SDK after observing."""
    from context_graph.api.app import create_app, lifespan
    from google.cloud.spanner_v1.database_sessions_manager import DatabaseSessionsManager
    # Only shorten the SDK's local termination polling for bounded test cleanup;
    # runtime store close registration and all cloud operations remain unchanged.
    original_poll=DatabaseSessionsManager._MAINTENANCE_THREAD_POLLING_INTERVAL
    DatabaseSessionsManager._MAINTENANCE_THREAD_POLLING_INTERVAL=timedelta(seconds=0.2)
    configure(values)
    app = create_app()
    owned = None
    original = None
    calls = 0
    try:
        async def scenario():
            nonlocal owned, original, calls
            async with lifespan(app), httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://compat") as client:
                owned=app.state.stores.event_log.database
                original=owned.close
                def observed_close():
                    nonlocal calls
                    calls+=1
                    return original()
                owned.close=observed_close
                assert (await client.get("/v1/health")).status_code == 200
                backends=app.state.stores.backends
                closers=len(app.state.stores._closers)
            manager=owned.sessions_manager
            thread=getattr(manager,"_multiplexed_session_thread",None)
            receipt={"registered_closers":closers,"database_close_calls_after_app_shutdown":calls,
                     "test_only_SDK_cleanup_poll_seconds":0.2,
                     "backends":backends,"SDK_session_retained":getattr(manager,"_multiplexed_session",None) is not None,
                     "SDK_background_thread_alive":bool(thread and thread.is_alive())}
            (run.directory / "SDK-shutdown.json").write_text(json.dumps(receipt,indent=2))
            assert calls>0, "Spanner database/session manager is not released by API shutdown"
            assert not receipt["SDK_background_thread_alive"]
            return receipt
        await run.check("API_lifecycle_releases_owned_Spanner_session_manager",["BOOT-01"],scenario)
    finally:
        if owned and original:
            owned.close=original
            await asyncio.to_thread(original)
            (run.directory / "SDK-manual-cleanup.json").write_text(json.dumps({"owned_database_closed_by_harness":True}))
        DatabaseSessionsManager._MAINTENANCE_THREAD_POLLING_INTERVAL=original_poll


async def JSON_boundaries(run, database, values, credentials):
    """Valid application JSON must not collide with the Spanner float marker."""
    from context_graph.api.app import create_app, lifespan
    await run.reset(database,values)
    configure(values)
    app=create_app()
    async with lifespan(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url="http://compat") as client:
        for name,value in [("numeric_tag","0.125"),("text_tag","ordinary-text")]:
            async def scenario():
                row=event("JSON-tags",payload={"content":"marker collision", "literal_object":{"$float":value}})
                response=await client.post("/v1/events",json=row)
                assert response.status_code == 201,response.text
                stored=None; error=None
                try:
                    (stored,)=await app.state.stores.event_log.get_documents([row["event_id"]])
                except Exception as exc:
                    error={"type":type(exc).__name__,"message":str(exc)}
                receipt={"event_id":row["event_id"],"ingestion_status":response.status_code,
                         "expected_payload":row["payload"],"stored_payload":stored.get("payload") if stored else None,
                         "read_error":error}
                (run.directory / f"{name}.json").write_text(json.dumps(receipt,indent=2))
                assert error is None, "accepted ordinary JSON marker makes the ledger document unreadable"
                assert stored["payload"]==row["payload"], "Spanner float marker changes an ordinary JSON object into a number"
                return receipt
            await run.check("JSON_literal_float_marker_"+name,["LED-01"],scenario)

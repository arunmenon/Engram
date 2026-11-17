"""Further tracked real-Spanner journeys; no alternate storage runners."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
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
                            "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}", "PYTHONUNBUFFERED": "1"}
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
        self.processes[name] = subprocess.Popen([sys.executable, str(self.bootstrap)],
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


async def startup(run, database, values, credentials):
    """Read-only ordinary ADC and negative token/database/dimension handshakes."""
    for mode in ("adc", "invalid_token", "missing_database", "dimension_mismatch"):
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
                    observation["configured_embedding_dimensions"] = 3
                    observation["existing_schema_ddl"] = list(database.ddl_statements)
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

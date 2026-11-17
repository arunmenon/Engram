"""Test-only token/provider bootstrap around ordinary Engram process entry points."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from engram_spanner_compat import load_credentials
from google.cloud import spanner
from google.oauth2.credentials import Credentials


class ScriptedProvider:
    def __init__(self, **kwargs):
        pass

    async def extract_from_session(self, **kwargs):
        return {
            "persona": {"name": "Process User", "tech_level": "advanced"},
            "entities": [{"name": "Spanner", "entity_type": "technology"}],
            "preferences": [],
            "skills": [{"skill_id": "skill:process-python", "name": "Python"}],
            "interests": [],
        }

    async def generate_text(self, prompt):
        return '{"links": []}'

    async def verify_entailment(self, **kwargs):
        return True


def main():
    if os.environ.get("ENGRAM_COMPAT_AUTH", "token") == "token":
        values = load_credentials(Path(os.environ["ENGRAM_COMPAT_CREDENTIAL_FILE"]))
        original = spanner.Client
        credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

        def authenticated_client(*args, **kwargs):
            kwargs["credentials"] = credentials
            return original(*args, **kwargs)

        spanner.Client = authenticated_client
    import context_graph.adapters.llm.client as llm

    llm.LLMExtractionClient = ScriptedProvider
    mode = os.environ["ENGRAM_COMPAT_PROCESS"]
    if mode == "api":
        import uvicorn

        uvicorn.run(
            "context_graph.api.app:create_app",
            factory=True,
            host="127.0.0.1",
            port=int(os.environ["ENGRAM_COMPAT_API_PORT"]),
            log_level="warning",
        )
    else:
        import context_graph.worker.__main__ as entry

        # Controlled test-only boundaries around real worker/storage calls.
        # The cloud service, queues and graph writes remain real Spanner.
        consumer = os.environ.get("ENGRAM_COMPAT_CONSUMER")
        if consumer:
            field, _ = entry.CONSUMER_SUBSCRIPTIONS[mode]
            entry.CONSUMER_SUBSCRIPTIONS[mode] = (field, consumer)
        gate = os.environ.get("ENGRAM_COMPAT_READ_GATE")
        if gate:
            from context_graph.adapters.spanner.subscription import SpannerSubscription
            read_new = SpannerSubscription.read_new
            read_once = False

            async def gated_read(self, count, block_ms):
                nonlocal read_once
                if read_once:
                    while not Path(gate + ".open").exists():
                        await asyncio.sleep(0.05)
                deliveries = await read_new(self, count, block_ms)
                if deliveries:
                    read_once = True
                    Path(gate + ".ready").write_text("delivered")
                return deliveries
            SpannerSubscription.read_new = gated_read
        fault = os.environ.get("ENGRAM_COMPAT_FAULT")
        marker = os.environ.get("ENGRAM_COMPAT_FAULT_MARKER")
        if fault:
            from context_graph.adapters.spanner.graph import SpannerGraphStore
            from context_graph.adapters.spanner.subscription import SpannerSubscription
            fired = False
            graph_write = SpannerGraphStore.merge_event_nodes_batch
            ack = SpannerSubscription.ack

            async def inject():
                nonlocal fired
                if fired:
                    return
                fired = True
                if marker:
                    Path(marker).write_text(fault)
                if fault in ("before_graph", "before_ack"):
                    await asyncio.Event().wait()
                if fault == "transient_once":
                    from context_graph.ports.errors import UnavailableError
                    raise UnavailableError("controlled test-only transient write failure")
                if fault == "permanent_once":
                    raise ValueError("controlled test-only permanent write failure")

            async def controlled_graph(self, nodes):
                if fault != "before_ack":
                    await inject()
                return await graph_write(self, nodes)

            async def controlled_ack(self, *positions):
                if fault == "before_ack":
                    await inject()
                return await ack(self, *positions)

            SpannerGraphStore.merge_event_nodes_batch = controlled_graph
            SpannerSubscription.ack = controlled_ack

        asyncio.run(entry.run_worker(mode))


if __name__ == "__main__":
    main()

"""Bounded run-owned ANN fixtures; SQL only supplies historical negative rows."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
from uuid import uuid4


async def verify_entity_ann(database, dimensions, evidence, checks, directory):
    from google.cloud.spanner_v1 import param_types

    from context_graph.adapters.composed_reads import (
        ComposedGraphReads,
        ComposedReadView,
        ReadScope,
    )
    from context_graph.adapters.search import GraphVectorIndex
    from context_graph.adapters.spanner.commits import CommitBudget
    from context_graph.adapters.spanner.graph import SpannerGraphStore
    from context_graph.adapters.spanner.log import json_param
    from context_graph.domain.pack_bundle import resolve_bundle
    from context_graph.ontology.loader import load_registry
    from context_graph.retrieval.engine import RetrievalEngine
    from context_graph.settings import DecaySettings

    prefix = "ann44_" + uuid4().hex
    rng = random.Random(prefix)
    query = [rng.uniform(-1, 1) for _ in range(dimensions)]
    entity_ids = [prefix + "_entity0", prefix + "_entity1"]
    event_ids = [prefix + "_evidence0", prefix + "_evidence1"]
    entity_keys = [("Entity", key) for key in entity_ids]
    entity_vectors = []
    for offset in (0.03, 0.05):
        vector = list(query)
        vector[0] += offset
        entity_vectors.append(vector)
    event_keys = [("Event", key) for key in event_ids] + [("Event", entity_ids[0])]
    # The same raw ID occurs in an Event and Entity. All distractors carry
    # canonical-looking entity_id too, so post-result identity filtering alone
    # cannot make a broad mixed-label ANN corpus pass this experiment.
    negatives = [("Event", entity_ids[0])] + [
        ("Change" if i % 2 else "UserProfile", prefix + f"_negative{i}") for i in range(64)
    ]
    owned_keys = list(dict.fromkeys(entity_keys + event_keys + negatives))
    owned_edges = [
        (("Event", event), "REFERENCES", ("Entity", entity))
        for event, entity in zip(event_ids, entity_ids, strict=True)
    ]
    graph = SpannerGraphStore(
        database,
        embedding_dimensions=dimensions,
        commit_budget=CommitBudget(max_mutations=70, max_bytes=100_000),
    )
    assert await graph._get_nodes(owned_keys) == {}, "run-owned fixture collision"
    evidence["ann_fixture"] = {
        "prefix": prefix,
        "owned_keys": owned_keys,
        "owned_edges": owned_edges,
        "query_dimensions": dimensions,
        "query": query,
        "entity_vectors": entity_vectors,
        "query_sha256": hashlib.sha256(json.dumps(query).encode()).hexdigest(),
        "negative_rows": len(negatives),
        "top_k": 2,
    }
    # Persist ownership and expected values before the first fixture write,
    # including if a process dies before its finally cleanup runs.
    with (directory / "ann-fixture.json").open("w") as stream:
        json.dump(evidence["ann_fixture"], stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    trace = []
    original_query = graph._query

    async def traced_query(sql, params=None, types=None):
        trace.append({"sql": sql, "top_k": (params or {}).get("top_k")})
        return await original_query(sql, params, types)

    graph._query = traced_query
    edge_sql = (
        "SELECT src_label, src_id, edge_type, dst_label, dst_id, props FROM GraphEdges "
        "ORDER BY src_label, src_id, edge_type, dst_label, dst_id"
    )
    original_edges = await graph._query(edge_sql)
    evidence["ann_before_edges_sha256"] = hashlib.sha256(
        json.dumps(original_edges, sort_keys=True, default=str).encode()
    ).hexdigest()
    try:
        await graph._upsert_nodes(
            [
                (key, {"entity_id": key[1], "name": key[1], "embedding": vector})
                for key, vector in zip(entity_keys, entity_vectors, strict=True)
            ]
            + [
                (
                    key,
                    {
                        "event_id": key[1],
                        "session_id": prefix,
                        "occurred_at": "2026-10-07T00:00:00Z",
                    },
                )
                for key in event_keys
            ]
        )
        await graph._upsert_edges([(key, {}) for key in owned_edges])

        # These are historical/direct-write negative fixtures, deliberately
        # bypassing today's Entity-only embedding-column writer.
        def inject():
            with database.batch() as batch:
                batch.insert_or_update(
                    "GraphNodes",
                    ["label", "node_id", "props", "embedding"],
                    [
                        [
                            label,
                            key,
                            json_param(
                                {
                                    "entity_id": key,
                                    **({"event_id": key} if label == "Event" else {}),
                                }
                            ),
                            query,
                        ]
                        for label, key in negatives
                    ],
                )

        await asyncio.to_thread(inject)
        membership = await graph._query(
            "SELECT label, node_id, entity_embedding_member FROM GraphNodes "
            "WHERE STARTS_WITH(node_id, @prefix)",
            {"prefix": prefix},
            {"prefix": param_types.STRING},
        )
        evidence["ann_membership"] = membership
        assert len(membership) == len(owned_keys)
        assert all(
            member is True if label == "Entity" else member is None
            for label, _key, member in membership
        )
        exact = await graph._query(
            "SELECT node_id, COSINE_DISTANCE(embedding, @query) AS distance FROM GraphNodes "
            "WHERE label = 'Entity' AND embedding IS NOT NULL ORDER BY distance LIMIT @top_k",
            {"query": query, "top_k": 2},
            {"query": param_types.Array(param_types.FLOAT64), "top_k": param_types.INT64},
        )
        evidence["ann_exact_entity_baseline"] = exact
        assert {key for key, _distance in exact} == set(entity_ids)
        assert all(distance > 0 for _key, distance in exact), (
            "negative vectors must be strictly closer"
        )
        port = GraphVectorIndex(graph)
        hits = await port.nearest(query, top_k=2, threshold=0.99)
        evidence["ann_initial_hits"] = [{"id": hit.id, "score": hit.score} for hit in hits]
        assert {hit.id for hit in hits} == set(entity_ids), "non-Entity corpus crowded ANN results"
        checks.append(
            {
                "name": "native ANN excludes 65 embedded non-Entity rows before top-k",
                "passed": True,
                "scenarios": [],
            }
        )

        bundle = resolve_bundle(load_registry(["pdlc"], builtin_packs=[]))
        selected = ComposedReadView(graph, ReadScope.from_bundle(bundle))
        engine = RetrievalEngine(
            ComposedGraphReads(selected),
            decay=DecaySettings(),
            bundle=bundle,
            pack_graph=selected,
            vector_index=port,
        )
        seeds = await engine._get_vector_seeds(query, 2)
        evidence["ann_event_seeds"] = seeds
        assert {key for key, _score in seeds} == set(event_ids), (
            "vector seeds confused Entity/Event IDs"
        )
        checks.append(
            {
                "name": "Engram vector Entity hits resolve to correct evidence Events",
                "passed": True,
                "scenarios": [],
            }
        )

        restarted = GraphVectorIndex(SpannerGraphStore(database, embedding_dimensions=dimensions))
        assert {hit.id for hit in await restarted.nearest(query, top_k=2, threshold=0.99)} == set(
            entity_ids
        )
        checks.append(
            {
                "name": "reconstructed adapter reads the filtered index",
                "passed": True,
                "scenarios": [],
            }
        )
        await graph._upsert_nodes([(entity_keys[0], {"embedding": [-v for v in query]})])
        updated = await port.nearest(query, top_k=2, threshold=0.99)
        evidence["ann_updated_hits"] = [hit.id for hit in updated]
        assert entity_ids[0] not in {hit.id for hit in updated} and entity_ids[1] in {
            hit.id for hit in updated
        }
        # Remove the still-visible Entity: a no-op removal must fail.
        await graph._upsert_nodes([(entity_keys[1], {"embedding": None})])
        removed = await port.nearest(query, top_k=2, threshold=0.99)
        assert not {hit.id for hit in removed}.intersection(entity_ids)
        physical = await graph._query(
            "SELECT embedding FROM GraphNodes WHERE label = 'Entity' AND node_id = @id",
            {"id": entity_ids[1]},
            {"id": param_types.STRING},
        )
        assert physical == [[None]], "removal did not null physical embedding"
        evidence["ann_removed_hits"] = [hit.id for hit in removed]
        evidence["ann_removed_physical_embedding"] = physical
        checks.append(
            {
                "name": "embedding update and removal affect native results",
                "passed": True,
                "scenarios": [],
            }
        )
        evidence["ann_query_trace"] = trace
    finally:
        evidence["ann_query_trace"] = trace
        # No global reset: remove only the exact typed keys registered above.
        cleanup_errors = []
        for remove, keys in ((graph._delete_edges, owned_edges), (graph._delete_nodes, owned_keys)):
            try:
                await remove(keys)
            except Exception as exc:
                cleanup_errors.append(exc)
        remaining_nodes = await graph._get_nodes(owned_keys)
        remaining_edges = await graph._edges(
            sources=event_keys, edge_type="REFERENCES", targets=entity_keys
        )
        final_edges = await graph._query(edge_sql)
        evidence["ann_after_edges_sha256"] = hashlib.sha256(
            json.dumps(final_edges, sort_keys=True, default=str).encode()
        ).hexdigest()
        evidence["ann_cleanup_errors"] = [type(exc).__name__ for exc in cleanup_errors]
        assert not remaining_nodes and not remaining_edges, "fixture cleanup incomplete"
        assert final_edges == original_edges, "unowned edge data changed"
        checks.append(
            {"name": "run-owned ANN nodes and edges removed", "passed": True, "scenarios": []}
        )
        if cleanup_errors:
            raise ExceptionGroup("ANN fixture cleanup failures", cleanup_errors)


async def verify_api_startup(values, credentials, evidence, checks, directory):
    """Two serial API processes, no ingestion, fixture reset or worker launches."""
    from types import SimpleNamespace

    from engram_spanner_compat import configure
    from engram_spanner_compat_remaining import Processes

    configure(values)
    evidence["startup_bootstrap"] = "explicit SDK token and scripted provider; not ADC"
    evidence["api_startups"] = []
    for iteration in range(2):
        owned = Processes(SimpleNamespace(directory=directory), credentials)
        # Explicitly override any inherited test auth mode.
        owned.environment["ENGRAM_COMPAT_AUTH"] = "token"
        observation = {"iteration": iteration + 1}
        evidence["api_startups"].append(observation)
        try:
            await owned.api()
            response = await owned.client.get("/v1/health")
            observation["health"] = response.json()
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            for field in ("event_log", "graph"):
                assert response.json()[field] == {"backend": "spanner", "ok": True}
            assert owned.processes["api"].poll() is None
            observation["pid"] = owned.processes["api"].pid
        finally:
            await owned.close()
            observation["cleanup"] = owned.receipts
            # Processes uses stable filenames; preserve each launch and log.
            for name in ("api.log", "api-launch.json", "process-cleanup.json"):
                path = directory / name
                if path.exists():
                    (directory / f"startup-{iteration + 1}-{name}").write_bytes(path.read_bytes())
        assert owned.receipts and all(item["exit_code"] is not None for item in owned.receipts)
        checks.append(
            {"name": f"API process startup {iteration + 1} healthy on Spanner", "passed": True,
             "scenarios": []}
        )
    assert evidence["api_startups"][0]["pid"] != evidence["api_startups"][1]["pid"]


async def verify_entity_bulk(database, dimensions, evidence, checks, directory):
    """Small real writes split by estimates; not a Spanner service-limit stress test."""
    from context_graph.adapters.spanner.commits import CommitBudget
    from context_graph.adapters.spanner.graph import SpannerGraphStore

    prefix = "bulk44_" + uuid4().hex
    keys = [("Entity", prefix + f"_{i}") for i in range(6)]
    vector = [0.1] * dimensions
    graph = SpannerGraphStore(
        database, embedding_dimensions=dimensions,
        commit_budget=CommitBudget(max_mutations=70, max_bytes=100_000),
    )
    assert not await graph._get_nodes(keys)
    fixture = {"owned_keys": keys, "embedding": vector, "retained_text": "retained " * 250}
    with (directory / "bulk-fixture.json").open("w") as stream:
        json.dump(fixture, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    original_rows = graph._node_rows
    original_transact = graph._transact
    pending_rows = []
    commits = []
    stage = "insert"

    def observed_rows(*args, **kwargs):
        rows = original_rows(*args, **kwargs)
        pending_rows.extend([list(row[:2]) for row in rows])
        return rows

    async def observed_transact(fn):
        def callback(transaction):
            # SDK retries get their own observation; retain only the callback
            # associated with the successful run_in_transaction return.
            pending_rows.clear()
            return fn(transaction)
        result = await original_transact(callback)
        commits.append({"stage": stage, "typed_keys": list(pending_rows)})
        return result

    graph._node_rows = observed_rows
    graph._transact = observed_transact
    try:
        await graph._upsert_nodes([
            (key, {"entity_id": key[1], "embedding": vector,
                   "retained_text": fixture["retained_text"]}) for key in keys
        ])
        stage = "replace"
        replacement = [-v for v in vector]
        await graph._upsert_nodes([(key, {"embedding": replacement, "status": "updated"})
                                   for key in keys])
        stored = await graph._get_nodes(keys)
        assert len(stored) == len(keys)
        for key in keys:
            assert stored[key]["entity_id"] == key[1]
            assert stored[key]["retained_text"] == fixture["retained_text"]
            assert stored[key]["status"] == "updated"
            assert stored[key]["embedding"] == replacement
        from google.cloud.spanner_v1 import param_types
        physical = await graph._query(
            "SELECT node_id, embedding, entity_embedding_member FROM GraphNodes "
            "WHERE label = 'Entity' AND STARTS_WITH(node_id, @prefix)",
            {"prefix": prefix}, {"prefix": param_types.STRING},
        )
        assert {key for key, _vector, _member in physical} == {key[1] for key in keys}
        assert all(value == replacement and member is True for _key, value, member in physical)
        for phase in ("insert", "replace"):
            batches = [item["typed_keys"] for item in commits if item["stage"] == phase]
            assert [len(batch) for batch in batches] == [2, 2, 2], batches
            assert [key for batch in batches for key in batch] == [list(key) for key in keys]
        evidence["bulk_commits"] = commits
        evidence["bulk_physical_rows"] = physical
        checks.append({"name": "six Entity insert/replacement rows split into two-row commits",
                       "passed": True, "scenarios": []})
    finally:
        graph._node_rows = original_rows
        graph._transact = original_transact
        evidence["bulk_commits"] = commits
        await graph._delete_nodes(keys)
        assert not await graph._get_nodes(keys), "owned bulk rows remain"
        checks.append({"name": "run-owned bulk Entities removed", "passed": True, "scenarios": []})

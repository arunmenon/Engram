"""Every adapter snapshot checks the same strong control snapshot before rows."""

from contextlib import contextmanager

import pytest

from context_graph.adapters.spanner.graph import SpannerGraphStore
from context_graph.adapters.spanner.log import SpannerEventLog
from context_graph.adapters.spanner.subscription import SpannerSubscription
from context_graph.adapters.spanner.tenant_control import TenantFence, TenantFenceError

RESOURCE = "projects/p/instances/i/databases/d"
FENCE = TenantFence("a", RESOURCE, "binding", 1, "sha256:" + "a" * 64)


class Database:
    name = RESOURCE

    def __init__(self, state="active", epoch=1):
        self.owner = ["a", RESOURCE, "binding", epoch, FENCE.bundle_digest, state]
        self.calls = []

    @contextmanager
    def snapshot(self, *, multi_use=False):
        assert multi_use, "Control and application reads require a multi-use snapshot"
        yield self

    def read(self, table, columns, keys, **kwargs):
        self.calls.append(table)
        if table == "TenantControl":
            return [self.owner]
        return []

    def execute_sql(self, sql, **kwargs):
        self.calls.append(sql)
        return [[0]] if "COUNT(*)" in sql else []


def operation(database, name, mode):
    kwargs = {"tenant_fence": FENCE, "tenant_read_operation": mode}
    graph = SpannerGraphStore(database, **kwargs)
    log = SpannerEventLog(database, **kwargs)
    sub = SpannerSubscription(
        database, "group", "consumer", tenant_engine_revision="test", **kwargs
    )
    return {
        "graph_query": lambda: graph._query("SELECT * FROM GraphNodes"),
        "graph_read": lambda: graph._read("GraphNodes", ["node_id"], None),
        "log_query": lambda: log._query("SELECT * FROM Events"),
        "log_documents": lambda: log._documents(["event"]),
        "delivery_counts": lambda: sub.delivery_counts(10),
        "dead_letters": sub.dead_letters,
        "lag": sub.lag,
    }[name]


READS = [
    "graph_query",
    "graph_read",
    "log_query",
    "log_documents",
    "delivery_counts",
    "dead_letters",
    "lag",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", READS)
@pytest.mark.parametrize("state,epoch", [("frozen", 1), ("active", 2), ("draining", 1)])
async def test_external_snapshot_refuses_before_application_reads(name, state, epoch):
    db = Database(state, epoch)
    with pytest.raises(TenantFenceError):
        await operation(db, name, "read")()
    assert db.calls == ["TenantControl"]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", READS)
@pytest.mark.parametrize("state", ["active", "draining"])
async def test_processing_reads_check_control_before_rows_and_allow_drain(name, state):
    db = Database(state)
    if name == "log_documents":
        from context_graph.ports.errors import RuntimeFencedError

        # Control allows drain, but a missing authoritative processing input refuses.
        with pytest.raises(RuntimeFencedError):
            await operation(db, name, "processing")()
    else:
        await operation(db, name, "processing")()
    assert db.calls[0] == "TenantControl"
    assert len(db.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("name", READS)
async def test_processing_reads_refuse_old_epoch_even_while_draining(name):
    db = Database("draining", 2)
    with pytest.raises(TenantFenceError):
        await operation(db, name, "processing")()
    assert db.calls == ["TenantControl"]


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["keyword", "vector"])
async def test_retrieval_cannot_downgrade_fenced_channel_to_empty_success(channel):
    from unittest.mock import AsyncMock, MagicMock

    from context_graph.ports.errors import RuntimeFencedError
    from tests.unit.test_retrieval_engine import FakeGraphReads, _engine

    broken = MagicMock()
    if channel == "keyword":
        broken.search = AsyncMock(side_effect=RuntimeFencedError("epoch changed"))
        engine = _engine(FakeGraphReads([]), keyword_index=broken)
        operation = engine._get_bm25_seeds("query", None, 10)
    else:
        broken.nearest = AsyncMock(side_effect=RuntimeFencedError("epoch changed"))
        engine = _engine(FakeGraphReads([]), vector_index=broken)
        operation = engine._get_vector_seeds([1.0], 10)
    with pytest.raises(RuntimeFencedError):
        await operation


@pytest.mark.asyncio
async def test_parallel_retrieval_cannot_hide_fenced_graph_channel():
    from unittest.mock import AsyncMock

    from context_graph.domain.models import SubgraphQuery
    from context_graph.ports.errors import RuntimeFencedError
    from tests.unit.test_retrieval_engine import FakeGraphReads, _engine

    engine = _engine(FakeGraphReads([]))
    engine._get_graph_seeds = AsyncMock(side_effect=RuntimeFencedError("changed"))
    engine._get_bm25_seeds = AsyncMock(return_value=[("valid-other-channel", 1.0)])
    with pytest.raises(RuntimeFencedError):
        await engine.get_subgraph(SubgraphQuery(query="query", session_id="s", agent_id="a"))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["graph", "log"])
async def test_health_cannot_hide_stale_runtime_as_backend_down(kind):
    db = Database("active", 2)
    store = (
        SpannerGraphStore(db, tenant_fence=FENCE)
        if kind == "graph"
        else SpannerEventLog(db, tenant_fence=FENCE)
    )
    with pytest.raises(TenantFenceError):
        await store.health_ping()
    assert db.calls == ["TenantControl"]


@pytest.mark.asyncio
async def test_eval_pending_cannot_keep_cached_answer_after_control_refusal():
    from unittest.mock import AsyncMock

    from context_graph.ontology.versioning import EvalPending
    from context_graph.ports.errors import RuntimeFencedError
    from tests.unit.test_tenant_catalog import bind

    graph = AsyncMock()
    graph.get_nodes.side_effect = [{}, RuntimeFencedError("changed")]
    pending = EvalPending(graph, bind().bundle.registry, ttl_s=0)
    await pending.packs()
    with pytest.raises(RuntimeFencedError):
        await pending.packs()

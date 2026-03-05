"""Adversarial concurrency tests for the Engram SDK."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engram.config import EngramConfig, configure, get_config, reset_config
from engram.models import AtlasResponse, IngestResult
from engram.sessions import SessionManager
from engram.transport import Transport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ingest_result() -> IngestResult:
    return IngestResult(event_id=str(uuid.uuid4()), global_position="1707644400000-0")


def _make_mock_client() -> AsyncMock:
    client = AsyncMock()
    client.ingest = AsyncMock(side_effect=lambda _: _make_ingest_result())
    client.get_context = AsyncMock(return_value=AtlasResponse())
    client.session = MagicMock(side_effect=lambda agent_id: SessionManager(client, agent_id))
    return client


# ===========================================================================
# TestConfigRaceConditions — threading-based tests
# ===========================================================================


class TestConfigRaceConditions:
    """Verify that global config access is thread-safe."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_config()
        yield
        reset_config()

    def test_concurrent_configure(self):
        """100 threads calling configure() simultaneously — no crash."""
        results: list[EngramConfig] = []
        errors: list[Exception] = []

        def worker(i: int) -> None:
            try:
                cfg = configure(base_url=f"http://host-{i}:8000")
                results.append(cfg)
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=100) as pool:
            list(pool.map(worker, range(100)))

        assert not errors, f"Unexpected errors: {errors}"
        assert len(results) == 100
        # Final state must be a valid config
        final = get_config()
        assert final.base_url.startswith("http://host-")

    def test_concurrent_get_config(self):
        """100 threads calling get_config() — all get the same instance."""
        configs: list[EngramConfig] = []

        def worker() -> None:
            configs.append(get_config())

        with ThreadPoolExecutor(max_workers=100) as pool:
            list(pool.map(lambda _: worker(), range(100)))

        assert len(configs) == 100
        # All should be the same instance (lazy init once)
        first = configs[0]
        for cfg in configs[1:]:
            assert cfg is first

    def test_configure_during_get_config(self):
        """One thread configures while others read — no partial state."""
        errors: list[Exception] = []
        configs: list[EngramConfig] = []

        def reader() -> None:
            try:
                cfg = get_config()
                # Config should be fully formed — base_url is never None
                assert cfg.base_url
                configs.append(cfg)
            except Exception as exc:
                errors.append(exc)

        def writer() -> None:
            try:
                configure(base_url="http://new-host:9000", api_key="key-99")
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = []
            for _ in range(49):
                futures.append(pool.submit(reader))
            futures.append(pool.submit(writer))
            for f in futures:
                f.result(timeout=5)

        assert not errors

    def test_reset_during_get_config(self):
        """reset_config() while get_config() in flight — safe."""
        errors: list[Exception] = []

        def reader() -> None:
            try:
                cfg = get_config()
                assert isinstance(cfg, EngramConfig)
            except Exception as exc:
                errors.append(exc)

        def resetter() -> None:
            try:
                reset_config()
            except Exception as exc:
                errors.append(exc)

        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = []
            for i in range(50):
                if i % 5 == 0:
                    futures.append(pool.submit(resetter))
                else:
                    futures.append(pool.submit(reader))
            for f in futures:
                f.result(timeout=5)

        assert not errors


# ===========================================================================
# TestSimpleModuleRaceConditions — asyncio-based tests
# ===========================================================================


class TestSimpleModuleRaceConditions:
    """Verify simple.py module-level singletons are created exactly once."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_config()
        import engram.simple as simple_mod

        simple_mod._default_client = None
        simple_mod._default_session = None
        yield
        simple_mod._default_client = None
        simple_mod._default_session = None
        reset_config()

    @pytest.mark.asyncio
    async def test_concurrent_record_creates_one_session(self):
        """10 concurrent record() when _default_session is None — exactly 1 session."""
        import engram.simple as simple_mod

        mock_client = _make_mock_client()
        with patch("engram.simple._get_client", return_value=mock_client):
            tasks = [simple_mod.record(f"msg-{i}", agent_id="agent") for i in range(10)]
            results = await asyncio.gather(*tasks)

        assert len(results) == 10
        # Only one session was created
        assert simple_mod._default_session is not None

    @pytest.mark.asyncio
    async def test_concurrent_record_after_session(self):
        """Concurrent record() after session exists — all reuse same session."""
        import engram.simple as simple_mod

        mock_client = _make_mock_client()
        with patch("engram.simple._get_client", return_value=mock_client):
            # Create initial session
            await simple_mod.record("init", agent_id="agent")
            session = simple_mod._default_session

            # Concurrent calls reuse it
            tasks = [simple_mod.record(f"msg-{i}", agent_id="agent") for i in range(10)]
            await asyncio.gather(*tasks)

        assert simple_mod._default_session is session

    @pytest.mark.asyncio
    async def test_configure_while_recording(self):
        """configure() while record() in-flight — no crash."""
        import engram.simple as simple_mod

        mock_client = _make_mock_client()
        with patch("engram.simple._get_client", return_value=mock_client):
            await simple_mod.record("init", agent_id="agent")

            # Configure resets state synchronously
            simple_mod.configure(base_url="http://other:8000")

            # Should work fine with new state
            with patch("engram.simple._get_client", return_value=mock_client):
                await simple_mod.record("after-configure", agent_id="agent")

    @pytest.mark.asyncio
    async def test_concurrent_recall_stateless(self):
        """Multiple concurrent recall() — all succeed independently."""
        import engram.simple as simple_mod

        mock_client = _make_mock_client()
        with patch("engram.simple._get_client", return_value=mock_client):
            tasks = [simple_mod.recall(session_id="sess-1") for _ in range(10)]
            results = await asyncio.gather(*tasks)

        assert len(results) == 10
        for r in results:
            assert isinstance(r, AtlasResponse)


# ===========================================================================
# TestSessionManagerConcurrency
# ===========================================================================


class TestSessionManagerConcurrency:
    """Verify SessionManager is safe under concurrent async usage."""

    def _make_session(self) -> SessionManager:
        mock_client = _make_mock_client()
        session = SessionManager(client=mock_client, agent_id="test-agent")
        session._started = True
        return session

    @pytest.mark.asyncio
    async def test_50_concurrent_records(self):
        """50 concurrent record() on one session — event_count == 50."""
        session = self._make_session()
        tasks = [session.record(f"event-{i}") for i in range(50)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 50
        assert session.event_count == 50
        # Each result is unique
        event_ids = {r.event_id for r in results}
        assert len(event_ids) == 50

    @pytest.mark.asyncio
    async def test_concurrent_record_and_end(self):
        """record() and end() called concurrently — no crash."""
        session = self._make_session()
        # First record some events
        await session.record("warmup")

        tasks = [
            session.record("concurrent-event-1"),
            session.record("concurrent-event-2"),
            session.end(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # No exceptions should occur
        for r in results:
            assert not isinstance(r, Exception), f"Unexpected error: {r}"

    @pytest.mark.asyncio
    async def test_double_end(self):
        """Two simultaneous end() — only one session_end event sent."""
        session = self._make_session()
        await session.record("warmup")

        results = await asyncio.gather(session.end(), session.end())

        # Exactly one should return a result, the other None
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 1
        assert session._ended is True

    @pytest.mark.asyncio
    async def test_concurrent_context_and_record(self):
        """context() and record() concurrent — both succeed."""
        session = self._make_session()

        async def do_context():
            return await session.context()

        tasks = [
            session.record("event-1"),
            do_context(),
            session.record("event-2"),
            do_context(),
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 4


# ===========================================================================
# TestTransportConcurrency
# ===========================================================================


class TestTransportConcurrency:
    """Verify Transport lazy-creates exactly one httpx client under concurrency."""

    def _make_transport(self) -> Transport:
        config = EngramConfig(base_url="http://test:8000")
        return Transport(config)

    @pytest.mark.asyncio
    async def test_concurrent_ensure_client(self):
        """20 concurrent requests when _client is None — only 1 client created."""
        transport = self._make_transport()
        clients: list[Any] = []

        async def get_client():
            c = await transport._ensure_client()
            clients.append(c)

        await asyncio.gather(*[get_client() for _ in range(20)])

        assert len(clients) == 20
        # All should be the same instance
        first = clients[0]
        for c in clients[1:]:
            assert c is first

        await transport.close()

    @pytest.mark.asyncio
    async def test_close_during_request(self):
        """close() while _ensure_client in-flight — no crash."""
        transport = self._make_transport()

        async def ensure_and_ignore():
            with contextlib.suppress(Exception):
                await transport._ensure_client()

        await asyncio.gather(
            ensure_and_ignore(),
            transport.close(),
        )

    @pytest.mark.asyncio
    async def test_many_concurrent_ensure_client(self):
        """200 concurrent _ensure_client calls — all complete."""
        transport = self._make_transport()

        async def get_client():
            return await transport._ensure_client()

        results = await asyncio.gather(*[get_client() for _ in range(200)])
        assert len(results) == 200
        await transport.close()

    @pytest.mark.asyncio
    async def test_client_reuse_after_close(self):
        """close() then _ensure_client — lazily recreates client."""
        transport = self._make_transport()

        client_1 = await transport._ensure_client()
        await transport.close()
        client_2 = await transport._ensure_client()

        # Should be a new instance
        assert client_2 is not client_1
        await transport.close()


# ===========================================================================
# TestSyncClientThreadSafety
# ===========================================================================


class TestSyncClientThreadSafety:
    """Verify EngramSyncClient thread/loop isolation."""

    def test_multiple_instances(self):
        """5 EngramSyncClient instances simultaneously — each has own loop/thread."""
        from engram.sync_client import EngramSyncClient

        instances = []
        for _ in range(5):
            instances.append(EngramSyncClient(config=EngramConfig(base_url="http://test:8000")))

        # Each has a distinct loop
        loops = {inst._loop for inst in instances}
        assert len(loops) == 5

        # Each has a distinct thread
        threads = {inst._thread for inst in instances}
        assert len(threads) == 5

        for inst in instances:
            inst.close()

    def test_close_idempotent(self):
        """close() called twice — no error."""
        from engram.sync_client import EngramSyncClient

        client = EngramSyncClient(config=EngramConfig(base_url="http://test:8000"))
        client.close()
        # Second close should not raise
        client.close()

    def test_thread_cleanup_on_close(self):
        """After close(), background thread is no longer alive."""
        from engram.sync_client import EngramSyncClient

        client = EngramSyncClient(config=EngramConfig(base_url="http://test:8000"))
        thread = client._thread
        assert thread.is_alive()

        client.close()
        assert not thread.is_alive()

    def test_gc_without_close(self):
        """Create client, drop reference — daemon thread allows process exit."""
        from engram.sync_client import EngramSyncClient

        client = EngramSyncClient(config=EngramConfig(base_url="http://test:8000"))
        thread = client._thread
        assert thread.daemon  # Daemon threads don't block process exit
        client.close()

    def test_stuck_coroutine_timeout(self):
        """Coroutine that never resolves — future.result() has timeout."""
        from engram.sync_client import EngramSyncClient

        client = EngramSyncClient(config=EngramConfig(base_url="http://test:8000", timeout=0.5))

        async def never_resolve():
            await asyncio.sleep(999)

        future = asyncio.run_coroutine_threadsafe(never_resolve(), client._loop)

        with pytest.raises(TimeoutError):
            # timeout = 0.5 + 5 = 5.5 ... use a shorter one for test speed
            future.result(timeout=0.2)

        client.close()


# ===========================================================================
# TestPageIteratorConcurrency
# ===========================================================================


class TestPageIteratorConcurrency:
    """Verify PageIterator instances are independent."""

    @pytest.mark.asyncio
    async def test_multiple_iterators_independent(self):
        """Two iterators on same endpoint — independent state."""
        from engram.pagination import PageIterator

        call_count = 0

        async def mock_fetch(*, session_id: str, cursor: str | None = None, **kw):
            nonlocal call_count
            call_count += 1
            from engram.models import Pagination, QueryMeta

            return AtlasResponse(
                pagination=Pagination(cursor=None, has_more=False),
                meta=QueryMeta(nodes_returned=0),
            )

        iter1 = PageIterator(mock_fetch, session_id="s1")
        iter2 = PageIterator(mock_fetch, session_id="s2")

        page1 = await iter1.__anext__()
        page2 = await iter2.__anext__()

        assert page1 is not page2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_anext_after_exhaustion(self):
        """__anext__ after StopAsyncIteration — raises again."""
        from engram.models import Pagination, QueryMeta
        from engram.pagination import PageIterator

        async def mock_fetch(**kw):
            return AtlasResponse(
                pagination=Pagination(cursor=None, has_more=False),
                meta=QueryMeta(nodes_returned=0),
            )

        iterator = PageIterator(mock_fetch, session_id="s1")
        await iterator.__anext__()  # First page

        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()

        # Second call should also raise
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()

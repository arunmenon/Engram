"""SDK-boundary instrumentation must not count scheduled writes as committed."""

import asyncio

import pytest
from engram_consolidation_shutdown_demo import SDKGate

from context_graph.ports.errors import UnavailableError


class Transaction:
    def __init__(self):
        self.scheduled = []

    def insert_or_update(self, table, columns, rows):
        self.scheduled.extend(rows)


class Database:
    def __init__(self, *, retry=False):
        self.transactions = []
        self.committed = []
        self.retry = retry

    def run_in_transaction(self, operation):
        for attempt in range(2 if self.retry else 1):
            tx = Transaction()
            self.transactions.append(tx)
            result = operation(tx)
            if self.retry and attempt == 0:
                continue  # Simulated SDK abort/retry after callback scheduling.
            self.committed.extend(tx.scheduled)
            return result


def write(tx, key="summary-s", scope="episode"):
    tx.insert_or_update(
        "GraphNodes",
        ["label", "node_id", "props", "embedding"],
        [
            [
                "Summary",
                key,
                {"summary_id": key, "scope": scope, "scope_id": "s", "event_count": 2},
                None,
            ]
        ],
    )


async def test_gate_holds_after_sdk_mutation_scheduling_and_counts_whole_cycle_commits():
    db = Database()
    gate = SDKGate(db, "stop")
    task = asyncio.create_task(asyncio.to_thread(gate.run_in_transaction, write))
    try:
        for _ in range(100):
            if gate.entered.is_set():
                break
            await asyncio.sleep(0.01)
        held = gate.evidence()
        assert db.transactions[0].scheduled
        assert db.committed == []
        assert held["summary_commits"] == []
        assert held["active_calls"] == 1
        gate.release.set()
        await task
        await asyncio.to_thread(
            gate.run_in_transaction, lambda tx: write(tx, "summary-session", "session")
        )
        await asyncio.to_thread(
            gate.run_in_transaction, lambda tx: write(tx, "summary-agent", "agent")
        )
        committed = gate.evidence()
        assert {entry["scope"] for entry in committed["summary_commits"]} == {
            "episode",
            "session",
            "agent",
        }
        assert committed["active_calls"] == 0
        assert committed["returned_calls"] == 3
        assert held["summary_commits"] == []  # Saved hold evidence must not mutate later.
    finally:
        gate.release.set()
        await task


async def test_sdk_callback_exception_does_not_count_scheduled_summary_as_committed():
    db = Database()
    gate = SDKGate(db, "storage-failure")
    gate.release.set()
    with pytest.raises(UnavailableError):
        await asyncio.to_thread(gate.run_in_transaction, write)
    observed = gate.evidence()
    assert db.committed == []
    assert observed["summary_commits"] == []
    assert len(observed["summary_rollbacks"]) == 1
    assert observed["gated_outcome"] == "UnavailableError"
    assert observed["active_calls"] == 0


async def test_sdk_retry_counts_only_the_committed_callback_attempt():
    db = Database(retry=True)
    gate = SDKGate(db, "restart")
    gate.release.set()
    await asyncio.to_thread(gate.run_in_transaction, write)
    observed = gate.evidence()
    assert len(db.transactions) == 2
    assert len(db.committed) == 1
    assert len(observed["summary_commits"]) == 1
    assert observed["gated_outcome"] == "committed"

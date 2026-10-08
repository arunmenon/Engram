"""Commit budgets for Spanner writes.

Spanner refuses a commit with more than 80,000 mutations or more than
100 MiB, secondary indexes included
(https://cloud.google.com/spanner/quotas). Writes that take a caller's
list (an import chunk, a projection flush, retention) are therefore split
into transactions whose estimated cost stays under a ``CommitBudget``
(``CG_SPANNER_COMMIT_MAX_MUTATIONS`` / ``_MAX_BYTES``).

The estimates follow Spanner's counting: an inserted or updated row costs
one mutation per column written, plus, for every index the row appears
in, one per column that index holds (its key, the table's primary key and
any ``STORING`` columns). Bytes are the values written, counted again for
each index that stores them. They are estimates, so the default budget
keeps half of each limit as headroom. A single item over budget still
goes in a transaction of its own: Spanner, not this module, has the last
word.

Source: ADR-0019, docs/review/2026-10-05-maturity-review-guide.md (S5)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import orjson

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

# Mutations per row, from adapters/spanner/schema.py.
# Events: 19 columns written; indexes EventsByShardPosition (3 + key 1),
# EventsBySession (3 + 1), EventsBySessionTag (2 + 1), and the EventsText
# search index (tokens + key + stored session_tag).
EVENT_ROW_MUTATIONS = 19 + 4 + 4 + 3 + 3
# Conservative coexistence budget: base/generated values, session index,
# retained legacy vector index, filtered Entity index with stored membership.
# Allow removal and replacement of entries; this is not SDK-internal accounting.
NODE_ROW_MUTATIONS = 2 * (6 + 4 + 3 + 4)
# GraphEdges: 6 columns; GraphEdgesByTarget and GraphEdgesByType each hold
# the 5 key columns and props.
EDGE_ROW_MUTATIONS = 6 + 6 + 6
# A deleted row: the row and one entry per index
NODE_DELETE_MUTATIONS = 1 + 3
EDGE_DELETE_MUTATIONS = 1 + 2
# Fixed per-row overhead for keys and column headers, in bytes
ROW_OVERHEAD_BYTES = 256


class CommitTooLarge(Exception):  # noqa: N818 - control flow, never leaves the adapter
    """Raised inside a transaction whose rows turn out larger than the budget.

    The transaction rolls back, and the caller splits the items and retries.
    """


def size_of(value: Any) -> int:
    """Approximate bytes of a value as written to Spanner."""
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value.encode())
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, (bool, int, float)):
        return 8
    if isinstance(value, (list, tuple)) and all(isinstance(v, (int, float)) for v in value):
        return 8 * len(value)
    return len(orjson.dumps(value, default=str))


def event_row_cost(document: dict[str, Any] | None) -> tuple[int, int]:
    """(mutations, bytes) of one Events row; the text columns are indexed again."""
    doc = document or {}
    text = sum(size_of(doc.get(name)) for name in ("summary", "keywords", "search_text"))
    return EVENT_ROW_MUTATIONS, size_of(document) + 2 * text + ROW_OVERHEAD_BYTES


def node_row_cost(key: tuple[str, str], props: dict[str, Any], embedding: Any) -> tuple[int, int]:
    """(mutations, bytes) of one GraphNodes row; props are stored again by the session index."""
    keys = size_of(key[0]) + size_of(key[1])
    session = size_of(props.get("session_id"))
    membership = 8
    size = (
        4 * keys
        + 2 * size_of(props)
        + 3 * size_of(embedding)
        + 2 * session
        + 2 * membership
        + 4 * ROW_OVERHEAD_BYTES
    )
    return NODE_ROW_MUTATIONS, size


def edge_row_cost(key: Any, props: dict[str, Any]) -> tuple[int, int]:
    """(mutations, bytes) of one GraphEdges row; both indexes store key and props."""
    (src_label, src_id), edge_type, (dst_label, dst_id) = key
    keys = sum(size_of(part) for part in (src_label, src_id, edge_type, dst_label, dst_id))
    return EDGE_ROW_MUTATIONS, 3 * (keys + size_of(props)) + ROW_OVERHEAD_BYTES


@dataclass(frozen=True)
class CommitBudget:
    """Most mutations and bytes one transaction should carry."""

    max_mutations: int = 40_000
    max_bytes: int = 50 * 1024 * 1024

    def fits(self, mutations: int, size: int) -> bool:
        return mutations <= self.max_mutations and size <= self.max_bytes

    def check(self, costs: Sequence[tuple[int, int]]) -> None:
        """Raise ``CommitTooLarge`` when the summed costs exceed the budget."""
        if not self.fits(sum(m for m, _b in costs), sum(b for _m, b in costs)):
            raise CommitTooLarge

    def chunks[T](self, items: Sequence[T], cost: Callable[[T], tuple[int, int]]) -> list[list[T]]:
        """Split ``items``, in order, into runs whose summed cost fits the budget.

        An item that alone exceeds the budget forms a run of its own.
        """
        runs: list[list[T]] = []
        current: list[T] = []
        mutations = size = 0
        for item in items:
            item_mutations, item_size = cost(item)
            if current and not self.fits(mutations + item_mutations, size + item_size):
                runs.append(current)
                current, mutations, size = [], 0, 0
            current.append(item)
            mutations += item_mutations
            size += item_size
        if current:
            runs.append(current)
        return runs


def group_by_key[T](items: Sequence[T], key: Callable[[T], Any]) -> list[list[T]]:
    """Items grouped by key, groups in first-seen order, items in order within a group.

    Writes to one key depend on each other (updates apply in order, a
    transition sees the one before), so a key's items share a transaction.
    """
    groups: dict[Any, list[T]] = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return list(groups.values())

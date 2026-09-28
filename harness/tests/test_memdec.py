import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memdec import export, targets  # noqa: E402


def test_export_builds_items_and_pairs_with_repo_splits():
    extractions = [
        {"session_id": "s1", "agent_id": "a", "ended_at": "2026-01-01", "preferences": [
            {"category": "tool", "key": "editor", "polarity": "positive", "strength": 0.8, "confidence": 0.9, "source": "explicit", "source_quote": "I use vim", "source_turn_index": 1}]},
        {"session_id": "s2", "agent_id": "a", "ended_at": "2026-01-02", "preferences": [
            {"category": "tool", "key": "editor", "polarity": "positive", "strength": 0.6, "confidence": 0.7, "source": "explicit", "source_quote": "switched to emacs", "source_turn_index": 0}]},
    ]
    transcripts = {"s1": [{"index": i, "role": "user", "text": f"t{i}"} for i in range(4)], "s2": [{"index": 0, "role": "user", "text": "u0"}]}
    items, pairs = export.build(extractions, transcripts, {"s1": "r1", "s2": "r1"}, window=1)
    assert len(items) == 2 and len(pairs) == 1
    assert pairs[0]["memory_a"]["quote"] == "I use vim"
    split = export.assign_splits([f"r{i}" for i in range(20)], 1, 10, 2, 8)
    assert sorted(set(split.values())) == ["test", "train", "val"]
    assert list(split.values()).count("test") == 8


def test_soft_targets_smoothing():
    rows = targets.soft_targets([
        {"item_id": "x", "labeller_id": "l1", "label": "store"},
        {"item_id": "y", "labeller_id": "l1", "label": "store"}, {"item_id": "y", "labeller_id": "l2", "label": "skip"},
    ])
    by = {r["id"]: r for r in rows}
    assert by["x"]["p_positive"] == 0.9 and by["y"]["p_positive"] == 0.5

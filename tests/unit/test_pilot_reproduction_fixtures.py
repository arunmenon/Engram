from copy import deepcopy

import pytest
from engram_pilot_reproduction_fixtures import freeze, with_library_extension


def test_extension_keeps_original_inputs_and_adds_one_scoped_change():
    base = freeze("pilot-p11-unit")
    original = deepcopy(base)
    extended = with_library_extension(base)
    assert base == original
    assert sum(len(g["steps"]) for g in extended["groups"]) == 3
    for before, after in zip(base["groups"], extended["groups"], strict=True):
        assert after["steps"][: len(before["steps"])] == before["steps"]
    b = extended["groups"][0]
    extra = b["steps"][1]
    assert extra["expected_node"] == "Change:pilot/pilot-p11-unit/library|8"
    assert b["source_expectations"][extra["expected_node"]] == [extra["request"]["event_id"]]
    assert extra["request"]["event_id"] != b["steps"][0]["request"]["event_id"]
    with pytest.raises(ValueError):
        with_library_extension(extended)


def test_foreign_positive_precedes_negative_and_memory_uses_raw_identity():
    plan = freeze("pilot-p11-unit")
    b, a = plan["groups"]
    foreign = b["steps"][0]["request"]["event_id"]
    assert b["final_queries"][0]["required"] == [foreign]
    query = a["final_queries"][0]
    assert foreign in query["seed_nodes"] and foreign in query["forbidden"]
    assert query["intent"] == "when"
    assert a["steps"][0]["expected_node"].startswith("goal-")
    assert not a["steps"][0]["expected_node"].startswith("Goal:")

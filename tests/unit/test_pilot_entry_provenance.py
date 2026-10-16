"""Retained content-keyed proposals still require each new source's evidence."""

from engram_pilot_first_run import sourced_proposals


def test_existing_identity_is_eligible_only_with_exact_current_source():
    state = {
        "nodes": [["Decision", "shared", {"status": "proposed"}],
                  ["Decision", "other", {}], ["Spec", "spec", {}]],
        "edges": [["Decision", "shared", "DERIVED_FROM", "Event", "old", {}],
                  ["Decision", "shared", "DERIVED_FROM", "Event", "current", {}],
                  ["Decision", "other", "DERIVED_FROM", "Event", "old", {}],
                  ["Spec", "spec", "DERIVED_FROM", "Event", "current", {}]],
    }
    assert [r[1] for r in sourced_proposals(state, {"current"})] == ["shared"]
    assert not sourced_proposals(state, {"missing"})
    state["edges"] = state["edges"][:1]
    assert not sourced_proposals(state, {"current"})

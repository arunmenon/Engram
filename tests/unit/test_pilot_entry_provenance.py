"""Retained content-keyed proposals still require each new source's evidence."""

from engram_pilot_first_run import sourced_proposals


def test_existing_identity_is_eligible_only_with_exact_current_source():
    state = {
        "nodes": [
            ["Decision", "shared", {"status": "proposed"}],
            ["Decision", "other", {}],
            ["Spec", "spec", {}],
        ],
        "edges": [
            ["Decision", "shared", "DERIVED_FROM", "Event", "old", {}],
            ["Decision", "shared", "DERIVED_FROM", "Event", "current", {}],
            ["Decision", "other", "DERIVED_FROM", "Event", "old", {}],
            ["Spec", "spec", "DERIVED_FROM", "Event", "current", {}],
        ],
    }
    assert [r[1] for r in sourced_proposals(state, {"current"})] == ["shared"]
    assert not sourced_proposals(state, {"missing"})
    state["edges"] = state["edges"][:1]
    assert not sourced_proposals(state, {"current"})


def test_selected_query_only_plan_contains_no_entry_events_or_scope(tmp_path):
    import json
    from types import SimpleNamespace

    from engram_pilot_first_run import build_plan

    path = tmp_path / "queries.json"
    path.write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "name": "retained",
                        "tenant": "b",
                        "steps": [],
                        "queries": [{"scenario": "read"}],
                    }
                ],
                "coverage": "Only retained read checks",
            }
        )
    )
    args = SimpleNamespace(
        run_id="selected-test", journey_file=path, spectrum=False, journeys_only=True
    )
    plan = build_plan(args)
    assert plan["events"] == []
    assert plan["expected_artifacts"] == {} and plan["queries"] == {}
    assert plan["scope"] == ["Only retained read checks"]
    assert plan["execution_mode"] == "selected-retained-reads"
    args.journeys_only = False
    default = build_plan(args)
    assert len(default["events"]) == 9
    assert "A-01" in default["scope"]


def test_selected_mode_rejects_empty_plan_before_cloud_execution(tmp_path):
    import json
    from types import SimpleNamespace

    import pytest
    from engram_pilot_first_run import build_plan

    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"groups": [], "coverage": "empty"}))
    with pytest.raises(ValueError, match="requires nonempty"):
        build_plan(
            SimpleNamespace(
                run_id="empty-test", journey_file=path, spectrum=False, journeys_only=True
            )
        )

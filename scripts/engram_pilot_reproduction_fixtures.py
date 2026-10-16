"""Small clean-checkout proof using existing JSON runner; no engine changes."""

from copy import deepcopy
from uuid import NAMESPACE_URL, uuid5

from engram_pilot_completion_fixtures import p04_memory, p04_negative_proof
from engram_pilot_retrieval_proof import freeze as retrieval_fixture


def freeze(run_id, *, extension=False):
    memory = p04_memory(run_id)["groups"][0]
    goal = deepcopy(next(s for s in memory["steps"] if s["scenario"] == "agent-goal-created"))
    source = goal["request"]
    goal["expected_props"]["description"] = source["payload"]["description"]
    a = dict(
        name="p11-a-goal",
        tenant="a",
        steps=[goal],
        queries=[],
        retained_negative_proofs=[p04_negative_proof()],
        source_expectations={
            goal["expected_node"]: [source["event_id"]],
            source["event_id"]: [source["event_id"]],
        },
    )
    change = deepcopy(retrieval_fixture(run_id)["groups"][0]["steps"][0])
    payload = change["request"]["payload"]
    change.update(
        expected_node="Change:" + payload["repo"] + "|" + str(payload["number"]),
        expected_props=dict(title=payload["title"], status="open"),
        extra_nodes={},
    )
    b = dict(
        name="p11-b-change",
        tenant="b",
        steps=[change],
        queries=[],
        source_expectations={
            change["expected_node"]: [change["request"]["event_id"]],
            change["request"]["event_id"]: [change["request"]["event_id"]],
        },
    )
    bs = change["request"]
    b["final_queries"] = [
        dict(
            query="Show this accepted source Event",
            intent="what",
            session_id=bs["session_id"],
            agent_id=bs["agent_id"],
            seed_nodes=[bs["event_id"]],
            required=[bs["event_id"]],
            forbidden=[],
        )
    ]
    a["final_queries"] = [
        dict(
            query="Show my explicit Goal and this requested source",
            intent="when",
            session_id=source["session_id"],
            agent_id=source["agent_id"],
            seed_nodes=[bs["event_id"], source["event_id"]],
            required=[goal["expected_node"], source["event_id"]],
            forbidden=[bs["event_id"], change["expected_node"]],
        )
    ]
    plan = dict(
        run_id=run_id,
        coverage=(
            "P11 technical checkout reproduction: B source positive then A exclusion; "
            "one explicit A Goal and B Change plus optional JSON library story"
        ),
        extension_included=False,
        groups=[b, a],
    )
    return with_library_extension(plan) if extension else plan


def with_library_extension(base):
    """Add one supported story by changing fixture data only; keep originals exact."""
    if base.get("extension_included"):
        raise ValueError("Library extension already present")
    plan = deepcopy(base)
    run_id = plan["run_id"]
    b = next(g for g in plan["groups"] if g["tenant"] == "b")
    change = b["steps"][0]
    extra = deepcopy(change)
    extra["scenario"] = "json-extension-library"
    extra["request"].update(
        event_id=str(uuid5(NAMESPACE_URL, run_id + ":json-extension")),
        session_id=run_id + ":json-extension",
        payload_ref="pilot-p11:json-extension",
    )
    extra["request"]["payload"].update(
        repo="pilot/" + run_id + "/library",
        number=8,
        title="Library metadata export",
        head_sha="def456",
    )
    extra.update(
        expected_node="Change:pilot/" + run_id + "/library|8",
        expected_props=dict(title="Library metadata export", status="open"),
    )
    b["steps"].append(extra)
    b["source_expectations"][extra["expected_node"]] = [extra["request"]["event_id"]]
    plan["extension_included"] = True
    return plan

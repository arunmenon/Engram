"""Frozen normalized G07-D deployment producers and independent acceptance oracles.

No backend execution. Query checkpoints must run after their named step and before
subsequent steps. A later explicit change.merged can match an upgrade's exact merge
identity under the pre-existing reciprocal rule; D06 forbids inference by upgrade.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5


def fixtures(run_id, *, start=None):
    prefix = "g07-d/" + run_id
    repo, service = prefix + "/app", prefix + "/api"
    start = start or datetime(2026, 10, 8, 10, tzinfo=UTC)
    start = start.astimezone(UTC)
    ids, steps, queries = {}, [], []

    def node(kind, *values):
        return kind + ":" + "|".join(str(v).replace("%", "%25").replace("|", "%7C") for v in values)

    def at(seconds):
        return (start + timedelta(seconds=seconds)).isoformat()

    def event_id(scenario):
        return str(uuid5(NAMESPACE_URL, run_id + ":" + scenario))

    def add(scenario, kind, payload, second, nid=None, props=None, edges=(), status=201):
        steps.append(
            dict(
                scenario=scenario,
                request=dict(
                    event_id=event_id(scenario),
                    event_type="pdlc.service." + kind,
                    occurred_at=at(second),
                    session_id=prefix,
                    agent_id="deployment.publisher",
                    trace_id=run_id,
                    payload_ref="synthetic:" + run_id + ":" + scenario,
                    payload=deepcopy(payload),
                ),
                expected_status=status,
                expected_node=nid,
                expected_props=props or {},
                expected_edges=[list(e) for e in edges],
                extra_nodes={},
            )
        )

    def query(scenario, after, seed, required, states, observations, edges=()):
        queries.append(
            dict(
                scenario=scenario,
                after_scenario=after,
                request=dict(query="trace", seed_node_ids=[seed], intent="trace"),
                required_nodes=required,
                expected_states=states,
                expected_observation_events=observations,
                expected_edges=[list(e) for e in edges],
            )
        )

    identity = dict(repo=repo, service=service, environment="production", artifact_id="same-sha")
    component = ids["component"] = node("Component", service)
    a = ids["deployment_a"] = node("Deployment", repo, service, "production", "same-sha", at(0))
    b = ids["deployment_b"] = node("Deployment", repo, service, "production", "same-sha", at(1))
    add(
        "D01-A",
        "deployed",
        identity | {"change_numbers": [7]},
        0,
        a,
        dict(status="succeeded"),
        [("DEPLOYS", a, node("Change", repo, 7)), ("DEPLOYED_TO", a, component)],
    )
    add(
        "D01-B",
        "deployed",
        identity | {"change_numbers": [9]},
        1,
        b,
        dict(status="succeeded"),
        [("DEPLOYS", b, node("Change", repo, 9)), ("DEPLOYED_TO", b, component)],
    )
    rollback = ids["rollback_b"] = node("DeploymentRollback", event_id("D02-rollback-B"))
    add(
        "D02-rollback-B",
        "rolledback",
        identity | {"target_started_at": at(1)},
        10,
        rollback,
        edges=[("ROLLS_BACK", rollback, b)],
    )
    query(
        "DQ02-retained-exact-target",
        "D02-rollback-B",
        rollback,
        [rollback, a, b],
        {a: "succeeded", b: "rolled_back"},
        {a: event_id("D01-A"), b: event_id("D01-B"), rollback: event_id("D02-rollback-B")},
        [("ROLLS_BACK", rollback, b), ("DEPLOYS", b, node("Change", repo, 9))],
    )
    add(
        "D03-late-original-B",
        "deployed",
        identity | {"change_numbers": [9]},
        1,
        b,
        dict(status="rolled_back"),
    )

    # Neighboring time and each scoped key are distinct attempts despite reused artifact.
    for suffix, changes in (
        ("repo", {"repo": prefix + "/other"}),
        ("service", {"service": prefix + "/worker"}),
        ("environment", {"environment": "staging"}),
    ):
        payload = identity | changes
        target = ids["collision_" + suffix] = node(
            "Deployment",
            payload["repo"],
            payload["service"],
            payload["environment"],
            payload["artifact_id"],
            at(1),
        )
        add("D03-collision-" + suffix, "deployed", payload, 1, target, dict(status="succeeded"))

    unknown = ids["unknown_target"] = node(
        "Deployment", repo, service, "production", "unknown-sha", at(2)
    )
    unknown_rollback = ids["unknown_rollback"] = node("DeploymentRollback", event_id("D04-unknown"))
    unknown_identity = identity | {"artifact_id": "unknown-sha"}
    add(
        "D04-unknown",
        "rolledback",
        unknown_identity | {"target_started_at": at(2)},
        11,
        unknown_rollback,
        edges=[("ROLLS_BACK", unknown_rollback, unknown)],
    )
    query(
        "DQ04-null-observation",
        "D04-unknown",
        unknown_rollback,
        [unknown_rollback, unknown],
        {unknown: "rolled_back"},
        {unknown: None, unknown_rollback: event_id("D04-unknown")},
    )
    add("D04-late-fill", "deployed", unknown_identity, 2, unknown, dict(status="rolled_back"))
    query(
        "DQ04-real-observation",
        "D04-late-fill",
        unknown_rollback,
        [unknown_rollback, unknown],
        {unknown: "rolled_back"},
        {unknown: event_id("D04-late-fill"), unknown_rollback: event_id("D04-unknown")},
    )

    upgrade = ids["upgrade"] = node(
        "Deployment", repo, service, "production", "upgrade-sha", at(20)
    )
    add(
        "D05-upgrade",
        "upgraded",
        identity | {"artifact_id": "upgrade-sha", "change_numbers": [11]},
        20,
        upgrade,
        dict(status="succeeded", operation="upgrade"),
        [("DEPLOYS", upgrade, node("Change", repo, 11)), ("DEPLOYED_TO", upgrade, component)],
    )
    no_changes = ids["upgrade_no_changes"] = node(
        "Deployment", repo, service, "production", "bare-sha", at(21)
    )
    add(
        "D06-upgrade-no-changes",
        "upgraded",
        identity | {"artifact_id": "bare-sha"},
        21,
        no_changes,
        dict(status="succeeded", operation="upgrade"),
        [("DEPLOYED_TO", no_changes, component)],
    )
    steps[-1]["forbidden_outgoing_edge_types"] = ["DEPLOYS"]

    for suffix, invalid in (
        ("missing", None),
        ("naive", "2026-10-08T10:00:00"),
        ("integer", 7),
        ("calendar", "2026-02-30T10:00:00Z"),
    ):
        payload = identity | ({"target_started_at": invalid} if invalid is not None else {})
        add("D06-invalid-" + suffix, "rolledback", payload, 30, status=422)
        steps[-1]["assert_no_owned_table_changes"] = True
    return dict(
        ids=ids,
        steps=steps,
        queries=queries,
        fallback_seed=rollback,
        source_kind="Synthetic normalized deployment assertions; no native adapters",
        limitations=[
            (
                "Upgrade projection never infers DEPLOYS; later explicit change.merged retains "
                "existing repo/artifact merge-identity matching."
            ),
            (
                "Timestamp contract uses a maintained bounded RFC3339 regex: year 0001–9999, "
                "explicit offset, no leap seconds, 1–6 fractional digits."
            ),
        ],
    )

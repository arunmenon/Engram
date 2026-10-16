"""Additional pilot journeys using existing independent goal fixture oracles.

No backend writes or models run during fixture construction. Execution uses the
pilot's public HTTP client and ordinary workers; snapshots supplement API reads.
This is a coverage stage, not an automatic claim that all discovery candidates
are supported. Discovery gaps keep distinct verdicts in the handoff matrix.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from engram_experiment_support import snapshot
from engram_goal02_fixtures import fixtures as planning
from engram_goal03_implementation_demo import (
    assert_forbidden_edges,
    assert_retrieval_policy,
    fixture_observations,
    http_steps,
)
from engram_goal05_fixtures import fixtures as connected
from engram_goal06_fixtures import fixtures as incidents
from engram_goal07_fixtures import fixtures as catalog
from engram_memory_actions_demo import identity

from context_graph.adapters.spanner.log import json_value


def replace_strings(value, replacements, pattern):
    if isinstance(value, str):
        return pattern.sub(lambda m: replacements[m[0]], value)
    if isinstance(value, list):
        return [replace_strings(v, replacements, pattern) for v in value]
    if isinstance(value, dict):
        return {
            replace_strings(k, replacements, pattern): replace_strings(v, replacements, pattern)
            for k, v in value.items()
        }
    return value


def freeze(run_id):
    groups = []
    for name, factory in (
        ("planning", planning),
        ("connected", connected),
        ("incident", incidents),
        ("catalog", catalog),
    ):
        data = factory(run_id + "-" + name)
        if name == "catalog":
            # Keep semantic/lifecycle/retry cases and one malformed input for
            # every event contract. Exhaustive field matrices remain G07 evidence.
            rejected = set()
            selected = []
            for step in data["steps"]:
                kind = step["request"]["event_type"]
                if step["expected_status"] != 422 or kind not in rejected:
                    selected.append(step)
                if step["expected_status"] == 422:
                    rejected.add(kind)
            data["steps"] = selected
            # The G07-A examples deliberately use literal IDs in an empty DB.
            # Namespace those examples and statement hashes for retained runs.
            replacements = {
                s: run_id + "/" + s
                for s in (
                    "RESET-REQUEST",
                    "MINIMAL",
                    "RESET-PRD",
                    "RESET-HLD",
                    "UNKNOWN-HLD",
                    "RESET-1",
                    "RESET-17",
                    "RESET-18",
                )
            }
            # A slash prefix leaves a trailing RESET-N token that commit-text
            # rules still recognize. Keep ticket identities valid Jira keys.
            ticket_project = "P" + hashlib.sha256(run_id.encode()).hexdigest()[:10].upper()
            replacements.update({f"RESET-{n}": f"{ticket_project}-{n}" for n in (1, 17, 18)})
            for step in data["steps"]:
                if (
                    step["scenario"].startswith("A")
                    and step["request"]["event_type"] == "pdlc.decision.recorded"
                ):
                    statement = step["request"]["payload"]["statement"]
                    revised = run_id + ": " + statement
                    replacements[statement] = revised
                    replacements[hashlib.sha256(statement.encode()).hexdigest()] = hashlib.sha256(
                        revised.encode()
                    ).hexdigest()
            pattern = re.compile(
                "|".join(re.escape(k) for k in sorted(replacements, key=len, reverse=True))
            )

            data = replace_strings(data, replacements, pattern)
        if name == "incident":
            old = "0" * 64
            data = replace_strings(
                data,
                {old: hashlib.sha256((run_id + ":absent-lesson").encode()).hexdigest()},
                re.compile(old),
            )
        data["steps"] = http_steps(data)
        for step in data["steps"]:
            if step.get("webhook"):
                step["expected_status"] = 201
                step["request"]["agent_id"] = "pilot.normalized-github"
                step.pop("expected_authority", None)
                step["source_kind"] = (
                    "Authored normalized GitHub check payload; not webhook-route proof"
                )
        for query_case in data.get("queries", []):
            explicit = query_case.get("request", {})
            query_case["intent"] = explicit.get("intent", query_case.get("intent"))
            query_case["text"] = (
                explicit.get("query")
                or query_case.get("text")
                or (query_case["intent"] + " " + (query_case.get("seed") or ""))
            )
            query_case["seeds"] = explicit.get("seed_node_ids", query_case.get("seeds"))
            query_case.setdefault("required", query_case.get("required_nodes", []))
            query_case.setdefault("forbidden", [])
            query_case.setdefault("max_depth", explicit.get("max_depth", 5))
            if query_case["scenario"] == "CQ6-text-discovery":
                # The unchanged seedless question searches all retained features.
                # An empty-database exact-set oracle is invalid in this pilot.
                query_case["exact"] = False
                query_case["global_discovery"] = {
                    "matching_terms": ["fifteen", "minute"],
                    "allowed_edges": [
                        "REFINES",
                        "APPROVES",
                        "SUPERSEDES",
                        "IMPLEMENTS",
                        "REVIEWS",
                        "VERIFIES",
                        "EXECUTES",
                        "RAN_AGAINST",
                        "INCLUDES",
                        "DEPLOYS",
                        "DEPLOYED_TO",
                    ],
                }

        source_expectations = {}
        for step in data["steps"]:
            if step["expected_status"] < 400:
                for nid in fixture_observations(step):
                    source_expectations.setdefault(nid, []).append(step["request"]["event_id"])
        if name in {"planning", "connected"}:
            for query_case in data["queries"]:
                required = set(query_case["required"])
                query_case["expected_edges"] = sorted(
                    {
                        tuple(edge)
                        for step in data["steps"]
                        if step["expected_status"] < 400
                        for edge in step["expected_edges"]
                        if edge[1] in required and edge[2] in required
                    }
                )
        groups.append(
            {
                "name": name,
                "source_expectations": source_expectations,
                "tenant": "b",
                "steps": data["steps"],
                "queries": data.get("queries", []),
                "source_kind": data.get("source_kind", "Synthetic normalized producer inputs"),
            }
        )
    for tenant in ("a", "b"):
        agent, session = run_id + ":" + tenant + ":memory-owner", run_id + ":" + tenant + ":memory"
        start = datetime.now(UTC) - timedelta(minutes=5)
        steps = []

        def add(
            key,
            kind,
            payload,
            family,
            subject,
            props,
            session=session,
            agent=agent,
            steps=steps,
            start=start,
        ):
            eid = str(uuid5(NAMESPACE_URL, session + ":" + key))
            nid = identity(family, agent, "session", session, subject)
            steps.append(
                dict(
                    scenario=key,
                    request=dict(
                        event_id=eid,
                        event_type="memory." + kind,
                        occurred_at=(start + timedelta(seconds=len(steps))).isoformat(),
                        session_id=session,
                        agent_id=agent,
                        trace_id=run_id,
                        payload_ref="pilot-spectrum:" + key,
                        payload=payload,
                    ),
                    expected_status=201,
                    expected_node=nid,
                    expected_props=props,
                    expected_edges=[],
                    extra_nodes={},
                    memory_intent="when",
                )
            )
            return eid, nid

        belief = dict(
            key="expiry",
            belief_text="Reset tokens expire in fifteen minutes.",
            confidence=0.7,
            category="world_model",
        )
        stated, old_id = add(
            "belief-stated",
            "belief.stated",
            belief,
            "Belief",
            "expiry",
            dict(origin="stated", confirmation_count=1, state_revision=0),
        )
        add(
            "belief-confirmed",
            "belief.confirmed",
            dict(key="expiry", expected_revision=0),
            "Belief",
            "expiry",
            dict(confirmation_count=2, state_revision=1),
        )
        inferred, new_id = add(
            "belief-inferred",
            "belief.inferred",
            dict(
                belief, key="replacement", belief_text="Expiry is ten minutes after policy review."
            ),
            "Belief",
            "replacement",
            dict(origin="inferred", confirmation_count=0),
        )
        add(
            "belief-corrected",
            "belief.corrected",
            dict(
                key="expiry", replacement_key="replacement", expected_revision=1, contradicts=True
            ),
            "Belief",
            "expiry",
            dict(superseded_by=new_id, state_revision=2),
        )
        correction = steps[-1]
        correction["expected_edges"] = [
            (kind, new_id, old_id) for kind in ("SUPERSEDES", "CONTRADICTS")
        ]
        correction["expected_edge_properties"] = [
            [*edge, dict(method="declared", source_event_id=correction["request"]["event_id"])]
            for edge in correction["expected_edges"]
        ]
        for key, terminal in (
            ("study", "completed"),
            ("household", "abandoned"),
            ("delivery", "superseded"),
        ):
            add(
                key + "-created",
                "goal.created",
                dict(key=key, description="Finish " + key, priority=5),
                "Goal",
                key,
                dict(status="active", evidence_count=1),
            )
            if terminal == "superseded":
                add(
                    "replacement-created",
                    "goal.created",
                    dict(key="new-plan", description="Use revised plan"),
                    "Goal",
                    "new-plan",
                    dict(status="active"),
                )
            add(
                key + "-terminal",
                "goal." + terminal,
                dict(
                    key=key,
                    expected_revision=0,
                    **({"replacement_key": "new-plan"} if terminal == "superseded" else {}),
                ),
                "Goal",
                key,
                dict(status=terminal, evidence_count=2),
            )
        supersede = steps[-1]
        supersede["expected_edges"] = [
            (
                "SUPERSEDES",
                identity("Goal", agent, "session", session, "new-plan"),
                supersede["expected_node"],
            )
        ]
        supersede["expected_edge_properties"] = [
            [
                *supersede["expected_edges"][0],
                dict(method="declared", source_event_id=supersede["request"]["event_id"]),
            ]
        ]
        groups.append(
            dict(
                name=tenant + "-memory",
                tenant=tenant,
                steps=steps,
                queries=[],
                source_kind="Explicit attributed Memory actions; no prose inference",
                final_queries=[
                    dict(
                        query="What assumptions remain current?",
                        intent="beliefs",
                        session_id=session,
                        agent_id=agent,
                        required=[new_id],
                        forbidden=[old_id],
                    ),
                    dict(
                        query="What changed in the assumptions?",
                        intent="when",
                        session_id=session,
                        agent_id=agent,
                        required=[old_id, new_id],
                        forbidden=[],
                    ),
                ],
            )
        )
    stories = [
        (
            "coding",
            "Maya",
            (
                "I have used Python professionally for five years. I am beginning Rust "
                "and am not a Rust expert."
            ),
            "What skills and learning interests did Maya actually state?",
            True,
        ),
        (
            "contexts",
            "Ishan",
            (
                "In incident response, I prefer short bullet-point actions. During design "
                "reviews, I prefer detailed explanations with trade-offs."
            ),
            "What response preferences apply in incidents and design reviews?",
            True,
        ),
        (
            "research",
            "Nila",
            (
                "I am researching battery recycling. I prefer answers that distinguish "
                "evidence from speculation and cite sources."
            ),
            "How should evidence and uncertainty be presented to Nila?",
            True,
        ),
        (
            "travel",
            "Omar",
            (
                "When planning a trip, I prefer trains to flights. I need extra time "
                "between connections."
            ),
            "What should a travel assistant remember about Omar?",
            True,
        ),
        (
            "work-journal",
            "Priya",
            (
                "I prefer planning tasks in the morning. Today I finished the "
                "investigation but the rollout is still uncertain."
            ),
            "How should Priya plan tasks, and what is still uncertain?",
            True,
        ),
        (
            "household",
            "Sam",
            (
                "I prefer reminders the evening before a household appointment. "
                "Discussing a repair is not a commitment to doing it."
            ),
            "When should Sam receive reminders?",
            True,
        ),
        (
            "paraphrase",
            "Tara",
            (
                "Long walls of text are hard for me to use; two or three practical steps "
                "work much better."
            ),
            "How should an assistant format a response for Tara?",
            True,
        ),
        (
            "absence",
            "",
            (
                "This is a network diagnostic record. No personal preference, skill or "
                "commitment is stated."
            ),
            "Do we have evidence of a personal preference or commitment?",
            False,
        ),
    ]
    semantics = {
        "contexts": [
            ("positive", ["incident", "short|brief|concise|bullet"]),
            ("positive", ["design", "detail|trade"]),
        ],
        "research": [
            ("positive", ["evidence|source|citation|cite", "speculat|uncertain|evidence|source"])
        ],
        "travel": [
            ("positive", ["train|rail", "flight|air|travel"]),
            ("positive", ["time|buffer", "connect|transfer"]),
        ],
        "work-journal": [("positive", ["morning", "plan|task"])],
        "household": [("positive", ["evening|night", "remind|appointment"])],
        "paraphrase": [("positive", ["step|action", "practical|two|three|short|concise"])],
    }
    for key, name, content, question, expect_user in stories:
        session, agent = run_id + ":story:" + key, run_id + ":owner:" + key
        start = datetime.now(UTC) - timedelta(minutes=4)
        rows = []
        for suffix, kind, payload in (
            (
                "source",
                "observation.input",
                {"content": ("My name is " + name + ". " if name else "") + content},
            ),
            ("end", "system.session_end", {}),
        ):
            rows.append(
                dict(
                    scenario=key + "-" + suffix,
                    expected_status=201,
                    request=dict(
                        event_id=str(uuid5(NAMESPACE_URL, session + ":" + suffix)),
                        event_type=kind,
                        occurred_at=(start + timedelta(seconds=len(rows))).isoformat(),
                        session_id=session,
                        agent_id=agent,
                        trace_id=run_id,
                        payload_ref="pilot-story:" + key,
                        payload=payload,
                    ),
                )
            )
        groups.append(
            dict(
                name="user-" + key,
                tenant="a",
                user_story=True,
                queries=[],
                steps=rows,
                owner=agent,
                session=session,
                question=question,
                expect_user=expect_user,
                expected_name=name,
                preference_semantics=semantics.get(key, []),
                source_kind="Actual model interpretation of distinct application context",
            )
        )
    for tenant in ("a", "b"):
        for outcome, content in (
            ("forward", "Investigation completed; rollout uncertain."),
            ("inverse", "Investigation incomplete; rollout completed."),
        ):
            session = run_id + ":" + tenant + ":summary:" + outcome
            agent = run_id + ":" + tenant + ":summary-owner"
            start = datetime.now(UTC) - timedelta(minutes=4)
            rows = []
            for i, text in enumerate(
                (content, "This is a progress record, not a request to change those outcomes.")
            ):
                rows.append(
                    dict(
                        scenario="source-" + str(i),
                        expected_status=201,
                        request=dict(
                            event_id=str(uuid5(NAMESPACE_URL, session + ":" + str(i))),
                            event_type="observation.input",
                            occurred_at=(start + timedelta(seconds=i)).isoformat(),
                            session_id=session,
                            agent_id=agent,
                            trace_id=run_id,
                            payload_ref="pilot:summary:" + outcome,
                            payload={"content": text},
                        ),
                    )
                )
            members = sorted(step["request"]["event_id"] for step in rows)
            episode = (
                "episode-"
                + hashlib.sha256(
                    json.dumps([session, members], separators=(",", ":")).encode()
                ).hexdigest()
            )
            summary = (
                "summary-"
                + episode
                + "-"
                + hashlib.sha256("|".join(members).encode()).hexdigest()[:12]
            )
            groups.append(
                dict(
                    name=tenant + "-summary-" + outcome,
                    tenant=tenant,
                    steps=rows,
                    queries=[],
                    temporal_story=True,
                    session=session,
                    owner=agent,
                    episode=episode,
                    summary=summary,
                    members=members,
                    expected_source=content,
                    contrast=outcome,
                    source_kind="Contrasting prose outcomes through actual summary provider",
                )
            )
    for group in groups:
        if "source_expectations" not in group:
            group["source_expectations"] = {}
            for step in group["steps"]:
                if step["expected_status"] < 400:
                    for nid in fixture_observations(step):
                        group["source_expectations"].setdefault(nid, []).append(
                            step["request"]["event_id"]
                        )
    return {
        "groups": groups,
        "coverage": (
            "Planning/revisions; connected requirement-to-deployment; incident/lesson; "
            "all28 PDLC contracts; explicit Belief/Goal lifecycles in both tenants"
        ),
        "limits": [
            "This stage does not certify automatic prose-to-Memory inference, context selection, "
            "Entity ambiguity, external cohort access or independent human reproduction.",
            "G07 exhaustive malformed-field matrices and native webhook routes "
            "are not repeated here.",
        ],
    }


def summary_contrast_matches(text, outcome):
    """Narrow probe oracle; no cross-clause or negated completion matches."""
    clauses = re.split(r"[;,.!?\n]|\b(?:and|while|but)\b", text.lower())
    complete = re.compile(r"\b(?:complete|completed|finished|done)\b")
    negative = re.compile(r"\b(?:not|never|no|incomplete|unfinished|ongoing|uncertain|pending)\b")

    def subject_matches(subject, state):
        selected = [clause for clause in clauses if re.search(r"\b" + subject + r"\b", clause)]
        if state == "completed":
            return (
                bool(selected)
                and any(complete.search(c) for c in selected)
                and not any(negative.search(c) for c in selected)
            )
        if state == "incomplete":
            return any(
                re.search(r"\b(?:incomplete|unfinished|ongoing)\b|\bnot\b.{0,15}\bcompleted?\b", c)
                and not re.search(r"\bnot\b.{0,15}\b(?:incomplete|unfinished|ongoing)\b", c)
                for c in selected
            ) and not any(complete.search(c) and not negative.search(c) for c in selected)
        return any(
            re.search(r"\b(?:uncertain|pending|unresolved|unknown)\b", c)
            and not re.search(r"\bnot\b.{0,15}\b(?:uncertain|pending|unresolved|unknown)\b", c)
            for c in selected
        ) and not any(complete.search(c) and not negative.search(c) for c in selected)

    return subject_matches(
        "investigation", "completed" if outcome == "forward" else "incomplete"
    ) and subject_matches("rollout", "uncertain" if outcome == "forward" else "completed")


def discovery_eligibility(state, policy, depth):
    """Independent pre-query relevance oracle, not a whitelist of returned IDs."""
    nodes = {
        r[1]: json_value(r[2])
        for r in state["nodes"]
        if r[0]
        not in {"Event", "Entity", "Summary", "Episode", "UserProfile", "Preference", "Skill"}
    }
    matching = set()
    for nid, props in nodes.items():
        words = re.findall(r"[a-z]+", json.dumps(props).lower())
        if all(any(word.startswith(term) for word in words) for term in policy["matching_terms"]):
            matching.add(nid)
    adjacency = {}
    for _, source, kind, _, target, raw in state["edges"]:
        if (
            kind in policy["allowed_edges"]
            and source in nodes
            and target in nodes
            and json_value(raw).get("method") not in {"extracted", "inferred"}
        ):
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set()).add(source)
    eligible, frontier = set(matching), set(matching)
    for _ in range(depth):
        frontier = {
            target for source in frontier for target in adjacency.get(source, ())
        } - eligible
        eligible.update(frontier)
    return matching, eligible


async def execute(
    plan,
    *,
    request,
    check,
    databases,
    record,
    save,
    consumers,
    baselines=None,
    evidence_directory=None,
    recovery_hooks=None,
    restart=None,
    stale_probe=None,
):
    """Run frozen expectations; never derive an expected artifact from output."""
    from engram_pilot_completion_fixtures import declared_dead_letters, memory_subject_snapshot

    results = record.setdefault("spectrum", [])
    observations_by_event = {}

    def material_state(state):
        # Background consolidation/reads may refresh these explicitly permitted
        # derived fields. Source documents and declared domain artifacts cannot change.
        nodes = []
        for label, nid, raw in state["nodes"]:
            if label in {"Summary", "Episode"}:
                continue
            props = dict(json_value(raw))
            if label == "Event":
                for key in ("importance_score", "access_count", "last_accessed_at"):
                    props.pop(key, None)
            if label == "Entity":
                for key in ("last_seen", "mention_count"):
                    props.pop(key, None)
            nodes.append((label, nid, props))
        ids = {n[1] for n in nodes}
        values = {
            "events": state["events"],
            "nodes": nodes,
            "edges": [r for r in state["edges"] if r[1] in ids and r[4] in ids],
        }
        return {
            k: sorted(json.dumps(r, sort_keys=True, default=str) for r in rows)
            for k, rows in values.items()
        }

    async def settle():
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            lags = await asyncio.gather(*(w._subscription.lag() for w in consumers))
            states = {t: await asyncio.to_thread(snapshot, db) for t, db in databases.items()}
            if not any(lags) and all(
                not st["pending"] and declared_dead_letters(st, plan["groups"], t)
                for t, st in states.items()
            ):
                return states
            await asyncio.sleep(0.3)
        raise TimeoutError("Pilot workers did not settle before material no-write proof")

    async def wait_for(tenant, step):
        deadline = time.monotonic() + 180
        eid = step["request"]["event_id"]
        while time.monotonic() < deadline:
            state = await asyncio.to_thread(snapshot, databases[tenant])
            nodes = {r[1]: json_value(r[2]) for r in state["nodes"]}
            required = {**step.get("extra_nodes", {}), **step.get("node_assertions", {})}
            if step.get("expected_node"):
                required[step["expected_node"]] = step["expected_props"]
            actual_edges = {(r[2], r[1], r[4]) for r in state["edges"]}
            applicable = step.get("requires_pack_output", False) or step["request"][
                "event_type"
            ] in {
                "pdlc.design.section_changed",
                "pdlc.spec.approved",
            }
            outcomes = [r for r in record["worker_outcomes"] if r.get("event_id") == eid]
            invalid = any(r.get("event") == "pack_extraction_answer_invalid" for r in outcomes)
            if invalid:
                check(step["scenario"] + " no invalid model answer", False)
            applied = any(r.get("event") == "pack_extraction_applied" for r in outcomes)
            if (
                (not applicable or applied)
                and not state["pending"]
                and declared_dead_letters(state, plan["groups"], tenant)
                and eid in nodes
                and all(
                    nid in nodes and all(nodes[nid].get(k) == v for k, v in props.items())
                    for nid, props in required.items()
                )
                and {tuple(e) for e in step["expected_edges"]} <= actual_edges
            ):
                return state
            await asyncio.sleep(0.3)
        raise TimeoutError("Spectrum projection missing: " + step["scenario"])

    if any(g.get("recovery_proof") for g in plan["groups"]):
        from engram_pilot_recovery_proof import execute as execute_recovery

        return await execute_recovery(
            plan,
            request=request,
            check=check,
            record=record,
            save=save,
            databases=databases,
            evidence_directory=evidence_directory,
            hooks=recovery_hooks,
            restart=restart,
            stale_probe=stale_probe,
            settle=settle,
        )

    if any(g.get("tenant_proof") for g in plan["groups"]):
        from engram_pilot_tenant_proof import execute as execute_tenants

        return await execute_tenants(
            plan,
            request=request,
            check=check,
            record=record,
            save=save,
            settle=settle,
            databases=databases,
            evidence_directory=evidence_directory,
        )

    if any(g.get("retrieval_proof") for g in plan["groups"]):
        from engram_pilot_retrieval_proof import execute as execute_retrieval

        return await execute_retrieval(
            plan, request=request, check=check, record=record, save=save, settle=settle
        )

    if any(g.get("episode_history_retained") for g in plan["groups"]):
        from engram_pilot_episode_history import execute as execute_history

        return await execute_history(
            plan,
            request=request,
            check=check,
            record=record,
            save=save,
            settle=settle,
        )

    if plan["groups"] and all(g.get("temporal_story") for g in plan["groups"]):
        from engram_pilot_summary_proof import execute as execute_summaries

        return await execute_summaries(
            plan,
            request=request,
            check=check,
            databases=databases,
            record=record,
            save=save,
            settle=settle,
        )

    if any(g.get("episode_bridge") for g in plan["groups"]):
        from engram_pilot_episode_bridge import execute as execute_bridges

        await execute_bridges(
            plan,
            request=request,
            check=check,
            databases=databases,
            record=record,
            save=save,
            settle=settle,
        )
        return

    for group in plan["groups"]:
        tenant = group["tenant"]
        entry = {"group": group["name"], "tenant": tenant, "steps": [], "queries": []}
        results.append(entry)
        expected_nodes, expected_edges, artifact_events = {}, set(), {}
        group_events = {
            s["request"]["event_id"] for s in group["steps"] if s["expected_status"] < 400
        }
        save()

        def assert_public_sources(answer, required, state, group=group):
            events = {r[1]: json_value(r[2]) for r in state["nodes"] if r[0] == "Event"}
            for nid in required:
                expected = set(group.get("source_expectations", {}).get(nid, [])) & events.keys()
                if not expected:
                    continue  # Unobserved placeholders are checked by the authored query policy.
                newest = max(datetime.fromisoformat(events[e]["occurred_at"]) for e in expected)
                allowed = {
                    e
                    for e in expected
                    if datetime.fromisoformat(events[e]["occurred_at"]) == newest
                }
                provenance = answer["nodes"][nid].get("provenance") or {}
                eid = provenance.get("event_id")
                check(
                    group["name"] + " exact public source " + nid,
                    eid in allowed
                    and provenance.get("source") == "spanner"
                    and provenance.get("global_position") == events[eid]["global_position"],
                )

        async def execute_query(query_case, tenant=tenant, group=group, entry=entry):
            body = dict(
                query=query_case["text"],
                intent=query_case["intent"],
                seed_node_ids=query_case.get("seeds")
                or ([query_case["seed"]] if query_case.get("seed") else []),
                max_nodes=100,
                max_depth=query_case.get("max_depth", 6),
            )
            prior = await asyncio.to_thread(snapshot, databases[tenant])
            if query_case.get("global_discovery"):
                matching, eligible = discovery_eligibility(
                    prior, query_case["global_discovery"], body["max_depth"]
                )
                entry.setdefault("discovery_preconditions", {})[query_case["scenario"]] = {
                    "matching": sorted(matching),
                    "eligible": sorted(eligible),
                    "rules": query_case["global_discovery"],
                }
                save()
            code, answer = await request(tenant, "/v1/query/artifacts", body)
            required = set(query_case["required"])
            actual = set(answer.get("nodes", {}))
            check(
                group["name"] + ":" + query_case["scenario"],
                code == 200
                and required <= actual
                and not (set(query_case["forbidden"]) & actual)
                and (not query_case.get("exact") or actual == required)
                and not answer.get("meta", {}).get("truncated"),
            )
            edges = {(e["edge_type"], e["source"], e["target"]) for e in answer.get("edges", [])}
            check(
                group["name"] + ":" + query_case["scenario"] + " directed links",
                {tuple(e) for e in query_case.get("expected_edges", [])} <= edges,
            )
            for channel, expected in query_case.get("expected_channels", {}).items():
                check(
                    group["name"] + ":" + query_case["scenario"] + " channel " + channel,
                    answer.get("meta", {}).get("retrieval_channels", {}).get(channel) == expected,
                )
            if query_case.get("global_discovery"):
                check(group["name"] + " global discovery relevance", actual <= eligible)
                for kind, count in query_case.get("minimum_types", {}).items():
                    check(
                        group["name"] + " global discovery minimum " + kind,
                        sum(nid.startswith(kind + ":") for nid in actual) >= count,
                    )
                for kind, source_type, target_type in query_case.get("required_link_shapes", []):
                    check(
                        group["name"] + " global discovery linked " + kind,
                        any(
                            edge_kind == kind
                            and source in actual
                            and target in actual
                            and source.startswith(source_type + ":")
                            and target.startswith(target_type + ":")
                            for edge_kind, source, target in edges
                        ),
                    )
                events = {r[0] for r in prior["events"]}
                positions = {
                    r[1]: json_value(r[2]).get("global_position")
                    for r in prior["nodes"]
                    if r[0] == "Event"
                }
                for nid in actual - required:
                    provenance = answer["nodes"][nid].get("provenance") or {}
                    eid = provenance.get("event_id")
                    check(
                        group["name"] + " extra artifact accepted-source proof " + nid,
                        eid in events
                        and provenance.get("source") == "spanner"
                        and provenance.get("global_position") == positions.get(eid)
                        and any(
                            r[1] == nid and r[2] == "DERIVED_FROM" and r[4] == eid
                            for r in prior["edges"]
                        ),
                    )
            assert_public_sources(answer, required, prior)
            assert_retrieval_policy(answer, query_case)
            entry["queries"].append(
                {"scenario": query_case["scenario"], "required": sorted(required)}
            )
            save()

        if group.get("temporal_story"):
            for step in group["steps"]:
                status, _ = await request(tenant, "/v1/events", step["request"])
                check(group["name"] + " source admitted", status == 201)
                entry["steps"].append(
                    {"scenario": step["scenario"], "event_id": step["request"]["event_id"]}
                )
            await settle()
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                state = await asyncio.to_thread(snapshot, databases[tenant])
                nodes = {r[1]: json_value(r[2]) for r in state["nodes"]}
                if group["episode"] in nodes and group["summary"] in nodes:
                    break
                await asyncio.sleep(0.5)
            check(
                group["name"] + " scheduled Episode and Summary",
                group["episode"] in nodes and group["summary"] in nodes,
            )
            members = {
                r[4] for r in state["edges"] if r[1] == group["episode"] and r[2] == "CONTAINS"
            }
            derived = {
                r[4] for r in state["edges"] if r[1] == group["episode"] and r[2] == "DERIVED_FROM"
            }
            check(group["name"] + " exact membership", members == derived == set(group["members"]))
            calls = [
                call
                for call in record["provider_calls"]
                if group["expected_source"] in json.dumps(call.get("input_messages", []))
                and all(e in json.dumps(call.get("input_messages", [])) for e in group["members"])
            ]
            check(group["name"] + " actual provider saw matching source content", bool(calls))
            body = dict(
                query="What happened in this session, and what remains uncertain?",
                intent="when",
                session_id=group["session"],
                agent_id=group["owner"],
                max_nodes=100,
                timeout_ms=30000,
            )
            code, answer = await request(tenant, "/v1/query/subgraph", body)
            check(
                group["name"] + " temporal public read",
                code == 200
                and {group["episode"], group["summary"], *group["members"]}
                <= answer.get("nodes", {}).keys()
                and not answer.get("meta", {}).get("truncated"),
            )
            text = answer["nodes"][group["summary"]]["attributes"]["content"]
            check(
                group["name"] + " preserved opposing outcomes",
                summary_contrast_matches(text, group["contrast"]),
            )
            check(
                group["name"] + " persisted text matches returned provider output",
                any(
                    call.get("state") == "returned" and call.get("output") == text for call in calls
                ),
            )
            entry.update(
                state="passed exact source and contrast checks",
                summary_text=text,
                provider_calls=len(calls),
            )
            save()
            continue
        if group.get("user_correction"):
            from engram_pilot_completion_fixtures import (
                correction_expected_updates,
                verified_user_correction,
            )

            before = (
                baselines[tenant]
                if group.get("recover_user_inputs") or group.get("verify_user_inputs")
                else (await settle())[tenant]
            )
            inputs = (
                group.get("recover_user_inputs")
                or group.get("verify_user_inputs")
                or [s["request"] for s in group["steps"]]
            )
            for step in group["steps"]:
                code, _ = await request(tenant, "/v1/events", step["request"])
                check(group["name"] + ":" + step["scenario"] + " admission", code == 201)
            trigger = inputs[-1]["event_id"]
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                after = await asyncio.to_thread(snapshot, databases[tenant])
                props = next(
                    (json_value(n[2]) for n in after["nodes"] if n[:2] == ["Event", trigger]), {}
                )
                if props.get("user_extraction_status") == "applied":
                    break
                await asyncio.sleep(0.3)
            if group.get("verify_user_inputs"):
                receipt = verified_user_correction(after, group)
                check(group["name"] + " exact already-applied correction state", True)
            else:
                updates, receipt = correction_expected_updates(before, after, group)
                actual_nodes = {(n[0], n[1]): json_value(n[2]) for n in after["nodes"]}
                check(
                    group["name"] + " exact permitted predecessor/profile changes",
                    all(actual_nodes[k] == json_value(json.dumps(v)) for k, v in updates.items()),
                )
            old_id, new_id = group["expected_previous"], group["expected_replacement"]
            other = group["unrelated_preference"]
            expected_active = {new_id, other}
            base = "/v1/users/user:" + group["owner"]
            code, active = await request(tenant, base + "/preferences", method="GET", role="admin")
            check(
                group["name"] + " active public preferences exclude predecessor",
                code == 200 and {p["preference_id"] for p in active} == expected_active,
            )
            current_replacement = next(p for p in active if p["preference_id"] == new_id)
            check(
                group["name"] + " public negative identity fields",
                all(
                    current_replacement.get(k) == v
                    for k, v in group["identity_fields"].items()
                    if k != "about_entity"
                ),
            )
            code, history = await request(tenant, base + "/data-export", method="GET", role="admin")
            check(
                group["name"] + " public historical export retains revisions",
                code == 200
                and {p["preference_id"] for p in history["preferences"]} == {old_id, new_id, other},
            )
            source = inputs[0]["event_id"]
            check(
                group["name"] + " public correction provenance and exact receipt",
                receipt in history["extraction_receipts"]
                and all(
                    any(
                        p["source_id"] == nid and p["event_id"] == source
                        for p in history["provenance_chains"]
                    )
                    for nid in (old_id, new_id)
                ),
            )
            code, answer = await request(
                tenant,
                "/v1/query/subgraph",
                dict(
                    query=group["question"],
                    intent="personalize",
                    agent_id=group["owner"],
                    session_id=group["session"],
                    max_nodes=100,
                    timeout_ms=30000,
                ),
            )
            check(
                group["name"] + " composed current read and unchanged design context",
                code == 200
                and expected_active <= answer.get("nodes", {}).keys()
                and old_id not in answer["nodes"]
                and not answer.get("meta", {}).get("truncated"),
            )
            source_props = next(json_value(n[2]) for n in after["nodes"] if n[1] == source)
            check(
                group["name"] + " exact public correction source position",
                answer["nodes"].get(source, {}).get("provenance", {}).get("global_position")
                == source_props["global_position"],
            )
            check(
                group["name"] + " public owner evidence exclusion",
                all(
                    n["provenance"]["agent_id"] == group["owner"]
                    for n in answer["nodes"].values()
                    if n.get("provenance")
                ),
            )
            entry.update(
                state="passed explicit correction checks",
                receipt=receipt,
                active_preferences=active,
                history_export=history,
                composed_read=answer,
            )
            save()
            continue
        if group.get("user_story"):
            entity_baseline = None
            if group.get("preserve_entity_origins"):
                entity_baseline = await asyncio.to_thread(snapshot, databases[tenant])
            for step in group["steps"]:
                status, _ = await request(tenant, "/v1/events", step["request"])
                check(group["name"] + ":" + step["scenario"] + " admission", status == 201)
            inputs = (
                group.get("recover_user_inputs")
                or group.get("verify_user_inputs")
                or [s["request"] for s in group["steps"]]
            )
            source, end = [row["event_id"] for row in inputs]
            deadline = time.monotonic() + 180
            receipt = None
            while time.monotonic() < deadline:
                state = await asyncio.to_thread(snapshot, databases[tenant])
                trigger = next(
                    (json_value(r[2]) for r in state["nodes"] if r[:2] == ["Event", end]), {}
                )
                receipt = trigger.get("user_extraction_receipt")
                if receipt and receipt.get("status") == "applied":
                    break
                await asyncio.sleep(0.3)
            check(
                group["name"] + " actual extraction applied",
                bool(receipt) and receipt.get("status") == "applied",
            )
            if group.get("recover_user_inputs") or group.get("verify_user_inputs"):
                from engram_pilot_completion_fixtures import verified_recovered_user_receipt

                verified_recovered_user_receipt(state, group)
                check(group["name"] + " exact original-source applied receipt validated", True)
            extracted = receipt["result"]
            entry["extraction"] = extracted
            check(
                group["name"] + " Luna and exact owner",
                extracted["model_id"] == "gpt-6-luna"
                and receipt["owner"] == "user:" + group["owner"],
            )
            prefs, skills = extracted["preferences"], extracted["skills"]
            for nid in group.get("preserve_entity_origins", []):
                original = next(
                    json_value(n[2]) for n in entity_baseline["nodes"] if n[:2] == ["Entity", nid]
                )
                current = next(json_value(n[2]) for n in state["nodes"] if n[:2] == ["Entity", nid])
                check(
                    group["name"] + " reobserved Entity origin and stored count preserved",
                    all(
                        original.get(k) == current.get(k)
                        for k in ("name", "entity_type", "first_seen", "mention_count")
                    )
                    and any(e["name"] == original["name"] for e in extracted["entities"])
                    and any(
                        e[:5] == ["Event", source, "REFERENCES", "Entity", nid]
                        for e in state["edges"]
                    ),
                )
            for polarity, expressions in group["preference_semantics"]:
                check(
                    group["name"] + " stated preference meaning " + str(expressions),
                    any(
                        p["polarity"] == polarity
                        and all(
                            re.search(
                                expression,
                                " ".join(str(p.get(k, "")) for k in ("key", "context")).lower(),
                            )
                            for expression in expressions
                        )
                        for p in prefs
                    ),
                )
            if group["expect_user"]:
                check(
                    group["name"] + " attributed profile",
                    bool(extracted["persona"])
                    and extracted["persona"]["name"] == group["expected_name"],
                )
                if group["name"] == "user-coding":
                    check(
                        "Python skill and Rust non-expertise",
                        any("python" in s["name"].lower() for s in skills)
                        and not any(
                            "rust" in s["name"].lower() and s["proficiency"] > 0.8 for s in skills
                        ),
                    )
                elif group.get("expect_preferences", True):
                    check(group["name"] + " useful preference", bool(prefs))
                else:
                    check(
                        group["name"]
                        + " no preference/skill/interest attributed from descriptive prose",
                        not prefs and not skills and not extracted["interests"],
                    )
                if group["name"] == "user-contexts":
                    contexts = [p.get("context", "").lower() for p in prefs]
                    check(
                        "distinct incident/design preference contexts",
                        len(prefs) >= 2
                        and any("incident" in c for c in contexts)
                        and any("design" in c for c in contexts),
                    )
            else:
                check("absence is not a preference, skill or interest", not prefs and not skills)
            check(
                group["name"] + " exact quote-supported membership",
                all(item["support_event_ids"] == [source] for item in [*prefs, *skills]),
            )
            body = dict(
                query=group["question"],
                intent="personalize",
                session_id=group["session"],
                agent_id=group["owner"],
                max_nodes=100,
                timeout_ms=30000,
            )
            code, answer = await request(tenant, "/v1/query/subgraph", body)
            required = {p["preference_id"] for p in prefs} | {k["skill_id"] for k in skills}
            if group["expect_user"]:
                required.add("profile:user:" + group["owner"])
            check(
                group["name"] + " natural wording public read",
                code == 200
                and required <= answer.get("nodes", {}).keys()
                and not answer.get("meta", {}).get("truncated"),
            )
            check(
                group["name"] + " no foreign owner evidence",
                all(
                    n.get("provenance", {}).get("agent_id") == group["owner"]
                    for n in answer["nodes"].values()
                    if n.get("provenance")
                ),
            )
            check(
                group["name"] + " no inferred Memory commitment",
                not any(
                    r[0] in {"Goal", "Belief"}
                    and json_value(r[2]).get("agent_id") == group["owner"]
                    for r in state["nodes"]
                ),
            )
            source_node = answer.get("nodes", {}).get(source)
            if required:
                source_props = next(json_value(r[2]) for r in state["nodes"] if r[1] == source)
                check(
                    group["name"] + " exact public source position",
                    bool(source_node)
                    and source_node["provenance"]["event_id"] == source
                    and source_node["provenance"]["global_position"]
                    == source_props["global_position"],
                )
            for diagnostic in group.get("diagnostic_queries", []):
                query_body = {
                    **body,
                    "query": diagnostic["query"],
                    "intent": diagnostic["intent"],
                }
                code, diagnostic_answer = await request(tenant, "/v1/query/subgraph", query_body)
                check(group["name"] + " diagnostic read completed", code == 200)
                entry.setdefault("diagnostics", []).append(
                    {
                        "request": query_body,
                        "response": diagnostic_answer,
                        "verdict": (
                            "observed diagnostic; "
                            "not proof of context selection or name disambiguation"
                        ),
                    }
                )
                save()
            entry["state"] = "passed selected semantic/source checks"
            save()
            continue
        for step in group["steps"]:
            label = group["name"] + ":" + step["scenario"]
            before = (await settle())[tenant]
            status, body = await request(tenant, "/v1/events", step["request"])
            check(label + " admission", status == step["expected_status"], status)
            entry["steps"].append(
                {
                    "scenario": step["scenario"],
                    "status": status,
                    "event_id": step["request"]["event_id"],
                }
            )
            save()
            duplicate = (
                step.get("duplicate")
                or (tenant, step["request"]["event_id"]) in observations_by_event
            )
            if status >= 400 or duplicate:
                after = (await settle())[tenant]
                check(label + " no material write", material_state(before) == material_state(after))
                if duplicate and status < 400:
                    original = next(
                        json_value(r[2])
                        for r in before["nodes"]
                        if r[1] == step["request"]["event_id"]
                    )
                    check(
                        label + " original receipt",
                        body.get("global_position") == original["global_position"],
                    )
                if step.get("absence_id"):
                    check(
                        label + " absent artifact",
                        not any(r[1] == step["absence_id"] for r in after["nodes"]),
                    )
            if status >= 400:
                for query_case in group["queries"]:
                    if query_case.get("after_scenario") == step["scenario"]:
                        await execute_query(query_case)
                continue
            if step.get("expected_worker_rejection"):
                deadline = time.monotonic() + 180
                key = [step["expected_worker_rejection"]["group"], step["request"]["event_id"]]
                while time.monotonic() < deadline:
                    state = await asyncio.to_thread(snapshot, databases[tenant])
                    if key in state["dead_letters"] and declared_dead_letters(
                        state, plan["groups"], tenant
                    ):
                        break
                    await asyncio.sleep(0.3)
                check(
                    label + " exact bound dead letter and conflict diagnostic",
                    key in state["dead_letters"]
                    and declared_dead_letters(state, plan["groups"], tenant),
                )
                source_node = next(json_value(r[2]) for r in state["nodes"] if r[1] == key[1])
                check(
                    label + " DLQ position equals admitted position",
                    source_node["global_position"] == body["global_position"],
                )
            state = await wait_for(tenant, step)
            state = (await settle())[tenant]
            if step.get("unchanged_subject"):
                subject = step["unchanged_subject"]
                check(
                    label + " exact subject and incident evidence unchanged",
                    memory_subject_snapshot(before, subject)
                    == memory_subject_snapshot(state, subject),
                )
            for proposed in step.get("required_proposed_edges", []):
                matches = [
                    json_value(row[5])
                    for row in state["edges"]
                    if (row[2], row[1], row[4])
                    == (proposed["kind"], proposed["source"], proposed["target"])
                ]
                check(
                    label + " exact proposed link",
                    len(matches) == 1
                    and matches[0].get("method") == proposed["method"]
                    and matches[0].get("link_status") == proposed["link_status"],
                    matches,
                )
            assert_forbidden_edges(state, step)
            observed = observations_by_event.setdefault(
                (tenant, step["request"]["event_id"]), fixture_observations(step)
            )
            declared_ids = set(expected_nodes) | set(step.get("extra_nodes", {}))
            if step.get("expected_node"):
                declared_ids.add(step["expected_node"])
            actual_sources = {
                (r[1], r[4])
                for r in state["edges"]
                if r[2] == "DERIVED_FROM"
                and r[4] == step["request"]["event_id"]
                and r[1] in declared_ids
            }
            check(
                label + " exact source evidence",
                actual_sources == {(n, step["request"]["event_id"]) for n in observed},
            )
            for kind, source, target, props in step.get("expected_edge_properties", []):
                matches = [
                    json_value(r[5])
                    for r in state["edges"]
                    if (r[2], r[1], r[4]) == (kind, source, target)
                ]
                expected = {
                    k: body.get("global_position") if v == "$receipt" else v
                    for k, v in props.items()
                }
                check(
                    label + " edge properties",
                    len(matches) == 1 and all(matches[0].get(k) == v for k, v in expected.items()),
                )
            nid = step.get("expected_node")
            if nid:
                expected_nodes[nid] = step["expected_props"]
            expected_nodes.update(step.get("extra_nodes", {}))
            for existing, props in step.get("node_assertions", {}).items():
                expected_nodes[existing] = {**expected_nodes[existing], **props}
            expected_edges.update(tuple(e) for e in step["expected_edges"])
            for oid in observed:
                artifact_events.setdefault(oid, set()).add(step["request"]["event_id"])
            actual_nodes = {r[1]: json_value(r[2]) for r in state["nodes"]}
            check(
                label + " cumulative properties",
                all(
                    n in actual_nodes and all(actual_nodes[n].get(k) == v for k, v in props.items())
                    for n, props in expected_nodes.items()
                ),
            )
            authored_sources = {
                r[1] for r in state["edges"] if r[2] == "DERIVED_FROM" and r[4] in group_events
            }
            actual_declared = {
                r[1]
                for r in state["nodes"]
                if r[1] in authored_sources
                and r[0]
                not in {
                    "Event",
                    "Entity",
                    "Summary",
                    "Episode",
                    "UserProfile",
                    "Preference",
                    "Skill",
                }
                and json_value(r[2]).get("method") not in {"extracted", "inferred"}
            }
            check(
                label + " no unexpected declared artifacts", actual_declared <= set(expected_nodes)
            )
            proposals = {
                r[1]
                for r in state["nodes"]
                if r[1] in authored_sources
                and json_value(r[2]).get("method") in {"extracted", "inferred"}
            }
            check(
                label + " proposals retain accepted sources",
                all(
                    any(
                        r[1] == nid and r[2] == "DERIVED_FROM" and r[4] in group_events
                        for r in state["edges"]
                    )
                    for nid in proposals
                ),
            )
            entry.setdefault("model_proposals", {})[step["scenario"]] = sorted(proposals)
            scope_ids = set(expected_nodes) | actual_declared
            actual_links = {
                (r[2], r[1], r[4])
                for r in state["edges"]
                if (r[1] in scope_ids or r[4] in scope_ids)
                and r[2] not in {"DERIVED_FROM", "SIMILAR_TO", "RELATED_TO"}
                and json_value(r[5]).get("method") not in {"inferred", "extracted"}
            }
            check(label + " cumulative declared links", actual_links == expected_edges)
            sources = {
                (r[1], r[4])
                for r in state["edges"]
                if r[2] == "DERIVED_FROM" and r[1] in artifact_events
            }
            check(
                label + " cumulative exact source membership",
                sources == {(n, e) for n, events in artifact_events.items() for e in events},
            )
            for placeholder in step.get("placeholders", []):
                check(
                    label + " placeholder has no false evidence",
                    not any(r[1] == placeholder and r[2] == "DERIVED_FROM" for r in state["edges"]),
                )
            if step.get("memory_intent"):
                query = dict(
                    query="Show this explicit Memory action and its history",
                    intent="when",
                    session_id=step["request"]["session_id"],
                    agent_id=step["request"]["agent_id"],
                    max_nodes=100,
                    timeout_ms=30000,
                )
                route = "/v1/query/subgraph"
            elif nid:
                query = dict(
                    query="Inspect this artifact",
                    intent="status",
                    seed_node_ids=[nid],
                    max_nodes=100,
                )
                route = "/v1/query/artifacts"
            else:
                query = dict(
                    query="Show the recorded event",
                    intent="what",
                    seed_nodes=[step["request"]["event_id"]],
                    session_id=step["request"]["session_id"],
                    agent_id=step["request"]["agent_id"],
                    max_nodes=30,
                    timeout_ms=30000,
                )
                route = "/v1/query/subgraph"
            code, answer = await request(tenant, route, query)
            key = nid or step["request"]["event_id"]
            check(label + " public read", code == 200 and key in answer.get("nodes", {}))
            if nid:
                assert_public_sources(answer, {nid}, state)
                check(
                    label + " public properties",
                    all(
                        answer["nodes"][nid]["attributes"].get(k) == v
                        for k, v in step["expected_props"].items()
                    ),
                )
            if step.get("memory_intent"):
                public_edges = {
                    (e["edge_type"], e["source"], e["target"]) for e in answer.get("edges", [])
                }
                check(
                    label + " public declared lifecycle links",
                    {tuple(e) for e in step["expected_edges"]} <= public_edges,
                )
                check(
                    label + " public exact action evidence",
                    all(
                        ("DERIVED_FROM", oid, step["request"]["event_id"]) in public_edges
                        for oid in observed
                    ),
                )
            if step.get("public_memory_guard"):
                guard = step["public_memory_guard"]
                guard_query = dict(
                    query="Show the delivery Goal and its evidence",
                    intent="when",
                    session_id=step["request"]["session_id"],
                    agent_id=step["request"]["agent_id"],
                    max_nodes=100,
                    timeout_ms=30000,
                )
                guard_code, guard_answer = await request(tenant, "/v1/query/subgraph", guard_query)
                props = (
                    guard_answer.get("nodes", {}).get(guard["node_id"], {}).get("attributes", {})
                )
                check(
                    label + " public Memory state unchanged by PDLC",
                    guard_code == 200
                    and not guard_answer.get("meta", {}).get("truncated")
                    and all(props.get(k) == v for k, v in guard["attributes"].items()),
                )
                assert_public_sources(guard_answer, {guard["node_id"]}, state)
            entry["queries"].append({"scenario": label, "route": route, "required": key})
            save()
            for query_case in group["queries"]:
                if query_case.get("after_scenario") == step["scenario"]:
                    await execute_query(query_case)
        for query_case in group["queries"]:
            if not query_case.get("after_scenario"):
                await execute_query(query_case)
        if group.get("model_proposal_check"):
            policy = group["model_proposal_check"]
            state = await asyncio.to_thread(snapshot, databases[tenant])
            proposed_ids = {
                row[1]
                for row in state["edges"]
                if row[0] == policy["required_type"]
                and row[2] == "DERIVED_FROM"
                and row[4] == policy["event_id"]
            }
            properties = {row[1]: json_value(row[2]) for row in state["nodes"]}
            check(
                group["name"] + " model proposals distinct from accepted decision",
                bool(proposed_ids)
                and policy["accepted_decision"] not in proposed_ids
                and all(properties[n].get("status") == policy["status"] for n in proposed_ids)
                and properties[policy["accepted_decision"]].get("status") == "accepted",
            )
            code, answer = await request(
                tenant,
                "/v1/query/artifacts",
                dict(
                    query="status",
                    intent="status",
                    seed_node_ids=sorted(proposed_ids),
                    max_nodes=100,
                ),
            )
            check(
                group["name"] + " proposed choices publicly retrievable",
                code == 200
                and all(
                    n in answer.get("nodes", {})
                    and answer["nodes"][n]["attributes"].get("status") == policy["status"]
                    for n in proposed_ids
                ),
            )
            accepted = {row[0] for row in state["events"]}
            event_positions = {
                row[1]: json_value(row[2]).get("global_position")
                for row in state["nodes"]
                if row[0] == "Event"
            }
            for nid in proposed_ids:
                provenance = answer["nodes"][nid].get("provenance") or {}
                source = provenance.get("event_id")
                check(
                    group["name"] + " public proposal accepted-source membership " + nid,
                    source in accepted
                    and provenance.get("source") == "spanner"
                    and provenance.get("global_position") == event_positions.get(source)
                    and any(
                        row[1] == nid and row[2] == "DERIVED_FROM" and row[4] == source
                        for row in state["edges"]
                    ),
                )
            entry["model_proposal_contrast"] = {
                "proposed": sorted(proposed_ids),
                "accepted": policy["accepted_decision"],
            }
            save()
        for query_case in group.get("final_queries", []):
            body = {
                k: v
                for k, v in query_case.items()
                if k not in {"required", "forbidden", "expected_edges", "forbidden_edges"}
            }
            body.update(max_nodes=100, timeout_ms=30000)
            code, answer = await request(tenant, "/v1/query/subgraph", body)
            check(
                group["name"] + ":" + body["intent"] + " current/history",
                code == 200
                and set(query_case["required"]) <= answer.get("nodes", {}).keys()
                and not set(query_case["forbidden"]) & answer.get("nodes", {}).keys(),
            )
            public_edges = {
                (e["edge_type"], e["source"], e["target"]) for e in answer.get("edges", [])
            }
            check(
                group["name"] + ":" + body["intent"] + " public Memory lifecycle links",
                {tuple(e) for e in query_case.get("expected_edges", [])} <= public_edges
                and not {tuple(e) for e in query_case.get("forbidden_edges", [])} & public_edges,
            )
            if group.get("source_expectations"):
                state = await asyncio.to_thread(snapshot, databases[tenant])
                assert_public_sources(answer, set(query_case["required"]), state)
            check(
                group["name"] + ":" + body["intent"] + " Memory owner exclusions",
                all(
                    n.get("attributes", {}).get("agent_id") == body["agent_id"]
                    for n in answer.get("nodes", {}).values()
                    if n.get("node_type") in {"Goal", "Belief"}
                ),
            )
        entry["state"] = "passed selected scenarios"
        save()

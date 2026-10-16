"""P08 bounded public retrieval probes and transparent native-vector observation."""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from engram_pilot_completion_fixtures import decoded_snapshot_cell as decode
from engram_pilot_completion_fixtures import p04_negative_proof, recovery_documents


def freeze(run_id):
    start = datetime.now(UTC) - timedelta(minutes=6)
    groups = []

    def event(t, key, kind, payload, **more):
        return dict(
            scenario=key,
            expected_status=201,
            expected_edges=[],
            request=dict(
                event_id=str(uuid5(NAMESPACE_URL, run_id + ":" + t + ":" + key)),
                event_type=kind,
                occurred_at=(start + timedelta(seconds=len(groups) * 10)).isoformat(),
                session_id=run_id + ":" + t + ":" + key.split("-")[0],
                agent_id=run_id + ":" + t + ":retrieval-owner",
                trace_id=run_id,
                payload_ref="pilot-p08:" + key,
                payload=payload,
            ),
            **more,
        )

    repo = "pilot/" + run_id + "/vega"
    title = "VegaLedger rejects expired reconciliation tokens"
    change, case, run = "Change:" + repo + "|7", "TestCase:" + repo + "|expiry", "TestRun:" + run_id
    steps = [
        event(
            "b",
            "chain-change",
            "pdlc.change.created",
            dict(repo=repo, number=7, title=title, head_sha="abc123"),
        ),
        event(
            "b",
            "chain-test",
            "pdlc.testcaserun.finished",
            dict(
                repo=repo,
                test_id="expiry",
                run_id=run_id,
                outcome="failure",
                name="VegaLedger rejects expired reconciliation tokens",
                path="tests/test_expiry.py",
                commit_sha="abc123",
                change_number=7,
            ),
        ),
        event(
            "b",
            "control-change",
            "pdlc.change.created",
            dict(
                repo=repo + "-control",
                number=7,
                title="Newsletter renders the welcome banner",
                head_sha="def456",
            ),
        ),
    ]
    trust_title = "OrionVault enforces archive retention duration"
    trusted, untrusted = "Change:" + repo + "-trusted|9", "Change:" + repo + "-untrusted|9"
    steps.extend(
        [
            event(
                "b",
                "trust-trusted",
                "pdlc.change.created",
                dict(repo=repo + "-trusted", number=9, title=trust_title, head_sha="abc123"),
            ),
            event(
                "b",
                "trust-untrusted",
                "pdlc.change.created",
                dict(repo=repo + "-untrusted", number=9, title=trust_title, head_sha="abc123"),
                role="untrusted",
            ),
        ]
    )
    groups.append(
        dict(
            name="p08-artifacts",
            tenant="b",
            retrieval_proof=True,
            steps=steps,
            queries=[],
            change=change,
            case=case,
            run=run,
            control="Change:" + repo + "-control|7",
            title=title,
            paraphrase=(
                "Which change prevents stale credentials from being accepted "
                "during payment reconciliation?"
            ),
            trust_title=trust_title,
            trusted=trusted,
            untrusted=untrusted,
            retained_negative_proofs=[p04_negative_proof()],
        )
    )
    for t in ("a", "b"):
        name = "VegaLedger" if t == "a" else "OrionVault"
        prose = event(
            t,
            "entity-source",
            "observation.input",
            dict(
                content=(
                    f"{name} is the name of our payment reconciliation service. "
                    f"{name} validates settlement records before posting them. "
                    "This describes a software service, not a personal preference."
                )
            ),
        )
        end = event(t, "entity-end", "system.session_end", {})
        groups.append(
            dict(
                name="p08-vector-" + t,
                tenant=t,
                retrieval_proof=True,
                steps=[prose, end],
                queries=[],
                entity_name=name,
                source_id=prose["request"]["event_id"],
                vector_query=name + " payment reconciliation service",
                absent_query="What proves QuasarNebula retention override was approved?",
                absent_seed="Change:pilot/" + run_id + "/absent|999",
            )
        )
    return dict(
        coverage=(
            "P08 exact/wording/paraphrase/budgets/native vector participation/trust/absence; "
            "not ANN performance or universal discovery"
        ),
        groups=groups,
    )


def observe_vectors(child, tenant, record, save):
    """Observe the exact executing request without changing results or failures."""
    context = ContextVar("p08-vector-" + tenant, default=None)
    engine = child.state.retrieval
    graph = child.state.graph_store
    original_read = engine.get_subgraph
    original_nearest = engine._vector_index.nearest
    original_seeds = engine._get_vector_seeds
    original_query = graph._query

    async def read(query):
        rows = record.setdefault("vector_observations", [])
        row = dict(
            id=f"vector-{tenant}-{len(rows)}",
            tenant=tenant,
            query=query.model_dump(mode="json"),
            ann=[],
            nearest=[],
            seeds=[],
        )
        rows.append(row)
        token = context.set(row)
        try:
            result = await original_read(query)
            row["state"] = "returned"
            return result
        except BaseException as exc:
            row.update(state="failed", error_type=type(exc).__name__)
            raise
        finally:
            context.reset(token)
            save()

    async def nearest(embedding, **kwargs):
        result = await original_nearest(embedding, **kwargs)
        if (row := context.get()) is not None:
            row["nearest"].append(
                dict(
                    embedding=list(embedding),
                    arguments=kwargs,
                    hits=[
                        dict(id=h.id, rank=h.rank, score=h.score, fields=h.fields) for h in result
                    ],
                )
            )
        return result

    async def seeds(embedding, limit):
        result = await original_seeds(embedding, limit)
        if (row := context.get()) is not None:
            row["seeds"].append(
                dict(
                    embedding=list(embedding) if embedding is not None else None,
                    limit=limit,
                    events=result,
                )
            )
        return result

    async def query(*args, **kwargs):
        result = await original_query(*args, **kwargs)
        if (row := context.get()) is not None and args and "APPROX_COSINE_DISTANCE" in args[0]:
            row["ann"].append(
                dict(
                    sql=args[0],
                    parameters=args[1],
                    dimensions=graph._dimensions,
                    rows=[[nid, decode(props), distance] for nid, props, distance in result],
                )
            )
        return result

    engine.get_subgraph, engine._vector_index.nearest = read, nearest
    engine._get_vector_seeds, graph._query = seeds, query


@lru_cache(maxsize=1)
def pilot_pdlc_registry():
    from context_graph.ontology import load_registry

    return load_registry(["pdlc"], builtin_packs=["core", "memory"])


def unresolved_reference_evidence(nid, node, body, state, saved):
    """Validate an explicit reference, never a sourced artifact/status claim."""
    from context_graph.domain.event_acceptance import EventAcceptance
    from context_graph.domain.models import Event
    from context_graph.domain.pack_projection import PackProjector, is_reference_stub

    registry = pilot_pdlc_registry()
    kind = registry.node_types.get(node["node_type"])
    props = saved.get((node["node_type"], nid), {})
    if (
        kind is None
        or not is_reference_stub(kind, props)
        or props["ontology_version"] != registry.version
    ):
        return False
    expected = {k: v for k, v in props.items() if k not in {"status", "status_changed_at"}}
    expected["reference_state"] = "unresolved"
    if node.get("attributes") != expected or any(
        r[1] == nid and r[2] == "DERIVED_FROM" for r in state["edges"]
    ):
        return False
    stored_edges = {tuple(r[:5]): decode(r[5]) for r in state["edges"]}
    ledger = {
        r[0]: (decode(r[1]), decode(r[2]))
        for r in state["events"]
        if len(r) > 2 and r[2] is not None
    }
    for edge in body.get("edges", []):
        if nid not in (edge["source"], edge["target"]):
            continue
        source, target = body["nodes"][edge["source"]], body["nodes"][edge["target"]]
        key = (
            source["node_type"],
            edge["source"],
            edge["edge_type"],
            target["node_type"],
            edge["target"],
        )
        if stored_edges.get(key) != edge["properties"]:
            continue
        neighbor = edge["target"] if edge["source"] == nid else edge["source"]
        declaring_events = {
            r[4]
            for r in state["edges"]
            if r[1] == neighbor and r[2] == "DERIVED_FROM" and r[3] == "Event"
        }
        for eid in declaring_events & ledger.keys():
            document, raw_acceptance = ledger[eid]
            event = Event.model_validate(document, strict=False)
            acceptance = EventAcceptance.model_validate(raw_acceptance)
            acceptance.require_same_request(acceptance, event, document.get("payload"))
            projected_event = saved.get(("Event", eid), {})
            if not projected_event.get("global_position"):
                continue
            document = {**document, "global_position": projected_event["global_position"]}
            event = event.model_copy(update={"global_position": projected_event["global_position"]})
            projector = PackProjector(
                registry,
                frozenset({event.agent_id})
                if acceptance.source_id == "demo.query"
                else frozenset(),
            )
            plan = projector.plan(event, document)
            if any(
                (e.source.label, e.source.key, e.edge_type, e.target.label, e.target.key) == key
                and all(edge["properties"].get(k) == v for k, v in e.properties.items())
                for e in plan.edges
            ):
                return True
    return False


def closed_response(body, state):
    """Event receipts or an Entity's stored REFERENCES path establish provenance."""
    nodes = body.get("nodes", {})
    saved = {(r[0], r[1]): decode(r[2]) for r in state["nodes"]}
    if any(e["source"] not in nodes or e["target"] not in nodes for e in body.get("edges", [])):
        return False

    def receipt(node):
        p = node.get("provenance")
        return bool(
            p
            and ("Event", p["event_id"]) in saved
            and p["global_position"] == saved[("Event", p["event_id"])].get("global_position")
            and p["source"] == "spanner"
        )

    stored_refs = {
        (r[1], r[4])
        for r in state["edges"]
        if r[0] == "Event" and r[2] == "REFERENCES" and r[3] == "Entity"
    }
    for nid, node in nodes.items():
        if node.get("provenance") is not None:
            if not receipt(node):
                return False
        elif node["node_type"] == "Entity":
            props = saved.get(("Entity", nid), {})
            if props.get("entity_id") != nid or not all(
                props.get(k) == v for k, v in node["attributes"].items()
            ):
                return False
            if not any(
                e["edge_type"] == "REFERENCES"
                and e["target"] == nid
                and (e["source"], nid) in stored_refs
                and nodes[e["source"]]["node_type"] == "Event"
                and receipt(nodes[e["source"]])
                for e in body.get("edges", [])
            ):
                return False
        elif node.get("attributes", {}).get("reference_state") == "unresolved":
            if not unresolved_reference_evidence(nid, node, body, state, saved):
                return False
        else:
            return False
    return True


def retained_sources(plan, states):
    """Pin the failed full-flow evidence and unchanged accepted records before reads."""
    proof = plan["retained_retrieval_proof"]
    root = Path(__file__).resolve().parents[1]
    directory = (root / proof["directory"]).resolve()
    expected_files = {
        "results.json",
        "fixtures.json",
        "reproduction-manifest.json",
        "recorded-source-audit.json",
        "a-final-state.json",
        "b-final-state.json",
    }
    if not directory.is_relative_to(root) or set(proof["sha256"]) != expected_files:
        raise ValueError("Exact retained P08 evidence pins are required")
    docs = {}
    for name, digest in proof["sha256"].items():
        raw = (directory / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("Retained proof changed: " + name)
        docs[name] = json.loads(raw)
    r = docs["results.json"]
    audit = docs["recorded-source-audit.json"]
    manifest = docs["reproduction-manifest.json"]
    if (
        r["state"] != "failed"
        or r.get("shutdown_errors") != []
        or r.get("finalization_errors")
        or {c["name"] for c in r["checks"] if not c["passed"]}
        != {
            "p08-vector-a endpoint/source closure",
            "actual provider calls returned after cooperative shutdown",
        }
        or not audit["all_match"]
        or audit["git_revision"] != manifest["git_revision"]
        or len(audit["files"]) != len(manifest["source_sha256"])
        or not all(
            f["matches"]
            and f["expected_sha256"]
            == f["committed_sha256"]
            == manifest["source_sha256"].get(f["path"])
            for f in audit["files"]
        )
    ):
        raise ValueError("Retained original is not the reviewed P08 failure/source proof")
    workers = {(w["tenant"], w["type"]) for w in r["workers"]}
    if workers != {
        (t, k)
        for t in ("a", "b")
        for k in ("projection", "extraction", "enrichment", "consolidation", "pack_extraction")
    }:
        raise ValueError("Original worker evidence incomplete")
    required_checks = {
        t + " " + suffix
        for t in ("a", "b")
        for suffix in (
            "final exact ledger append and retained owner",
            "prior graph preserved except approved derived refresh",
            "exact prior Episode membership retained",
            "final zero pending and exactly declared DLQ",
        )
    }
    if not required_checks <= {c["name"] for c in r["checks"] if c["passed"]}:
        raise ValueError("Original preservation proof incomplete")
    if len([q for q in r["requests"] if q["path"] == "/v1/events" and q["status"] == 201]) != 9:
        raise ValueError("Original accepted input inventory changed")
    original = docs["fixtures.json"]["spectrum"]["groups"]
    if len(original) != len(plan["groups"]):
        raise ValueError("Retained groups changed")
    for g, old in zip(plan["groups"], original, strict=True):
        if (
            g["steps"]
            or g["retained_steps"] != old["steps"]
            or any(
                g.get(k) != v
                for k, v in old.items()
                if k not in {"steps", "queries", "retained_negative_deliveries"}
            )
        ):
            raise ValueError("Frozen P08 source or question changed")
        sources = [s["request"] for s in old["steps"]]
        current_documents = recovery_documents(states[g["tenant"]], sources)
        positions = {d["event_id"]: d["global_position"] for d in current_documents}
        for source in sources:
            q = [
                q
                for q in r["requests"]
                if q["path"] == "/v1/events" and q["tenant"] == g["tenant"] and q["input"] == source
            ]
            if (
                len(q) != 1
                or q[0]["status"] != 201
                or q[0]["output"]["status"] != "created"
                or positions[source["event_id"]] != q[0]["output"]["global_position"]
            ):
                raise ValueError("Original accepted source receipt missing")
        if current_documents != recovery_documents(
            docs[g["tenant"] + "-final-state.json"]["snapshot"], sources
        ):
            raise ValueError("Retained accepted content/authority/position changed")
    ids = {s["request"]["event_id"] for g in original for s in g["steps"]}
    failed = [c for c in r["provider_calls"] if c.get("state") != "returned"]
    if len(failed) != 1 or failed[0].get("error_type") != "InternalServerError":
        raise ValueError("Unexpected original provider failure")
    scope = next(
        o for o in r["summary_cache_observations"] if o["id"] == failed[0].get("summary_request_id")
    )
    if set(scope["source_event_ids"]) & ids:
        raise ValueError("Required P08 input had failed summary invocation")
    return dict(
        original_run=proof["directory"],
        original_verdict="failed",
        accepted_inputs=9,
        unrelated_background_provider_failure=failed[0],
        pins=proof,
    )


def vector_chain(row, state, source_id, body, entity_name):
    nodes = {(r[0], r[1]): decode(r[2]) for r in state["nodes"]}
    refs = {
        r[4]
        for r in state["edges"]
        if r[0] == "Event" and r[1] == source_id and r[2] == "REFERENCES" and r[3] == "Entity"
    }
    eligible = {
        eid
        for eid in refs
        if entity_name.lower() in str(nodes.get(("Entity", eid), {}).get("name", "")).lower()
    }
    for near in row.get("nearest", []):
        for ann in row.get("ann", []):
            if not (
                len(near["embedding"]) == ann["dimensions"] == 384
                and ann["parameters"]["query"] == near["embedding"]
                and "FORCE_INDEX=" in ann["sql"]
            ):
                continue
            native_ids = {r[0] for r in ann["rows"]}
            hits = {h["id"] for h in near["hits"]}
            if not eligible & hits & native_ids:
                continue
            if (
                any(
                    s["embedding"] == near["embedding"]
                    and source_id in {eid for eid, score in s["events"]}
                    for s in row.get("seeds", [])
                )
                and source_id in body.get("nodes", {})
                and body["nodes"][source_id]["node_type"] == "Event"
            ):
                return True
    return False


async def execute(plan, *, request, check, record, save, settle):
    entries = record.setdefault("retrieval_proof", [])
    for g in plan["groups"]:
        for step in g["steps"]:
            code, out = await request(
                g["tenant"], "/v1/events", step["request"], role=step.get("role", "api")
            )
            check(g["name"] + ":" + step["scenario"] + " admitted", code == 201, code)
    states = await settle()
    if plan.get("retained_retrieval_proof"):
        record["retained_retrieval_source_proof"] = retained_sources(plan, states)
        check("retained P08 accepted sources and original worker proof", True)
        save()

    async def read(g, name, path, body):
        code, out = await request(g["tenant"], path, body)
        entry = dict(tenant=g["tenant"], name=name, request=body, status=code, response=out)
        entries.append(entry)
        save()
        check(name + " public200", code == 200, code)
        check(name + " endpoint/source closure", closed_response(out, states[g["tenant"]]))
        return out, entry

    g = plan["groups"][0]
    base = dict(
        query="Trace this artifact",
        intent="trace",
        seed_node_ids=[g["change"]],
        max_nodes=30,
        max_depth=5,
    )
    full, _ = await read(g, "exact-chain", "/v1/query/artifacts", base)
    required = {g[k] for k in ("change", "case", "run")}
    check(
        "exact source-backed failure chain",
        required <= set(full["nodes"])
        and g["control"] not in full["nodes"]
        and full["nodes"][g["run"]]["attributes"]["outcome"] == "failure",
    )
    edges = {(e["edge_type"], e["source"], e["target"]): e["properties"] for e in full["edges"]}
    check("exact declared EXECUTES link", ("EXECUTES", g["run"], g["case"]) in edges)
    ran = edges.get(("RAN_AGAINST", g["run"], g["change"]), {})
    check(
        "exact declared RAN_AGAINST commit link",
        ran.get("commit_sha") == "abc123" and ran.get("source_trust") == "trusted",
    )
    for name, updates in [
        ("one-node-budget", dict(max_nodes=1)),
        ("one-hop-budget", dict(max_depth=1)),
    ]:
        out, _ = await read(g, name, "/v1/query/artifacts", {**base, **updates})
        check(name + " bounded nodes", len(out["nodes"]) <= updates.get("max_nodes", 30))
        if "max_nodes" in updates:
            check(
                name + " actual cut disclosed",
                out["meta"]["truncated"] is True and g["change"] in out["nodes"],
            )
        else:
            check(
                name + " exact one-hop frontier",
                g["change"] in out["nodes"]
                and g["run"] in out["nodes"]
                and g["case"] not in out["nodes"],
            )
    for name, text in [
        ("ordinary-wording", g["title"]),
        ("independent-paraphrase", g["paraphrase"]),
    ]:
        out, entry = await read(
            g,
            name,
            "/v1/query/artifacts",
            dict(query=text, intent="trace", max_nodes=30, max_depth=5),
        )
        entry["discovery_verdict"] = (
            "supported" if g["change"] in out["nodes"] else "unsupported-for-frozen-question"
        )
        check(name + " unrelated authored control excluded", g["control"] not in out["nodes"])
        if name == "ordinary-wording":
            check(name + " target discovered", g["change"] in out["nodes"])
        save()
    acceptance = {r[0]: decode(r[2]) for r in states["b"]["events"]}
    for step in g.get("retained_steps") or g["steps"]:
        if step["scenario"].startswith("trust-"):
            expected_source = "demo.untrusted" if step.get("role") == "untrusted" else "demo.query"
            check(
                step["scenario"] + " authenticated acceptance source",
                acceptance[step["request"]["event_id"]]["source_id"] == expected_source,
            )
    trust_nodes = {r[1]: decode(r[2]) for r in states["b"]["nodes"]}
    check(
        "authenticated trust stored distinctly",
        trust_nodes[g["trusted"]]["source_trust"] == "trusted"
        and trust_nodes[g["untrusted"]]["source_trust"] == "untrusted",
    )
    trust_ids = {g["trusted"], g["untrusted"]}
    check(
        "trust controls have no corroborating business link",
        not any(
            r[2] != "DERIVED_FROM" and (r[1] in trust_ids or r[4] in trust_ids)
            for r in states["b"]["edges"]
        ),
    )
    for include in (False, True):
        out, _ = await read(
            g,
            "trust-opt-in-" + str(include),
            "/v1/query/artifacts",
            dict(query=g["trust_title"], intent="status", include_untrusted=include, max_nodes=30),
        )
        check("trusted discovered-" + str(include), g["trusted"] in out["nodes"])
        check(
            "untrusted matches declared seedless policy-" + str(include),
            (g["untrusted"] in out["nodes"]) == include,
        )
        if include:
            check(
                "untrusted returned label",
                out["nodes"][g["untrusted"]]["retrieval_reason"] == "untrusted"
                and out["nodes"][g["untrusted"]]["attributes"]["source_trust"] == "untrusted",
            )
    for g in plan["groups"][1:]:
        t = g["tenant"]
        # Extraction is a prerequisite, not an invented Entity inserted for the test.
        check(
            g["name"] + " named Entity references actually produced",
            any(
                r[0] == "Event" and r[1] == g["source_id"] and r[2] == "REFERENCES"
                for r in states[t]["edges"]
            ),
        )
        body = dict(
            query=g["vector_query"],
            intent="related",
            session_id=(g.get("retained_steps") or g["steps"])[0]["request"]["session_id"],
            agent_id=(g.get("retained_steps") or g["steps"])[0]["request"]["agent_id"],
            max_nodes=100,
            timeout_ms=30000,
        )
        out, _ = await read(g, g["name"], "/v1/query/subgraph", body)
        rows = [
            r
            for r in record.get("vector_observations", [])
            if r["tenant"] == t and r["query"]["query"] == g["vector_query"]
        ]
        check(
            g["name"] + " actual native ANN to Entity to Event participation",
            len(rows) == 1
            and rows[0]["state"] == "returned"
            and vector_chain(rows[0], states[t], g["source_id"], out, g["entity_name"]),
        )
        if g.get("entity_paraphrase_query"):
            text = g["entity_paraphrase_query"]
            check(
                g["name"] + " descriptive query excludes exact Entity token",
                g["entity_name"].lower() not in text.lower(),
            )
            diagnostic, entry = await read(
                g, g["name"] + "-descriptive", "/v1/query/subgraph", {**body, "query": text}
            )
            observed = [
                r
                for r in record.get("vector_observations", [])
                if r["tenant"] == t and r["query"]["query"] == text
            ]
            entry["target_source_returned"] = g["source_id"] in diagnostic["nodes"]
            entry["target_vector_participation"] = len(observed) == 1 and vector_chain(
                observed[0], states[t], g["source_id"], diagnostic, g["entity_name"]
            )
            entry["diagnostic_verdict"] = (
                "target-vector-participates"
                if entry["target_vector_participation"]
                else "C04-semantic-vector-gap"
            )
            save()
        absent, entry = await read(
            g,
            "absent-" + t,
            "/v1/query/artifacts",
            dict(query=g["absent_query"], seed_node_ids=[g["absent_seed"]], max_nodes=30),
        )
        check("absent identity not invented-" + t, g["absent_seed"] not in absent["nodes"])
        check(
            "absent claimed approval not invented-" + t,
            not any(
                "quasarnebula" in str(n["attributes"]).lower() for n in absent["nodes"].values()
            ),
        )
        entry["limit"] = (
            "No matching absent identity/claim; response may contain legitimate broad recall."
        )
        save()

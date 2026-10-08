"""All28 G07-E normalized catalog fixtures; no projector-derived expectations.

IDs, graph edges and lifecycle expectations originate in the checked-in literal
catalog. Scoping applies documented identity substitutions; event-keyed authored
lesson and statement-keyed decision hashes follow their declared public identity
contracts. This factory performs no API, database or model execution.
"""

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from context_graph.ontology import load_registry

CATALOG_PATH = Path(__file__).resolve().parents[1] / "tests/fixtures/pack_contracts/pdlc.json"


def fixtures(run_id, *, start=None):
    catalog = json.loads(CATALOG_PATH.read_text())
    registry = load_registry(["pdlc"])
    start = (start or datetime(2026, 10, 8, 10, tzinfo=UTC)).astimezone(UTC)
    stamp = start.isoformat()
    steps, ids = [], {}
    nested_baselines = {}
    # Small declared producer examples for the current PDLC reference branches.
    # Validate a fully populated parent before attempting any child rejection.
    references = {
        "work_items": {"tracker": "jira", "external_key": "PAY-7"},
        "entries": {"pr_number": 7, "section": "fixed"},
        "requirements": {"spec_id": "payments", "spec_version": "1", "local_id": "R1"},
        "designs": {"doc_id": "payments-hld", "section_path": "Retries", "version": "1"},
        "refines_designs": {"doc_id": "payments-hld", "section_path": "Retries", "version": "1"},
        "lesson_refs": {"content_hash": "a" * 64 + ":authored"},
        "change": {"repo": "example/payments", "number": 8},
        "incident": {"repo": "example/payments", "service": "payments", "incident_id": "inc-1"},
    }
    unpopulated = []
    for index, original in enumerate(catalog["cases"], 1):
        scenario = f"E{index:02d}-{original['event_type'].removeprefix('pdlc.')}"
        scope = f"g07-e/{run_id}/{index:02d}"
        eid = str(uuid5(NAMESPACE_URL, run_id + ":" + scenario))
        replacements = {
            "example/payments": scope + "/repo",
            "payments-hld": scope + "-hld",
            "payments": scope + "-service",
            "run-1": scope + "-run",
            "PAY-7": "G07-" + str(int(uuid5(NAMESPACE_URL, scope).hex[:10], 16)),
            "REQ-1": scope + "-request",
            "a1": scope + "-approval",
            "00000000-0000-0000-0000-000000000001": eid,
            "2026-10-07T00:00:00+00:00": stamp,
            "2026-10-07T00:00:00Z": stamp,
        }
        if original["event_type"] == "pdlc.incident.lesson_recorded":
            old = "7ac1b8d7010bb6cd3a3e84e7f90136b880bbc899e428ece49333372911ab9052"
            replacements[old] = sha256(eid.encode()).hexdigest()
        if original["event_type"] == "pdlc.decision.recorded":
            statement = scope + ": Use idempotency keys"
            replacements["Use idempotency keys"] = statement
            replacements["6778ff223842c4456865ed4e67200039c848ea423c4c715cc9b67c61468e27bd"] = (
                sha256(statement.encode()).hexdigest()
            )
        pattern = re.compile(
            "|".join(re.escape(k) for k in sorted(replacements, key=len, reverse=True))
        )

        def scoped(value, pattern=pattern, replacements=replacements):
            if isinstance(value, str):
                return pattern.sub(lambda m: replacements[m[0]], value)
            if isinstance(value, list):
                return [scoped(v) for v in value]
            if isinstance(value, dict):
                return {scoped(k): scoped(v) for k, v in value.items()}
            return value

        case = scoped(original)
        observed = case["expected_observed_node_ids"]
        ids[scenario] = (observed or [case["expected_domain_edges"][0][1]])[0]
        props = case.get("expected_node_properties", {})
        all_nodes = set(observed) | set(case["expected_states"]) | set(props)
        for _, source, target in case["expected_domain_edges"]:
            all_nodes.update((source, target))
        extra = {nid: dict(props.get(nid, {})) for nid in sorted(all_nodes)}
        for nid, state in case["expected_states"].items():
            extra[nid]["status"] = state
        primary = ids[scenario]
        request = dict(
            event_id=eid,
            event_type=case["event_type"],
            occurred_at=stamp,
            session_id=scope,
            agent_id="catalog.publisher",
            trace_id=run_id,
            payload_ref="synthetic:" + run_id + ":" + scenario,
            payload=case["payload"],
        )
        positive = dict(
            scenario=scenario,
            request=request,
            expected_status=201,
            expected_node=primary,
            expected_props=extra.pop(primary),
            extra_nodes=extra,
            expected_edges=case["expected_domain_edges"],
            expected_observed_node_ids=observed,
            expected_observation_events={
                nid: eid if nid in observed else None for nid in sorted(all_nodes)
            },
            source_kind=case["source_kind"],
            note=case["note"],
        )
        steps.append(positive)
        retry = deepcopy(positive)
        retry.update(
            scenario=scenario + "-retry", duplicate=True, assert_no_owned_table_changes=True
        )
        steps.append(retry)
        contract = registry.event_types[case["event_type"]].definition.payload_contract
        assert contract is not None
        # Alter one admitted scalar while retaining the Event ID, exercising a real conflict.
        conflict = deepcopy(positive)

        def scalar_path(properties, payload, prefix=()):
            for name, field in properties.items():
                if name not in payload:
                    continue
                path = (*prefix, name)
                if field.type == "string" and not field.enum and not field.pattern:
                    return path, payload[name] + "-conflict"
                if field.type == "integer":
                    return path, payload[name] + 1
                if field.type == "object":
                    found = scalar_path(field.properties, payload[name], path)
                    if found:
                        return found
            return None

        mutation = scalar_path(contract.properties, request["payload"])
        if mutation is None:
            raise ValueError("no bounded conflict mutation for " + case["event_type"])
        path, value = mutation
        target = conflict["request"]["payload"]
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        contract.validate_payload(conflict["request"]["payload"])
        conflict.update(
            scenario=scenario + "-conflict",
            expected_status=409,
            expected_node=None,
            expected_props={},
            extra_nodes={},
            expected_edges=[],
            expected_observed_node_ids=[],
            expected_observation_events={},
            assert_no_owned_table_changes=True,
        )
        steps.append(conflict)
        for name, field in contract.properties.items():
            if not field.required:
                continue
            variants = [("missing", ...), ("null", None), ("wrong-type", [])]
            if field.type == "string":
                variants.append(("empty", ""))
            for variant, invalid in variants:
                negative = deepcopy(conflict)
                negative["request"] = deepcopy(request)
                negative["scenario"] = scenario + "-invalid-" + name + "-" + variant
                negative["request"]["event_id"] = str(
                    uuid5(NAMESPACE_URL, run_id + ":" + negative["scenario"])
                )
                if invalid is ...:
                    del negative["request"]["payload"][name]
                else:
                    negative["request"]["payload"][name] = invalid
                negative["expected_status"] = 422
                steps.append(negative)
        for branch, container in contract.properties.items():
            is_list = container.type == "array" and container.items.type == "object"
            if container.type != "object" and not is_list:
                continue
            child = container.items if is_list else container
            if branch not in references:
                unpopulated.append(case["event_type"] + ":" + branch)
                continue
            baseline = deepcopy(request["payload"])
            baseline[branch] = (
                [scoped(references[branch])] if is_list else scoped(references[branch])
            )
            contract.validate_payload(baseline)
            baseline_id = scenario + ":" + branch
            nested_baselines[baseline_id] = baseline
            for name, field in child.properties.items():
                if not field.required:
                    continue
                variants = [("missing", ...), ("null", None), ("wrong-type", [])]
                if field.type == "string" and (field.min_length or field.enum):
                    variants.append(("empty", ""))
                if field.enum:
                    variants.append(("invalid-enum", "not-a-declared-enum-value"))
                location = [branch, 0, name] if is_list else [branch, name]
                for variant, invalid in variants:
                    negative = deepcopy(conflict)
                    negative["request"] = deepcopy(request)
                    negative["request"]["payload"] = deepcopy(baseline)
                    negative["scenario"] = (
                        scenario + "-nested-" + branch + "-" + name + "-" + variant
                    )
                    negative["request"]["event_id"] = str(
                        uuid5(NAMESPACE_URL, run_id + ":" + negative["scenario"])
                    )
                    parent = negative["request"]["payload"][branch]
                    if is_list:
                        parent = parent[0]
                    if invalid is ...:
                        del parent[name]
                    else:
                        parent[name] = invalid
                    negative.update(
                        expected_status=422,
                        validation_baseline=baseline_id,
                        expected_validation_location=location,
                        validation_variant=variant,
                    )
                    try:
                        contract.validate_payload(negative["request"]["payload"])
                    except ValidationError as exc:
                        if {error["loc"] for error in exc.errors()} != {tuple(location)}:
                            raise ValueError(
                                "nested probe rejected at unintended location: "
                                + negative["scenario"]
                            ) from exc
                    else:
                        raise ValueError("nested probe unexpectedly valid: " + negative["scenario"])
                    steps.append(negative)
    return dict(
        ids=ids,
        steps=steps,
        queries=[],
        fallback_seed=next(iter(ids.values())),
        source_kind=catalog["fixture_kind"],
        pack_version=catalog["pack_version"],
        nested_validation_baselines=nested_baselines,
        unpopulated_nested_branches=unpopulated,
        limitations=[
            (
                "Expected properties are declared literally for four newly mapped cases; "
                "all28 declare exact observed IDs, domain edges and lifecycle transitions."
            ),
            (
                "Required nested probes use validated populated producer examples and exact "
                "ValidationError locations; any unavailable branches are listed explicitly."
            ),
        ],
    )

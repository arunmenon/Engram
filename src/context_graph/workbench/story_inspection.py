"""Deterministic story coverage and read-only failure context, never oracle repair."""

import json
from typing import Any

from context_graph.workbench.draft_stories import snapshot_registry
from context_graph.workbench.engine import digest, engine_revision
from context_graph.workbench.journey_runner import frozen_registry

QUESTION_KINDS = {"retrieval", "evaluation", "retrieval_benchmark"}


def story_registry(record: dict[str, Any]) -> Any:
    story = record["journey"]
    snapshot = record.get("journey_pack_snapshot")
    return (
        snapshot_registry(snapshot, story["pack_digest"])
        if snapshot
        else frozen_registry(story["pack_digest"])
    )


def result_stale(record: dict[str, Any]) -> bool:
    result, story = record.get("journey_result"), record.get("journey")
    if not result or not story:
        return False
    return (
        result.get("journey_digest") != digest(story)
        or result.get("pack_digest") != story["pack_digest"]
        or result.get("engine_revision") != engine_revision()
        or bool(
            record.get("journey_pack_snapshot")
            and digest(record["journey_pack_snapshot"]) != story["pack_digest"]
        )
    )


def story_specification(record: dict[str, Any]) -> str | None:
    """Only the accepted story's origin is evidence; a pending brief is a proposal."""
    origin = record.get("journey_origin") or {}
    return (origin.get("brief") or {}).get("specification") if origin.get("reviewer") else None


def check_differences(check: dict[str, Any], result: dict[str, Any]) -> list[str]:
    """Plain recorded comparisons, without inferring why the outcome differs."""
    if result.get("status") != "failed":
        return []
    expected, actual = check["expected"], result.get("actual") or {}

    def value(item: Any) -> str:
        if item is None:
            return "not recorded"
        if isinstance(item, str):
            return item
        return json.dumps(item, ensure_ascii=False)

    def records(items: list[str]) -> str:
        return (
            "; ".join(item.replace(":", " · ", 1).replace("|", " / ") for item in items) or "none"
        )

    if check["kind"] == "properties":
        props = actual.get("properties") or {}
        return [
            f"Expected {key}: {value(wanted)}. Recorded: {value(props.get(key))}."
            for key, wanted in expected.get("properties", {}).items()
            if key not in props or props[key] != wanted
        ]
    if check["kind"] == "evaluation":
        return [
            f"Expected answers: {records(q.get('expected', []))}. "
            f"Found: {records(q.get('found', []))}."
            for q in actual.get("questions", [])
            if set(q.get("expected", [])) != set(q.get("found", []))
        ]
    if check["kind"] == "retrieval":
        lines = []
        for key, label in (
            ("missing", "Expected but missing"),
            ("forbidden", "Found but forbidden"),
            ("unexpected_nodes", "Unexpected answers"),
        ):
            if actual.get(key):
                lines.append(f"{label}: {records(actual[key])}.")
        return lines
    return []


def check_guidance(
    check: dict[str, Any], observed: dict[str, Any], has_source: bool
) -> dict[str, Any]:
    kind, status = check["kind"], observed.get("status")
    category, action = "uncertain", "Compare the event, current rules and reviewed expectation."
    if status in {"unsupported", "not_run"} or kind == "supplemental":
        category = "unsupported"
        action = (
            "This check has no executable result here. Use a supported check or retain it "
            "as an explicit gap; question answers currently use sets of records, not scalar totals."
        )
    elif status == "error":
        category = "execution"
        action = "Inspect the processing error and retry only after its cause is addressed."
    elif kind == "disposition":
        category = "event handling"
        action = (
            "Compare the supplied event with its payload contract and duplicate/conflict "
            "rules. A rejection may be intentional; verify the reviewed expected handling."
        )
    elif kind in QUESTION_KINDS:
        category = "answer scope"
        action = (
            "Check the question's account, starting records and answer type against the "
            "business rules. Compare missing and unexpected answers. This mismatch alone "
            "does not establish whether the pack or the expected answer is wrong."
        )
    elif kind in {"node_present", "edge_present", "properties", "graph_exact"}:
        category = "graph or mapping"
        action = (
            "Inspect the input event, matching projection rules and stored records at this "
            "checkpoint. A missing record or field may come from the sample, a rule, or "
            "the expectation; do not assume a pack defect without that comparison."
        )
    if not has_source:
        action += (
            " No reviewed domain specification is attached to this story; supply it "
            "before deciding which business outcome is correct."
        )
    return {
        "category": category,
        "action": action,
        "rerun": (
            "After a reviewed correction, rerun the whole story, including this check "
            "and its dependent questions. Keep the prior result as historical evidence."
        ),
        "boundary": "Never change a reviewed expectation merely to make a check pass.",
    }


def proof_warnings(
    check: dict[str, Any], result: dict[str, Any] | None, record: dict[str, Any]
) -> list[str]:
    expected, kind = check["expected"], check["kind"]
    if kind == "properties" and not expected.get("properties"):
        return ["No fields are asserted. This cannot count as proof of a property update."]
    if not result or result.get("status") != "passed":
        return []
    run = record.get("journey_result") or {}
    index = check.get("after_step")
    steps = run.get("steps") or []
    graph = (
        steps[index]
        if index is not None and index < len(steps)
        else steps[-1]
        if steps
        else run.get("initial_graph") or {}
    )
    ids = {node["id"] for node in graph.get("nodes", [])}
    # Absence alone is not proof that a rule was exercised. Use observed history
    # conservatively: never describe an unseen candidate as statically impossible.
    history = [
        run.get("initial_graph") or {},
        *steps[: index + 1 if index is not None else len(steps)],
    ]
    seen = {node["id"] for snapshot in history for node in snapshot.get("nodes", [])}
    if kind == "node_absent" and expected["node"] not in seen:
        return [
            "This record never appears in the observed story. Its absence alone "
            "does not show that a creation or removal rule was exercised; add a "
            "relevant comparison example."
        ]
    if kind == "evaluation" and expected.get("min_f1") == 0:
        return [
            "The required answer score is zero, so any answer can pass. Review the "
            "threshold before counting this as answer proof."
        ]
    if (
        kind == "retrieval"
        and expected.get("forbidden")
        and not any(
            expected.get(key)
            for key in ("required", "exact_nodes", "properties", "edges", "forbidden_edges")
        )
        and not set(expected["forbidden"]) & ids
    ):
        return [
            "This question only forbids records absent from the graph. It does not "
            "demonstrate that the question excludes an available answer; add a "
            "relevant comparison example."
        ]
    if kind in {"properties", "property_absent"}:
        try:
            node_type = story_registry(record).node_types.get(expected["node"].split(":", 1)[0])
        except ValueError:
            node_type = None  # The separate pack warning already blocks trusted coverage.
        if node_type:
            identity = {"node_type", "node_id", node_type.key_property, *node_type.key}
            if kind == "properties" and set(expected.get("properties", {})) <= identity:
                return [
                    "Only the record type or identity fields are checked. This proves "
                    "identity, not a business-field update."
                ]
            if (
                kind == "property_absent"
                and expected["property"] not in set(node_type.properties) | identity
            ):
                return [
                    "This field is not declared for the record type. Its absence does not "
                    "prove a field-removal rule was exercised."
                ]
    if kind == "edge_absent" and not {expected["source"], expected["target"]} <= ids:
        return [
            (
                "A relationship endpoint is absent. The missing link alone does not prove "
                "the relationship rule was exercised; review the prerequisite records."
            )
        ]
    if kind == "evidence_absent" and expected["node"] not in ids:
        return ["The record itself is absent. This does not prove its evidence-link behavior."]
    if kind == "retrieval" and not any(
        expected.get(key)
        for key in (
            "required",
            "forbidden",
            "exact_nodes",
            "properties",
            "edges",
            "forbidden_edges",
        )
    ):
        return [
            (
                "This question asserts no answer or relationship outcome. Review the "
                "intended assertion before counting it as answer proof."
            )
        ]
    return []


def inspect_story(record: dict[str, Any]) -> dict[str, Any]:
    story = record["journey"]
    run = record.get("journey_result") or {}
    stale = result_stale(record)
    results = {r["check_id"]: r for r in run.get("checks", [])}
    checks = story["checks"]
    details = []
    has_source = bool(story_specification(record))
    for check in checks:
        result = results.get(check["id"])
        warnings = proof_warnings(check, result, record)
        status = "defined"
        if result:
            status = (
                "stale"
                if stale
                else "defined"
                if result["status"] in {"unsupported", "not_run"}
                else "executed"
            )
            if (
                not stale
                and result["status"] == "passed"
                and not warnings
                and story["expectations_reviewed"]
            ):
                status = "passing"
        if warnings and not stale:
            status = "needs_review"
        details.append(
            {
                "id": check["id"],
                "label": check["description"],
                "kind": check["kind"],
                "status": status,
                "outcome": result.get("status") if result else None,
                "warnings": warnings,
                "differences": check_differences(check, result or {}),
                "guidance": check_guidance(check, result or {}, has_source),
            }
        )
    by_id = {item["id"]: item for item in details}

    def row(
        kind: str, label: str, selected: list[dict[str, Any]], occurrences: int = 0
    ) -> dict[str, Any]:
        statuses = [by_id[c["id"]]["status"] for c in selected]
        state = (
            "no_check"
            if not selected
            else "stale"
            if "stale" in statuses
            else "needs_review"
            if "needs_review" in statuses
            else "passing"
            if all(s == "passing" for s in statuses)
            else "executed"
            if "executed" in statuses
            else "defined"
        )
        return {
            "kind": kind,
            "label": label,
            "status": state,
            "occurrences": occurrences,
            "checks": [c["id"] for c in selected],
        }

    rows = []
    try:
        registry = story_registry(record)
        event_names = sorted(
            {
                name
                for p in registry.packs
                if p.name not in {"core", "memory", "user"}
                for name in p.events
            }
            | {e["request"]["event_type"] for e in story["events"]}
        )
        for name in event_names:
            steps = {
                i
                for i, event in enumerate(story["events"])
                if event["request"]["event_type"] == name
            }
            selected = [
                c for c in checks if c.get("after_step") in steps and c["kind"] == "disposition"
            ]
            rows.append(row("event handling", name, selected, len(steps)))
            rejection = [c for c in selected if c["expected"].get("http_status") in {409, 422}]
            rows.append(row("rejection scenario", name, rejection))
        for pack in registry.packs:
            for rule in pack.projection:
                if not rule.transition:
                    continue
                transition = rule.transition
                steps = {
                    i
                    for i, event in enumerate(story["events"])
                    if event["request"]["event_type"] == rule.event
                }
                state_field = "status"  # Lifecycled engine state property.
                selected = [
                    c
                    for c in checks
                    if c.get("after_step") in steps
                    and c["kind"] == "properties"
                    and c["expected"].get("node", "").startswith(transition.type + ":")
                    and c["expected"].get("properties", {}).get(state_field) == transition.to
                ]
                rows.append(
                    row(
                        "transition state assertion",
                        f"{transition.type}: {rule.event} → {transition.to}",
                        selected,
                        len(steps),
                    )
                )
        for pack in registry.packs:
            if pack.name in {"core", "memory", "user"}:
                continue
            for intent in pack.retrieval.intents:
                selected = [
                    c
                    for c in checks
                    if c["kind"] in QUESTION_KINDS
                    and (
                        c["expected"].get("intent") == intent
                        or c["expected"].get("question", {}).get("intent") == intent
                    )
                ]
                rows.append(row("question intent", intent, selected))
        issue = None
    except ValueError as exc:
        issue = str(exc)[:500]
    rows.extend(
        row("question", c["description"], [c])
        for c in checks
        if c["kind"] in QUESTION_KINDS or c["kind"] == "supplemental"
    )
    return {
        "rows": rows,
        "checks": details,
        "stale": stale,
        "pack_issue": issue,
        "boundary": (
            "Domain event handling, state assertions and questions are separate. Built-in "
            "root capabilities are outside this inventory. Passing these "
            "checks is not exhaustive behavior or guard coverage. Checks without an "
            "explicit event checkpoint are listed separately."
        ),
    }


def failure_context(record: dict[str, Any], index: int, question: str) -> dict[str, Any]:
    inspection = inspect_story(record)
    if inspection["stale"] or inspection["pack_issue"]:
        raise ValueError("Rerun the current pinned story before explaining an old result")
    checks = record["journey"]["checks"]
    if index >= len(checks):
        raise ValueError("This check is no longer available")
    check = checks[index]
    result = next(
        (
            r
            for r in (record.get("journey_result") or {}).get("checks", [])
            if r["check_id"] == check["id"]
        ),
        None,
    )
    if not result or result["status"] not in {"failed", "error", "unsupported", "not_run"}:
        raise ValueError("Select a failed, unavailable or unfinished check")
    step = check.get("after_step")
    event = record["journey"]["events"][step] if step is not None else None
    rules: list[dict[str, Any]] = []
    if event:
        for pack in story_registry(record).packs:
            rules.extend(
                rule.model_dump(mode="json", by_alias=True)
                for rule in pack.projection
                if rule.event == event["request"]["event_type"]
            )
    if not event:
        intent_name = check["expected"].get("intent") or check["expected"].get("question", {}).get(
            "intent"
        )
        intent = story_registry(record).intents.get(intent_name) if intent_name else None
        if intent:
            rules.append(
                {
                    "pack": intent.pack,
                    "intent": intent_name,
                    "settings": intent.definition.model_dump(mode="json"),
                    "weights": intent.weights,
                }
            )
        event = {
            "scope": "Final graph check; no single event is attributed as the cause",
            "question": check["expected"].get("question") or check["expected"].get("text"),
            "explicit_intent": intent_name,
        }
    values = [
        ("subject", "failed_check", check),
        ("observed", "observed", result),
        ("guidance", "guidance", inspection["checks"][index]["guidance"]),
        ("event", "event", event),
        ("rules", "pack", rules),
        ("specification", "source", story_specification(record)),
    ]
    evidence = []
    for name, kind, value in values:
        text = json.dumps(value)
        if len(text) > 12000:
            raise ValueError("This check's evidence is too large; inspect its recorded details")
        evidence.append({"id": name, "kind": kind, "text": text})
    return {
        "scope": "failed_check",
        "question": question,
        "evidence": evidence,
        "instructions": (
            "Explain the supplied failure and uncertainty. Do not change expectations, "
            "draft a repair instruction or invent missing evidence. Identify what needs "
            "inspection and rerunning. A fixture or agent explanation is not a verified "
            "root cause."
        ),
    }

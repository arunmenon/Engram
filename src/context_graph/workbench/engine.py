"""Adapters to the real ontology parser, composition, admission and projection planner."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any
from uuid import NAMESPACE_URL, uuid5

import yaml

from context_graph.domain.models import Event
from context_graph.domain.ontology import Pack
from context_graph.domain.pack_admission import compile_admission_policy
from context_graph.domain.pack_bundle import ActiveBundle, resolve_bundle
from context_graph.domain.pack_intents import RegistryIntents
from context_graph.domain.pack_projection import PackProjector
from context_graph.domain.pack_versioning import classify_change
from context_graph.ontology.loader import load_registry
from context_graph.workbench.authoring import samples
from context_graph.workbench.catalog import CATALOG_DIR

if TYPE_CHECKING:
    from collections.abc import Iterator

    from context_graph.workbench.models import Content


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@contextmanager
def composed(
    content: Content, raw_pack: dict[str, Any]
) -> Iterator[tuple[Pack, ActiveBundle, Path]]:
    pack = Pack.model_validate(raw_pack)
    # Never create a path from unvalidated model output or allow shadowing roots.
    if pack.name in {"core", "memory", "user", *content.existing_packs}:
        raise ValueError("Authored pack must not shadow a selected or built-in pack")
    with TemporaryDirectory(prefix="engram-draft-") as directory:
        path = Path(directory)
        (path / f"{pack.name}.pack.yaml").write_text(yaml.safe_dump(raw_pack, sort_keys=False))
        registry = load_registry(
            [*content.existing_packs, pack.name],
            [path, CATALOG_DIR],
            builtin_packs=list(content.roots),
        )
        yield pack, resolve_bundle(registry), path


def event_from_sample(sample: dict[str, Any], index: int) -> Event:
    return Event.model_validate_json(
        json.dumps(
            {
                "event_id": str(
                    uuid5(NAMESPACE_URL, str(sample.get("event_id", f"sample-{index}")))
                ),
                "event_type": sample["event_type"],
                "occurred_at": sample.get(
                    "occurred_at",
                    (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)).isoformat(),
                ),
                "session_id": "workbench-scenario",
                "agent_id": sample.get("producer_id", "workbench.sample"),
                # Explicit event identities must retain a stable envelope on retry.
                "trace_id": sample.get("trace_id", str(sample.get("event_id", f"sample-{index}"))),
                "payload_ref": json.dumps(sample["payload"]),
            }
        )
    )


def validate(content: Content, raw_pack: dict[str, Any]) -> dict[str, Any]:
    with composed(content, raw_pack) as (pack, bundle, _path):
        registry = bundle.registry
        policy = compile_admission_policy(bundle)
        projector = PackProjector(registry, frozenset(content.trusted_ids))
        sample_results = []
        problems = []
        available_intents = RegistryIntents.for_artifacts(registry).names
        for question in content.questions:
            if question.intent and question.intent not in available_intents:
                problems.append(
                    f"Question {question.id}: intent {question.intent} is not executable"
                )
        for selected_pack in registry.packs:
            if selected_pack.extraction.sources and selected_pack.extraction.propose:
                problems.append(f"{selected_pack.name}: extraction worker sandbox is not supported")
        for name, event_def in pack.events.items():
            if event_def.payload_contract is None:
                problems.append(f"{name}: payload contract required for tenant-bound admission")
        for index, sample in enumerate(samples(content)):
            decision = policy.decide(sample["event_type"], sample["payload"])
            event = event_from_sample(sample, index)
            result = {
                "index": index,
                "event_type": sample["event_type"],
                "input": sample["payload"],
                "source_id": sample["_source_id"],
                "source_record": sample["_index"] + 1,
                "rules": [
                    rule.model_dump(mode="json", by_alias=True, exclude_none=True)
                    for _owner, rule in registry.rules_for(sample["event_type"])
                ],
                "admission": asdict(decision),
                "planned": None,
            }
            if decision.allowed and decision.handling == "processed":
                result["planned"] = asdict(projector.plan(event, {"payload": sample["payload"]}))
            if result["planned"]:
                operations = sum(
                    len(result["planned"][part]) for part in ("nodes", "states", "edges", "lookups")
                )
                if operations > 200:
                    problems.append(f"Sample {index + 1}: exceeds 200 planned sandbox operations")
            expected = sample.get("expect_admitted", True)
            if decision.allowed != expected:
                problems.append(
                    f"Sample {index + 1}: admission differs from expect_admitted={expected}"
                )
            sample_results.append(result)
        return {
            "passed": not problems,
            "problems": problems,
            "bundle_digest": bundle.identity,
            "change": classify_change(None, registry).as_dict(),
            "pack_name": pack.name,
            "pack_version": pack.version,
            "packs": [{"name": p.name, "version": p.version} for p in registry.packs],
            "inert": registry.inert_settings(),
            "samples": sample_results,
            "schema": {
                "nodes": raw_pack.get("types", {}).get("nodes", {}),
                "edges": raw_pack.get("types", {}).get("edges", {}),
            },
        }


def engine_revision() -> str:
    """Fingerprint the source tree at server startup, including local engine changes."""
    root = Path(__file__).resolve().parents[1]
    hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".yaml"}
    }
    return "sha256:" + digest(hashes)

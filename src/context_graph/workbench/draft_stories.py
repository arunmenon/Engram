"""Freeze an authored pack bundle for a separate, reviewable story workspace."""

from typing import Any

from context_graph.domain.ontology import OntologyRegistry, Pack
from context_graph.workbench.authoring import samples
from context_graph.workbench.engine import composed, digest, event_from_sample
from context_graph.workbench.journeys import Journey
from context_graph.workbench.models import Content


def snapshot_registry(snapshot: dict[str, Any], expected_digest: str) -> OntologyRegistry:
    if digest(snapshot) != expected_digest:
        raise ValueError("Story pack snapshot differs from its pinned digest")
    registry = OntologyRegistry([Pack.model_validate(p) for p in snapshot["packs"]])
    if snapshot["primary_pack"] not in {p.name for p in registry.packs}:
        raise ValueError("Story's domain pack is absent from its snapshot")
    return registry


def draft_story(content: Content, raw_pack: dict[str, Any]) -> tuple[Journey, dict[str, Any]]:
    with composed(content, raw_pack) as (pack, bundle, _):
        snapshot = {
            "primary_pack": pack.name,
            "packs": [
                p.model_dump(mode="json", by_alias=True, exclude_none=True)
                for p in bundle.registry.packs
            ],
        }
    events, checks = [], []
    for i, sample in enumerate(samples(content)):
        request = event_from_sample(sample, i).model_dump(mode="json", exclude_none=True)
        request["payload"] = sample["payload"]
        events.append({"id": f"sample-{i}", "title": sample["event_type"], "request": request})
        checks.append(
            {
                "id": f"admission-{i}",
                "description": "Expected sample admission",
                "source": "operator-samples",
                "kind": "disposition",
                "after_step": i,
                "expected": {"http_status": 201 if sample.get("expect_admitted", True) else 422},
            }
        )
    if not events:
        raise ValueError("Add sample events before creating a story workspace")
    return Journey.model_validate(
        {
            "id": "authored-pack-story",
            "title": f"{content.name[:140]} · story draft",
            "story": "Plan a story for this pinned pack, then review generated events and answers.",
            "source_refs": ["operator-samples", "selected-pack", "operator-specification"],
            "pack_digest": digest(snapshot),
            "events": events,
            "checks": checks,
            "trusted_producers": content.trusted_ids,
            "expectations_reviewed": False,
        }
    ), snapshot

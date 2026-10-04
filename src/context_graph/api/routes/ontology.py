"""The active ontology (ADR-0018 phase 3).

``GET /v1/ontology`` describes the composed packs the service runs with:
versions, node, edge and event types, retrieval intents and the
extraction profiles (with the output schema the model is held to). It
also reports the version the configured graph records and how the change
between the two would be applied (``none``, ``additive``, ``mapping`` or
``breaking``), so an operator can see whether a rebuild is due.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse

from context_graph.domain.ontology import EnumSpec
from context_graph.domain.pack_extraction import extraction_profiles
from context_graph.ontology.versioning import plan_for_state, read_state

if TYPE_CHECKING:
    from context_graph.domain.ontology import OntologyRegistry, PropertySpec
    from context_graph.ports.pack_graph import PackGraph
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

router = APIRouter(tags=["ontology"])


def _spec(spec: PropertySpec) -> Any:
    return {"enum": list(spec.enum)} if isinstance(spec, EnumSpec) else spec


def describe(registry: OntologyRegistry, settings: Settings) -> dict[str, Any]:
    """The registry as JSON: summary, types, events, intents and extraction profiles."""
    ontology = settings.ontology
    profiles = extraction_profiles(
        registry,
        max_nodes=ontology.extraction_max_nodes,
        max_links=ontology.extraction_max_links,
        max_text_chars=ontology.extraction_max_text_chars,
        max_value_chars=ontology.extraction_max_value_chars,
    )
    return {
        **registry.summary(),
        "node_types": {
            name: {
                "pack": t.pack,
                "key": t.key,
                "key_property": t.key_property,
                "interfaces": t.interfaces,
                "properties": {p: _spec(s) for p, s in sorted(t.properties.items())},
                "lifecycle": None
                if t.lifecycle is None
                else {"initial": t.lifecycle.initial, "states": t.lifecycle.states},
            }
            for name, t in sorted(registry.node_types.items())
        },
        "edge_types": {
            name: {
                "pack": e.pack,
                "from": sorted(e.from_types),
                "to": sorted(e.to_types),
                "from_packs": sorted(e.from_packs),
                "to_packs": sorted(e.to_packs),
                "properties": {p: _spec(s) for p, s in sorted(e.properties.items())},
            }
            for name, e in sorted(registry.edge_types.items())
        },
        "event_types": {name: {"pack": e.pack} for name, e in sorted(registry.event_types.items())},
        "intent_definitions": {
            name: {
                "pack": i.pack,
                "keywords": i.definition.keywords,
                "weights": dict(sorted(i.weights.items())),
                "seed_strategy": i.definition.seed_strategy,
                "plugin": i.definition.plugin,
                "direction": i.definition.direction,
            }
            for name, i in sorted(registry.intents.items())
        },
        "extraction": [
            {
                "pack": profile.pack_name,
                "sources": sorted(profile.sources),
                "propose_nodes": sorted(profile.nodes),
                "propose_links": sorted(profile.edges),
                "never_propose": sorted(profile.never_propose),
                "output_schema": profile.output_schema(),
            }
            for profile in profiles
        ],
    }


@router.get("/ontology")
async def get_ontology(request: Request) -> ORJSONResponse:
    registry: OntologyRegistry = request.app.state.ontology
    settings: Settings = request.app.state.settings
    graph: PackGraph = request.app.state.graph_store
    body = describe(registry, settings)
    try:
        state = await read_state(graph)
        plan = plan_for_state(state, registry)
    except Exception:
        log.exception("ontology_graph_state_unavailable")
        body["graph"] = {"error": "the graph's ontology state could not be read"}
        return ORJSONResponse(content=body)
    body["graph"] = (
        None
        if state is None
        else {
            "version": state.version,
            "recorded_at": state.recorded_at,
            "applied": state.properties.get("applied"),
            "packs": state.properties.get("packs"),
            "eval_pending": state.properties.get("eval_pending", []),
            "gate_passed": state.properties.get("gate_passed"),
        }
    )
    body["change"] = plan.as_dict()
    return ORJSONResponse(content=body)

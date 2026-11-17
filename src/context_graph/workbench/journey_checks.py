"""Executable expected-value formats shared by story generation and validation."""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

from context_graph.ontology.evaluation import EvalQuestion
from context_graph.workbench.journeys import QueryOptions, RetrievalLimits

FIELDS: dict[str, dict[str, Any]] = {
    "edge_targets": {
        "type": str,
        "node": str,
        "direction": Literal["in", "out"],
        "targets": list[str],
    },
    "nodes_matching": {"type": str, "properties": dict[str, Any], "ids": list[str]},
    "properties": {"node": str, "properties": dict[str, Any]},
    "node_present": {"node": str},
    "node_absent": {"node": str},
    "property_absent": {"node": str, "property": str},
    "evidence_absent": {"node": str},
    "edge_present": {"type": str, "source": str, "target": str},
    "edge_absent": {"type": str, "source": str, "target": str},
    "graph_exact": {
        "nodes": dict[str, dict[str, Any]],
        "edges": list[tuple[str, str, str]],
        "evidence": dict[str, list[str]],
    },
    "disposition": {"http_status": Literal[201, 409, 422]},
    "retrieval": {
        "seed": str | None,
        "intent": str | None,
        "required": list[str],
        "forbidden": list[str],
    },
    "evaluation": {"question": EvalQuestion, "min_f1": Annotated[float, Field(ge=0, le=1)]},
    "unchanged": {},
    "supplemental": {"reason": str},
}
OPTIONAL: dict[str, dict[str, tuple[Any, Any]]] = {
    "edge_present": {"properties": (dict[str, Any], Field(default_factory=dict))},
    "evaluation": {"declared_gate": (float, 0.8)},
    "retrieval": {
        "text": (str, ""),
        "not_truncated": (bool, False),
        "query_options": (QueryOptions, Field(default_factory=QueryOptions)),
        "scenario": (str, ""),
        "properties": (dict[str, dict[str, Any]], Field(default_factory=dict)),
        "evidence": (dict[str, list[str]], Field(default_factory=dict)),
        "edges": (list[tuple[str, str, str]], Field(default_factory=list)),
        "forbidden_edges": (list[tuple[str, str, str]], Field(default_factory=list)),
        "seeds": (list[str], Field(default_factory=list)),
        "required_seeds": (list[str], Field(default_factory=list)),
        "exact_nodes": (list[str], Field(default_factory=list)),
        "first_seed": (str, ""),
        "truncated": (bool | None, False),
        "max_node_count": (int, 0),
        "node_count": (int, 0),
        "max_observed_graph_calls": (int, 0),
        "metadata": (dict[str, Any], Field(default_factory=dict)),
        "metadata_fields": (dict[str, dict[str, Any]], Field(default_factory=dict)),
        "reasons": (dict[str, str], Field(default_factory=dict)),
        "forbidden_reasons": (list[str], Field(default_factory=list)),
        "types": (dict[str, list[str]], Field(default_factory=dict)),
        "nodes_by_type": (dict[str, list[str]], Field(default_factory=dict)),
        "first_of_type": (dict[str, dict[str, dict[str, Any]]], Field(default_factory=dict)),
        "work_budget": (dict[str, int], Field(default_factory=dict)),
        "compare_retrieval_limits": (RetrievalLimits, Field(default_factory=RetrievalLimits)),
    },
}


def _expected_model(kind: str, fields: dict[str, Any]) -> type[BaseModel]:
    definitions: dict[str, Any] = {name: (annotation, ...) for name, annotation in fields.items()}
    definitions.update(OPTIONAL.get(kind, {}))
    return create_model(
        f"{kind.title().replace('_', '')}Expected",
        __config__=ConfigDict(extra="forbid", strict=True),
        **definitions,
    )


EXPECTED_MODELS = {kind: _expected_model(kind, fields) for kind, fields in FIELDS.items()}
EXPECTED_FIELDS = {kind: set(fields) for kind, fields in FIELDS.items()}

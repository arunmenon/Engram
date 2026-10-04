"""``python -m context_graph.ontology``: target overrides (ADR-0018 phase 3 review)."""

from __future__ import annotations

import pytest

from context_graph.ontology.__main__ import known_settings_keys, same_graph, target_settings
from context_graph.settings import Settings


def test_known_keys_cover_nested_and_top_level_settings() -> None:
    keys = known_settings_keys()
    assert {"CG_NEO4J_URI", "CG_SPANNER_DATABASE", "CG_STORAGE_GRAPH", "CG_LOG_LEVEL"} <= keys


def test_a_misspelled_override_is_refused() -> None:
    with pytest.raises(SystemExit, match="CG_NEO4J_URL is not a setting"):
        target_settings(["CG_NEO4J_URL=bolt://green:7687"])
    with pytest.raises(SystemExit, match="CG_KEY=VALUE"):
        target_settings(["NEO4J_URI=bolt://green:7687"])


def test_same_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CG_STORAGE_GRAPH", "neo4j")
    live = Settings()
    assert same_graph(live, target_settings(["CG_LOG_LEVEL=DEBUG"]))
    assert not same_graph(live, target_settings(["CG_NEO4J_URI=bolt://green:7687"]))
    monkeypatch.setenv("CG_STORAGE_GRAPH", "spanner")
    live = Settings()
    assert not same_graph(live, target_settings(["CG_SPANNER_DATABASE=green"]))

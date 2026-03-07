"""JSON persistence for the knowledge graph.

Serializes/deserializes the in-memory graph to a JSON file on disk
using orjson for fast I/O. The graph file is stored in the project
root and should be added to .gitignore.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from kg_memory.graph import KnowledgeGraph


def save_graph(graph: KnowledgeGraph, path: Path) -> None:
    """Serialize the knowledge graph to a JSON file.

    Uses orjson for fast serialization. Creates parent directories
    if they don't exist. Writes atomically via temp file + rename.
    """
    data = graph.to_dict()
    json_bytes = orjson.dumps(data, option=orjson.OPT_INDENT_2)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_bytes(json_bytes)
    tmp_path.rename(path)


def load_graph(path: Path) -> KnowledgeGraph | None:
    """Deserialize a knowledge graph from a JSON file.

    Returns None if the file doesn't exist or is corrupted.
    """
    from kg_memory.graph import KnowledgeGraph

    if not path.exists():
        return None
    try:
        json_bytes = path.read_bytes()
        data = orjson.loads(json_bytes)
        return KnowledgeGraph.from_dict(data)
    except (orjson.JSONDecodeError, KeyError, TypeError):
        return None

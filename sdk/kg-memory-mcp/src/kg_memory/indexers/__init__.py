"""Indexing pipeline orchestrator for the knowledge graph.

Coordinates tree-sitter structural indexing across Python source files,
ADR documents, and CLAUDE.md configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_memory.graph import KnowledgeGraph


def build_index(
    project_root: Path,
    source_dirs: list[Path] | None = None,
    adr_dir: Path | None = None,
    config_path: Path | None = None,
) -> tuple[KnowledgeGraph, dict[Path, Any]]:
    """Build a full knowledge graph index from the project.

    Returns the graph and a tree cache for incremental re-parsing.
    """
    graph = KnowledgeGraph()
    tree_cache: dict[Path, Any] = {}

    # Default paths
    if source_dirs is None:
        source_dirs = [project_root / "src"]
    if adr_dir is None:
        adr_dir = project_root / "docs" / "adr"
    if config_path is None:
        config_path = project_root / "CLAUDE.md"

    # Phase 1: Python files
    from kg_memory.indexers.python_indexer import index_python_files

    for src_dir in source_dirs:
        if src_dir.exists():
            cache = index_python_files(graph, src_dir, project_root=project_root)
            tree_cache.update(cache)

    # Phase 2: ADR files
    from kg_memory.indexers.adr_indexer import index_adr_files

    if adr_dir.exists():
        index_adr_files(graph, adr_dir)

    # Phase 3: Config files
    from kg_memory.indexers.config_indexer import index_config_files

    if config_path.exists():
        index_config_files(graph, config_path)

    # Phase 4: Cross-link ADRs to modules
    _link_adr_to_modules(graph)

    return graph, tree_cache


def reindex_file(
    graph: KnowledgeGraph,
    tree_cache: dict[Path, Any],
    file_path: Path,
    project_root: Path,
) -> None:
    """Incrementally re-index a single file.

    Removes old nodes/edges for the file, then re-parses using
    the cached tree-sitter tree for efficiency.
    """
    rel_path = str(file_path.relative_to(project_root))
    graph.remove_file_nodes(rel_path)

    if file_path.suffix == ".py":
        from kg_memory.indexers.python_indexer import index_single_python_file

        old_tree = tree_cache.get(file_path)
        new_tree = index_single_python_file(
            graph, file_path, project_root=project_root, old_tree=old_tree
        )
        tree_cache[file_path] = new_tree
    elif file_path.suffix == ".md":
        if "adr" in str(file_path).lower():
            from kg_memory.indexers.adr_indexer import index_single_adr

            index_single_adr(graph, file_path)
        else:
            from kg_memory.indexers.config_indexer import index_config_files

            index_config_files(graph, file_path)


def _link_adr_to_modules(graph: KnowledgeGraph) -> None:
    """Create governs edges from ADRs to modules they reference.

    Scans ADR node properties for module path mentions and links them
    to existing file/module nodes via the path index.
    """
    from kg_memory.graph import Edge, EdgeType, NodeType

    adr_nodes = graph.get_nodes_by_type(NodeType.ADR)
    for adr in adr_nodes:
        governed = adr.properties.get("governed_paths", [])
        if isinstance(governed, list):
            for path_fragment in governed:
                # Try exact match first
                target_id = graph.path_index.get(path_fragment)
                if target_id is None:
                    # Try partial match
                    for indexed_path, node_id in graph.path_index.items():
                        if path_fragment in indexed_path:
                            target_id = node_id
                            break
                if target_id:
                    graph.add_edge(
                        Edge(
                            source=adr.id,
                            target=target_id,
                            edge_type=EdgeType.GOVERNS,
                        )
                    )

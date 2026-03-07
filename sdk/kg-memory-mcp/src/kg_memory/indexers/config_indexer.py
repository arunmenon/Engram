"""Tree-sitter based config file indexer (CLAUDE.md).

Parses CLAUDE.md using tree-sitter-markdown, extracts sections as config
nodes, identifies referenced file paths and module names, and creates
appropriate nodes and edges in the knowledge graph.

Produces:
- CONFIG nodes (NodeType.CONFIG) for each ## section with section heading, content, path
- GOVERNS edges from CONFIG nodes to file/module nodes referenced in code spans
- CONCEPT nodes (NodeType.CONCEPT) with DEFINES edges for named concepts
  extracted from tables (node types, edge types, intent types, etc.)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import tree_sitter_markdown
from tree_sitter import Language, Parser

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tree-sitter setup
# ---------------------------------------------------------------------------

_MD_LANGUAGE = Language(tree_sitter_markdown.language())


def _make_md_parser() -> Parser:
    return Parser(_MD_LANGUAGE)


_md_parser = _make_md_parser()

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Code spans (backtick-delimited)
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")

# Module/file path heuristic
_MODULE_PATH_RE = re.compile(
    r"^(?:src/)?(?:context_graph/)?"
    r"(?:domain|adapters|api|worker|ports|tests|docker|sdk)"
    r"(?:/[\w.*-]+)*(?:\.py)?/?$"
)

# Table row pattern: | cell1 | cell2 | ... |
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")

# Separator row: |---|---|
_TABLE_SEP_RE = re.compile(r"^\|[\s:_-]+\|")


# ---------------------------------------------------------------------------
# Tree-sitter section extraction
# ---------------------------------------------------------------------------


def _get_heading_text(heading_node: Any) -> str:
    """Extract text content from an atx_heading node."""
    for child in heading_node.children:
        if child.type == "inline":
            return child.text.decode("utf-8", errors="replace").strip()
    return heading_node.text.decode("utf-8", errors="replace").lstrip("#").strip()


def _get_heading_level(heading_node: Any) -> int:
    """Return heading level (1-6) from an atx_heading node."""
    for child in heading_node.children:
        if child.type.startswith("atx_h") and child.type.endswith("_marker"):
            return child.text.decode().count("#")
    return 1


def _collect_section(section_node: Any) -> dict[str, Any]:
    """Recursively collect a section and its subsections from the CST."""
    heading_text = ""
    heading_level = 0
    body_parts: list[str] = []
    subsections: list[dict[str, Any]] = []

    for child in section_node.children:
        if child.type == "atx_heading":
            heading_text = _get_heading_text(child)
            heading_level = _get_heading_level(child)
        elif child.type == "section":
            subsections.append(_collect_section(child))
        else:
            body_parts.append(child.text.decode("utf-8", errors="replace"))

    return {
        "heading": heading_text,
        "level": heading_level,
        "body_text": "\n".join(body_parts).strip(),
        "subsections": subsections,
    }


def _parse_document_sections(source_bytes: bytes) -> list[dict[str, Any]]:
    """Parse markdown and return the section tree."""
    tree = _md_parser.parse(source_bytes)
    sections: list[dict[str, Any]] = []
    for child in tree.root_node.children:
        if child.type == "section":
            sections.append(_collect_section(child))
    return sections


def _get_full_text(section: dict[str, Any]) -> str:
    """Get section body text including all subsection text."""
    parts = [section["body_text"]]
    for sub in section.get("subsections", []):
        parts.append(_get_full_text(sub))
    return "\n\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert heading text to a snake_case slug for node IDs."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    slug = re.sub(r"_+", "_", slug)
    return slug[:60]


def _extract_code_spans(text: str) -> list[str]:
    """Extract all backtick-delimited code spans from text."""
    return _CODE_SPAN_RE.findall(text)


def _filter_module_paths(code_spans: list[str]) -> list[str]:
    """Filter code spans to only file/module path patterns."""
    paths = []
    seen: set[str] = set()
    for span in code_spans:
        if _MODULE_PATH_RE.match(span) and span not in seen:
            paths.append(span)
            seen.add(span)
    return paths


def _resolve_module_path(graph: KnowledgeGraph, module_path: str) -> str | None:
    """Resolve a module path to an existing node ID via graph.path_index."""
    node_id = graph.path_index.get(module_path)
    if node_id:
        return node_id

    prefixed = f"src/context_graph/{module_path}"
    node_id = graph.path_index.get(prefixed)
    if node_id:
        return node_id

    stripped = module_path.rstrip("/")
    node_id = graph.path_index.get(stripped)
    if node_id:
        return node_id

    for indexed_path in graph.path_index:
        if indexed_path.startswith(module_path) or indexed_path.startswith(prefixed):
            return graph.path_index[indexed_path]

    return None


def _parse_table_rows(text: str) -> list[list[str]]:
    """Parse markdown table text into a list of rows (each row is a list of cells).

    Skips the header separator row. Returns empty list if not a valid table.
    """
    rows: list[list[str]] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if _TABLE_SEP_RE.match(line):
            continue
        row_match = _TABLE_ROW_RE.match(line)
        if row_match:
            cells = [cell.strip() for cell in row_match.group(1).split("|")]
            rows.append(cells)
    return rows


def _extract_concepts_from_table(
    table_rows: list[list[str]], section_heading: str
) -> list[dict[str, str]]:
    """Extract named concepts from table data.

    Looks for tables that list node types, edge types, intent types, etc.
    The first column is typically the concept name.
    """
    if len(table_rows) < 2:
        return []

    header = [h.lower() for h in table_rows[0]]
    concepts: list[dict[str, str]] = []

    # Detect the table type from header columns
    name_col = _find_column(
        header,
        [
            "node type",
            "edge type",
            "type",
            "intent",
            "consumer",
            "adr",
            "store",
            "parameter",
        ],
    )
    desc_col = _find_column(
        header,
        [
            "label",
            "description",
            "from",
            "from \u2192 to",
            "source",
            "role",
            "primary module",
            "data",
            "view",
        ],
    )

    if name_col is None:
        return []

    for row in table_rows[1:]:
        if name_col >= len(row):
            continue
        concept_name = row[name_col].strip().strip("`").strip(":")
        if not concept_name or concept_name == "---":
            continue

        description = ""
        if desc_col is not None and desc_col < len(row):
            description = row[desc_col].strip()

        concepts.append({"name": concept_name, "description": description})

    return concepts


def _find_column(header: list[str], candidates: list[str]) -> int | None:
    """Find the index of the first header column matching any candidate."""
    for i, col in enumerate(header):
        for candidate in candidates:
            if candidate in col:
                return i
    return None


def _collect_h2_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten to all level-2 sections, including nested inside level-1."""
    h2_sections: list[dict[str, Any]] = []
    for section in sections:
        if section["level"] == 2:
            h2_sections.append(section)
        for sub in section.get("subsections", []):
            if sub["level"] == 2:
                h2_sections.append(sub)
    return h2_sections


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_config_files(graph: KnowledgeGraph, config_path: Path) -> None:
    """Index CLAUDE.md into config and concept nodes.

    Creates:
    - CONFIG nodes for each ## section with section heading, content, path
    - GOVERNS edges from CONFIG nodes to file/module nodes referenced in code spans
    - CONCEPT nodes from table entries (node types, edge types, intent types)
      with DEFINES edges from the containing CONFIG node
    """
    if not config_path.exists():
        return

    try:
        _index_config(graph, config_path)
        logger.info("Indexed config file: %s", config_path.name)
    except Exception:
        logger.exception("Failed to index config: %s", config_path)


def _index_config(graph: KnowledgeGraph, file_path: Path) -> None:
    """Parse CLAUDE.md and populate the graph with config/concept nodes."""
    source_bytes = file_path.read_bytes()
    rel_path = str(file_path)

    sections = _parse_document_sections(source_bytes)
    h2_sections = _collect_h2_sections(sections)

    for section in h2_sections:
        section_heading = section["heading"]
        if not section_heading:
            continue

        section_slug = _slugify(section_heading)
        section_node_id = f"config:{section_slug}"
        full_text = _get_full_text(section)

        # -- Create CONFIG node --
        graph.add_node(
            Node(
                id=section_node_id,
                node_type=NodeType.CONFIG,
                name=section_heading,
                properties={
                    "path": rel_path,
                    "section": section_heading,
                    "content": full_text[:1000],
                    "source_file": rel_path,
                },
            )
        )

        # -- GOVERNS edges: code spans in this section that look like module paths --
        section_code_spans = _extract_code_spans(full_text)
        section_module_paths = _filter_module_paths(section_code_spans)
        for module_path in section_module_paths:
            target_node_id = _resolve_module_path(graph, module_path)
            if target_node_id:
                graph.add_edge(
                    Edge(
                        source=section_node_id,
                        target=target_node_id,
                        edge_type=EdgeType.GOVERNS,
                        properties={"module_path": module_path},
                    )
                )

        # -- CONCEPT nodes from tables in this section --
        _extract_section_concepts(graph, section, section_node_id, rel_path)


def _extract_section_concepts(
    graph: KnowledgeGraph,
    section: dict[str, Any],
    config_node_id: str,
    source_file: str,
) -> None:
    """Extract concept nodes from tables found in a section and its subsections."""
    # Tables in the section body
    table_rows = _parse_table_rows(section["body_text"])
    concepts = _extract_concepts_from_table(table_rows, section["heading"])
    for concept in concepts:
        _add_concept_node(graph, concept, config_node_id, source_file)

    # Check subsections (e.g., "### 11 Node Types" under "## Graph Schema")
    for sub in section.get("subsections", []):
        sub_rows = _parse_table_rows(sub["body_text"])
        sub_concepts = _extract_concepts_from_table(sub_rows, sub["heading"])
        for concept in sub_concepts:
            _add_concept_node(graph, concept, config_node_id, source_file)

        # One more level deep
        for subsub in sub.get("subsections", []):
            subsub_rows = _parse_table_rows(subsub["body_text"])
            subsub_concepts = _extract_concepts_from_table(subsub_rows, subsub["heading"])
            for concept in subsub_concepts:
                _add_concept_node(graph, concept, config_node_id, source_file)


def _add_concept_node(
    graph: KnowledgeGraph,
    concept: dict[str, str],
    config_node_id: str,
    source_file: str,
) -> None:
    """Create a CONCEPT node and a DEFINES edge from the config section."""
    concept_slug = _slugify(concept["name"])
    if not concept_slug:
        return
    concept_node_id = f"concept:{concept_slug}"

    graph.add_node(
        Node(
            id=concept_node_id,
            node_type=NodeType.CONCEPT,
            name=concept["name"],
            properties={
                "description": concept["description"],
                "source_file": source_file,
            },
        )
    )
    graph.add_edge(
        Edge(
            source=config_node_id,
            target=concept_node_id,
            edge_type=EdgeType.DEFINES,
        )
    )

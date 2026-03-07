"""Tree-sitter based ADR (Architecture Decision Record) indexer.

Parses ADR Markdown files using tree-sitter-markdown, extracts structural
information (title, status, sections, cross-references, module mentions),
and populates the in-memory KnowledgeGraph with nodes and edges.

Produces:
- ADR nodes (NodeType.ADR) with path, number, title, status, decision_summary
- REFERENCES edges between ADR nodes for cross-references (ADR-NNNN patterns)
- GOVERNS edges from ADR nodes to file/module nodes found in code spans
- CONCEPT nodes (NodeType.CONCEPT) with DEFINES edges from Decision subsections
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
    parser = Parser(_MD_LANGUAGE)
    return parser


_md_parser = _make_md_parser()

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# ADR cross-references: "ADR-0009", "ADR 0005", "ADR-0009"
_ADR_CROSS_REF_RE = re.compile(r"ADR[- ]?(\d{4})")

# ADR filename: 0009-multi-graph-schema.md
_ADR_FILENAME_RE = re.compile(r"^(\d{4})-(.+)\.md$")

# Code spans (backtick-delimited)
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")

# Module/file path heuristic
_MODULE_PATH_RE = re.compile(
    r"^(?:src/)?(?:context_graph/)?"
    r"(?:domain|adapters|api|worker|ports|tests|docker|sdk)"
    r"(?:/[\w.-]+)*(?:\.py)?/?$"
)

# Status line: "Status: **Accepted**" or "Status: **Proposed — Amended**"
_STATUS_LINE_RE = re.compile(r"^Status:\s*\*{0,2}(.+?)\*{0,2}\s*$", re.MULTILINE)

# Generic headings to skip when extracting concepts
_GENERIC_HEADINGS = frozenset(
    {
        "decision",
        "overview",
        "summary",
        "notes",
        "references",
        "examples",
        "non-goals",
        "non-goals for this decision",
        "non-goals for mvp",
        "implementation path (if adopted)",
        "evaluation criteria before adoption",
        "recommendation",
    }
)


# ---------------------------------------------------------------------------
# Tree-sitter section extraction
# ---------------------------------------------------------------------------


def _get_heading_text(heading_node: Any) -> str:
    """Extract text content from an atx_heading node (strips # markers)."""
    for child in heading_node.children:
        if child.type == "inline":
            return child.text.decode("utf-8", errors="replace").strip()
    # Fallback
    return heading_node.text.decode("utf-8", errors="replace").lstrip("#").strip()


def _get_heading_level(heading_node: Any) -> int:
    """Return heading level (1-6) from an atx_heading node."""
    for child in heading_node.children:
        if child.type.startswith("atx_h") and child.type.endswith("_marker"):
            return child.text.decode().count("#")
    return 1


def _collect_sections(
    section_node: Any,
) -> list[dict[str, Any]]:
    """Recursively collect section hierarchy from the tree-sitter CST.

    Returns a flat list of section dicts. Each has:
    - heading: str
    - level: int (1-6)
    - body_text: str (text of paragraphs, lists, tables, code blocks)
    - subsections: list[dict] (nested sections)
    """
    heading_text = ""
    heading_level = 0
    body_parts: list[str] = []
    subsections: list[dict[str, Any]] = []

    for child in section_node.children:
        if child.type == "atx_heading":
            heading_text = _get_heading_text(child)
            heading_level = _get_heading_level(child)
        elif child.type == "section":
            subsections.append(_collect_sections(child))
        else:
            # paragraph, list, table, fenced_code_block, etc.
            body_parts.append(child.text.decode("utf-8", errors="replace"))

    return {
        "heading": heading_text,
        "level": heading_level,
        "body_text": "\n".join(body_parts).strip(),
        "subsections": subsections,
    }


def _parse_document_sections(source_bytes: bytes) -> list[dict[str, Any]]:
    """Parse markdown source and return the top-level section tree."""
    tree = _md_parser.parse(source_bytes)
    root = tree.root_node
    sections: list[dict[str, Any]] = []

    for child in root.children:
        if child.type == "section":
            sections.append(_collect_sections(child))

    return sections


def _find_section(sections: list[dict[str, Any]], heading_lower: str) -> dict[str, Any] | None:
    """Find a section by heading text (case-insensitive), searching recursively."""
    for section in sections:
        if section["heading"].lower() == heading_lower:
            return section
        found = _find_section(section.get("subsections", []), heading_lower)
        if found:
            return found
    return None


def _get_full_text(section: dict[str, Any]) -> str:
    """Get the full text of a section including all nested subsection text."""
    parts = [section["body_text"]]
    for sub in section.get("subsections", []):
        parts.append(_get_full_text(sub))
    return "\n\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_adr_number(file_path: Path) -> str | None:
    """Extract the 4-digit ADR number from the filename."""
    match = _ADR_FILENAME_RE.match(file_path.name)
    if match:
        return match.group(1)
    # Fallback: leading digits
    digit_match = re.match(r"(\d+)", file_path.stem)
    if digit_match:
        return digit_match.group(1).zfill(4)
    return None


def _extract_title(sections: list[dict[str, Any]], source_text: str) -> str:
    """Extract the ADR title from the h1 heading."""
    for section in sections:
        if section["level"] == 1:
            title = section["heading"]
            # Strip "ADR-NNNN: " or "N. " prefix
            title = re.sub(r"^ADR[- ]?\d{4}:\s*", "", title)
            title = re.sub(r"^\d+\.\s*", "", title)
            return title.strip()
    # Fallback: first line
    first_line = source_text.split("\n", 1)[0].lstrip("#").strip()
    first_line = re.sub(r"^ADR[- ]?\d{4}:\s*", "", first_line)
    return first_line


def _extract_status(source_text: str) -> str:
    """Extract the status from the Status: line."""
    match = _STATUS_LINE_RE.search(source_text)
    if match:
        return match.group(1).strip()
    return "Unknown"


def _extract_decision_summary(sections: list[dict[str, Any]]) -> str:
    """Extract the first paragraph of the Decision section."""
    decision = _find_section(sections, "decision")
    if not decision or not decision["body_text"]:
        return ""

    text = decision["body_text"]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        summary = paragraphs[0]
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary
    return ""


def _extract_code_spans(text: str) -> list[str]:
    """Extract all backtick-delimited code spans from text."""
    return _CODE_SPAN_RE.findall(text)


def _filter_module_paths(code_spans: list[str]) -> list[str]:
    """Filter code spans to only file/module path patterns."""
    paths = []
    seen = set()
    for span in code_spans:
        if _MODULE_PATH_RE.match(span) and span not in seen:
            paths.append(span)
            seen.add(span)
    return paths


def _extract_adr_references(text: str, own_number: str) -> list[str]:
    """Find cross-references to other ADRs. Returns sorted list of 4-digit numbers."""
    refs = set()
    for match in _ADR_CROSS_REF_RE.finditer(text):
        number = match.group(1)
        if number != own_number:
            refs.add(number)
    return sorted(refs)


def _slugify(text: str) -> str:
    """Convert text to a snake_case slug for node IDs."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    slug = re.sub(r"_+", "_", slug)
    return slug[:80]


def _extract_concepts(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract concepts from Decision section subsection headings.

    Each subsection heading under Decision becomes a concept node, with
    the subsection body as its description.
    """
    decision = _find_section(sections, "decision")
    if not decision:
        return []

    concepts: list[dict[str, str]] = []
    for sub in decision.get("subsections", []):
        heading = sub["heading"]
        if not heading or heading.lower() in _GENERIC_HEADINGS:
            continue
        description = sub["body_text"][:300] if sub["body_text"] else ""
        concepts.append({"name": heading, "description": description})

    return concepts


def _resolve_module_path(graph: KnowledgeGraph, module_path: str) -> str | None:
    """Try to resolve a module path to a node ID via graph.path_index.

    Tries exact match, then common prefix variations.
    """
    # Exact match
    node_id = graph.path_index.get(module_path)
    if node_id:
        return node_id

    # Try with src/context_graph/ prefix
    prefixed = f"src/context_graph/{module_path}"
    node_id = graph.path_index.get(prefixed)
    if node_id:
        return node_id

    # Strip trailing slash
    stripped = module_path.rstrip("/")
    node_id = graph.path_index.get(stripped)
    if node_id:
        return node_id

    # Prefix match: find any indexed path that starts with this path
    for indexed_path in graph.path_index:
        if indexed_path.startswith(module_path) or indexed_path.startswith(prefixed):
            return graph.path_index[indexed_path]

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_adr_files(graph: KnowledgeGraph, adr_dir: Path) -> None:
    """Index all ADR Markdown files in the directory.

    Two-pass approach:
    1. Create all ADR nodes, concept nodes, and GOVERNS/DEFINES edges.
    2. Resolve ADR cross-references (REFERENCES edges) now that all ADR nodes exist.
    """
    if not adr_dir.is_dir():
        return

    adr_files = sorted(adr_dir.glob("*.md"))
    adr_files = [f for f in adr_files if _ADR_FILENAME_RE.match(f.name)]

    # First pass: create nodes and non-cross-ref edges
    pending_cross_refs: list[tuple[str, list[str]]] = []
    for file_path in adr_files:
        try:
            refs = _index_adr_first_pass(graph, file_path)
            if refs:
                pending_cross_refs.append(refs)
        except Exception:
            logger.exception("Failed to index ADR: %s", file_path)

    # Second pass: create cross-reference edges (all ADR nodes now exist)
    for adr_node_id, ref_numbers in pending_cross_refs:
        for ref_number in ref_numbers:
            target_id = f"adr:{ref_number}"
            graph.add_edge(
                Edge(
                    source=adr_node_id,
                    target=target_id,
                    edge_type=EdgeType.REFERENCES,
                    properties={"reference_type": "cross_reference"},
                )
            )

    logger.info("Indexed %d ADR files from %s", len(adr_files), adr_dir)


def index_single_adr(graph: KnowledgeGraph, file_path: Path) -> None:
    """Index a single ADR file into the graph.

    Cross-reference edges are created immediately (targets must already exist).
    """
    result = _index_adr_first_pass(graph, file_path)
    if result:
        adr_node_id, ref_numbers = result
        for ref_number in ref_numbers:
            target_id = f"adr:{ref_number}"
            graph.add_edge(
                Edge(
                    source=adr_node_id,
                    target=target_id,
                    edge_type=EdgeType.REFERENCES,
                    properties={"reference_type": "cross_reference"},
                )
            )


def _index_adr_first_pass(graph: KnowledgeGraph, file_path: Path) -> tuple[str, list[str]] | None:
    """Create the ADR node, concept nodes, GOVERNS edges, and DEFINES edges.

    Returns (adr_node_id, list_of_cross_ref_numbers) for deferred edge creation,
    or None if the file cannot be parsed.
    """
    adr_number = _extract_adr_number(file_path)
    if adr_number is None:
        return None

    source_bytes = file_path.read_bytes()
    source_text = source_bytes.decode("utf-8", errors="replace")

    sections = _parse_document_sections(source_bytes)

    title = _extract_title(sections, source_text)
    status = _extract_status(source_text)
    decision_summary = _extract_decision_summary(sections)

    # -- Create ADR node --
    adr_node_id = f"adr:{adr_number}"
    graph.add_node(
        Node(
            id=adr_node_id,
            node_type=NodeType.ADR,
            name=title,
            properties={
                "path": str(file_path),
                "number": adr_number,
                "title": title,
                "status": status,
                "decision_summary": decision_summary,
                "source_file": str(file_path),
            },
        )
    )

    # -- GOVERNS edges: code spans that look like module paths --
    code_spans = _extract_code_spans(source_text)
    module_paths = _filter_module_paths(code_spans)
    for module_path in module_paths:
        target_node_id = _resolve_module_path(graph, module_path)
        if target_node_id:
            graph.add_edge(
                Edge(
                    source=adr_node_id,
                    target=target_node_id,
                    edge_type=EdgeType.GOVERNS,
                    properties={"module_path": module_path},
                )
            )

    # -- CONCEPT nodes with DEFINES edges from Decision subsections --
    concepts = _extract_concepts(sections)
    for concept in concepts:
        concept_slug = _slugify(concept["name"])
        if not concept_slug:
            continue
        concept_node_id = f"concept:{concept_slug}"
        graph.add_node(
            Node(
                id=concept_node_id,
                node_type=NodeType.CONCEPT,
                name=concept["name"],
                properties={
                    "description": concept["description"],
                    "source_file": str(file_path),
                    "source_adr": adr_number,
                },
            )
        )
        graph.add_edge(
            Edge(
                source=adr_node_id,
                target=concept_node_id,
                edge_type=EdgeType.DEFINES,
            )
        )

    # -- Collect cross-references for deferred edge creation --
    adr_refs = _extract_adr_references(source_text, adr_number)
    return (adr_node_id, adr_refs)

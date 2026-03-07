"""Seven MCP tool definitions for the KG Memory server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import TextContent, Tool

if TYPE_CHECKING:
    from mcp.server import Server

    from kg_memory.server import KGMemoryServer

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="kg_search",
        description=(
            "Search the codebase knowledge graph by keyword or concept. "
            "Returns matching files, classes, functions, ADRs, and concepts "
            "ranked by relevance."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (keyword or concept name)",
                },
                "node_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Filter by node types: module, class, function, file, "
                        "adr, decision, concept, trade_off, config"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="kg_relate",
        description=(
            "Get related nodes for a given node ID. Expands the neighborhood "
            "via BFS traversal, optionally filtered by edge type."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The node ID to expand from (e.g., 'file:src/context_graph/domain/models.py')",
                },
                "edge_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Filter by edge types: contains, imports, calls, inherits, "
                        "method_of, depends_on, references, governs, decided_in, "
                        "defines, implements, same_as, related_to"
                    ),
                },
                "depth": {
                    "type": "integer",
                    "description": "Max traversal depth (hops)",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 5,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum nodes to return",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["node_id"],
        },
    ),
    Tool(
        name="kg_context",
        description=(
            "Get full context for a file path: contained classes/functions, "
            "imports, dependents, governing ADRs, related concepts, and "
            "architectural decisions."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative file path (e.g., 'src/context_graph/domain/scoring.py')",
                },
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="kg_path",
        description=(
            "Find the shortest path connecting two nodes in the knowledge graph. "
            "Useful for understanding how two concepts or files are related."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source node ID",
                },
                "target": {
                    "type": "string",
                    "description": "Target node ID",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum path length",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["source", "target"],
        },
    ),
    Tool(
        name="kg_ask",
        description=(
            "Ask a natural language question about the codebase. Uses the "
            "knowledge graph to find relevant context, then synthesizes an "
            "answer with provenance citations. Requires LLM to be enabled."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about the codebase",
                },
            },
            "required": ["question"],
        },
    ),
    Tool(
        name="kg_reindex",
        description=(
            "Trigger a full re-index of the codebase. Rebuilds the knowledge "
            "graph from scratch: structural parsing, LLM extraction, and "
            "entity reconciliation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "llm": {
                    "type": "boolean",
                    "description": "Run LLM extraction (slower but richer)",
                    "default": True,
                },
            },
        },
    ),
    Tool(
        name="kg_status",
        description=(
            "Show knowledge graph statistics: node/edge counts by type, "
            "reconciliation stats, file watcher status, and index freshness."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(server: Server, mcp_server: KGMemoryServer) -> None:
    """Register all 7 KG Memory tools with the MCP server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        handlers = {
            "kg_search": _handle_search,
            "kg_relate": _handle_relate,
            "kg_context": _handle_context,
            "kg_path": _handle_path,
            "kg_ask": _handle_ask,
            "kg_reindex": _handle_reindex,
            "kg_status": _handle_status,
        }
        handler = handlers.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            return await handler(mcp_server, arguments)
        except Exception as exc:
            return [TextContent(type="text", text=f"Error: {exc}")]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def _handle_search(
    mcp_server: KGMemoryServer, arguments: dict[str, Any]
) -> list[TextContent]:
    query = arguments["query"]
    node_types = arguments.get("node_types")
    limit = min(arguments.get("limit", 20), 100)

    results = mcp_server.retriever.search(query, node_types=node_types, limit=limit)

    if not results:
        return [TextContent(type="text", text=f"No results found for: {query}")]

    lines = [f"# Search: {query}\n", f"*{len(results)} results*\n"]

    for result in results:
        score_str = f" [{result.score:.2f}]"
        props = result.properties
        detail = ""
        if result.node_type == "file":
            detail = f" ({props.get('path', '')})"
        elif result.node_type == "adr":
            detail = f" — {props.get('title', '')}"
        elif result.node_type == "concept":
            defn = props.get("definition", "")
            if defn:
                detail = f" — {defn[:80]}"
        elif result.node_type in ("class", "function"):
            detail = f" ({props.get('path', '')}:{props.get('line', '')})"

        lines.append(f"- **{result.name}** ({result.node_type}){score_str}{detail}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_relate(
    mcp_server: KGMemoryServer, arguments: dict[str, Any]
) -> list[TextContent]:
    node_id = arguments["node_id"]
    edge_types = arguments.get("edge_types")
    depth = min(arguments.get("depth", 1), 5)
    limit = min(arguments.get("limit", 30), 100)

    result = mcp_server.retriever.get_neighbors(
        node_id, edge_types=edge_types, depth=depth, limit=limit
    )

    if not result.nodes:
        return [TextContent(type="text", text=f"Node not found: {node_id}")]

    lines = [f"# Neighborhood: {node_id}\n"]
    lines.append(f"*{len(result.nodes)} nodes, {len(result.edges)} edges (depth={depth})*\n")

    # Group nodes by type
    by_type: dict[str, list] = {}
    for node in result.nodes.values():
        by_type.setdefault(node.node_type, []).append(node)

    for ntype, nodes in sorted(by_type.items()):
        lines.append(f"## {ntype} ({len(nodes)})")
        for node in nodes:
            lines.append(f"- **{node.name}** (`{node.id}`)")
        lines.append("")

    # Edges
    if result.edges:
        lines.append(f"## Edges ({len(result.edges)})")
        for edge in result.edges[:30]:
            lines.append(f"- {edge['source']} --[{edge['edge_type']}]--> {edge['target']}")
        if len(result.edges) > 30:
            lines.append(f"  ... and {len(result.edges) - 30} more")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_context(
    mcp_server: KGMemoryServer, arguments: dict[str, Any]
) -> list[TextContent]:
    file_path = arguments["file_path"]
    ctx = mcp_server.retriever.file_context(file_path)

    if ctx.file_node is None:
        return [TextContent(type="text", text=f"File not found in graph: {file_path}")]

    lines = [f"# File Context: {file_path}\n"]

    # Structure
    lines.append("## Structure")
    lines.append(f"- Module: {ctx.module}")
    if ctx.classes:
        class_names = ", ".join(c.name for c in ctx.classes)
        lines.append(f"- Classes: {class_names}")
    if ctx.functions:
        func_names = ", ".join(f.name for f in ctx.functions)
        lines.append(f"- Functions: {func_names}")
    size = ctx.file_node.properties.get("size_lines", "?")
    lines.append(f"- Lines: {size}")
    lines.append("")

    # Imports
    if ctx.imports:
        lines.append("## Imports")
        for imp in ctx.imports:
            lines.append(f"- -> {imp}")
        lines.append("")

    # Governing ADRs
    if ctx.governing_adrs:
        lines.append("## Governing ADRs")
        for adr in ctx.governing_adrs:
            title = adr.properties.get("title", adr.name)
            lines.append(f"- {adr.name}: {title}")
        lines.append("")

    # Decisions
    if ctx.decisions:
        lines.append("## Decisions (LLM-extracted)")
        for dec in ctx.decisions:
            stmt = dec.properties.get("statement", dec.name)
            lines.append(f'- "{stmt}"')
        lines.append("")

    # Related Concepts
    if ctx.related_concepts:
        lines.append("## Related Concepts")
        concept_names = ", ".join(c.name for c in ctx.related_concepts)
        lines.append(f"- {concept_names}")
        lines.append("")

    # Dependents
    if ctx.dependents:
        lines.append("## Dependents (who imports this)")
        for dep in ctx.dependents:
            lines.append(f"- {dep}")
        lines.append("")

    # Reconciled links
    if ctx.reconciled_links:
        lines.append("## Entity Links (reconciled)")
        for link in ctx.reconciled_links:
            src = link.get("source_name", link.get("source", ""))
            tgt = link.get("target_name", link.get("target", ""))
            lines.append(f'- "{src}" <-SAME_AS-> "{tgt}"')
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_path(mcp_server: KGMemoryServer, arguments: dict[str, Any]) -> list[TextContent]:
    source = arguments["source"]
    target = arguments["target"]
    max_depth = min(arguments.get("max_depth", 5), 10)

    path = mcp_server.retriever.find_path(source, target, max_depth=max_depth)

    if path is None:
        return [
            TextContent(
                type="text",
                text=f"No path found between `{source}` and `{target}` within depth {max_depth}",
            )
        ]

    lines = [f"# Path: {source} -> {target}\n"]
    lines.append(f"*{len(path)} nodes, {len(path) - 1} hops*\n")

    for i, node_id in enumerate(path):
        node = mcp_server.graph.get_node(node_id)
        name = node.name if node else node_id
        ntype = node.node_type if node else "?"
        prefix = "  " * i
        connector = "-> " if i > 0 else ""
        lines.append(f"{prefix}{connector}**{name}** ({ntype}: `{node_id}`)")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_ask(mcp_server: KGMemoryServer, arguments: dict[str, Any]) -> list[TextContent]:
    question = arguments["question"]

    if not mcp_server.llm_enabled or mcp_server.extractor is None:
        return [
            TextContent(
                type="text",
                text="LLM is not enabled. Set KG_LLM_ENABLED=true to use kg_ask.",
            )
        ]

    # Step 1: Search graph for relevant nodes
    search_results = mcp_server.retriever.search(question, limit=10)

    if not search_results:
        return [
            TextContent(
                type="text",
                text=f"No relevant nodes found for: {question}",
            )
        ]

    # Step 2: Expand neighborhood
    all_nodes: dict[str, Any] = {}
    for result in search_results[:5]:
        subgraph = mcp_server.retriever.get_neighbors(result.node_id, depth=1, limit=10)
        for nid, node in subgraph.nodes.items():
            all_nodes[nid] = node

    # Step 3: Format context
    context_parts: list[str] = []
    for node in all_nodes.values():
        desc = f"[{node.node_type}] {node.name}"
        if node.properties.get("path"):
            desc += f" (path: {node.properties['path']})"
        if node.properties.get("title"):
            desc += f" — {node.properties['title']}"
        if node.properties.get("docstring"):
            doc = node.properties["docstring"][:200]
            desc += f"\n  Docstring: {doc}"
        if node.properties.get("statement"):
            desc += f"\n  Decision: {node.properties['statement']}"
        if node.properties.get("definition"):
            desc += f"\n  Definition: {node.properties['definition']}"
        context_parts.append(desc)

    context_str = "\n".join(context_parts)

    # Step 4: Ask LLM
    answer = await mcp_server.extractor.answer_question(question, context_str)

    # Step 5: Format response with provenance
    lines = [f"# Answer: {question}\n"]
    lines.append(answer)
    lines.append("\n## Sources")
    for result in search_results[:5]:
        lines.append(f"- **{result.name}** ({result.node_type}, score={result.score:.2f})")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_reindex(
    mcp_server: KGMemoryServer, arguments: dict[str, Any]
) -> list[TextContent]:
    run_llm = arguments.get("llm", True)
    stats = await mcp_server.reindex(run_llm=run_llm)

    lines = ["# Reindex Complete\n"]
    lines.append(f"- **Nodes**: {stats['total_nodes']}")
    lines.append(f"- **Edges**: {stats['total_edges']}")
    lines.append(f"- **Files indexed**: {stats['indexed_paths']}")
    lines.append(f"- **LLM extraction**: {'yes' if run_llm else 'no'}")

    if stats.get("node_counts"):
        lines.append("\n## Node Counts")
        for ntype, count in sorted(stats["node_counts"].items()):
            lines.append(f"- {ntype}: {count}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_status(
    mcp_server: KGMemoryServer, arguments: dict[str, Any]
) -> list[TextContent]:
    stats = mcp_server.retriever.get_stats()

    lines = ["# KG Memory Status\n"]

    # Graph size
    lines.append("## Graph Size")
    lines.append(f"- Nodes: {stats.total_nodes} | Edges: {stats.total_edges}")
    lines.append(f"- Files indexed: {stats.indexed_paths}")
    lines.append("")

    # Node types
    if stats.node_counts:
        lines.append("## Node Types")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for ntype, count in sorted(stats.node_counts.items()):
            lines.append(f"| {ntype} | {count} |")
        lines.append("")

    # Edge types
    if stats.edge_counts:
        lines.append("## Edge Types")
        lines.append("| Type | Count |")
        lines.append("|------|-------|")
        for etype, count in sorted(stats.edge_counts.items()):
            lines.append(f"| {etype} | {count} |")
        lines.append("")

    # Reconciliation
    lines.append("## Reconciliation")
    lines.append(f"- Entity clusters: {stats.reconciliation_clusters}")
    lines.append(f"- SAME_AS edges: {stats.same_as_edges}")
    lines.append(f"- RELATED_TO edges: {stats.related_to_edges}")
    lines.append("")

    # Metadata
    watcher_status = "Active" if mcp_server._watcher is not None else "Disabled"
    lines.append(f"## File Watcher: {watcher_status}")
    if mcp_server.last_indexed:
        lines.append(f"## Last indexed: {mcp_server.last_indexed.isoformat()}")
    lines.append(f"## LLM model: {mcp_server.llm_model}")
    lines.append(f"## LLM enabled: {mcp_server.llm_enabled}")

    return [TextContent(type="text", text="\n".join(lines))]

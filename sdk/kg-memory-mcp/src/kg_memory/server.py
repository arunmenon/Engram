"""KG Memory MCP Server — entry point and lifecycle management.

Auto-indexes the codebase on startup (from JSON cache or full rebuild),
starts a file watcher for live updates, and exposes 7 MCP tools for
graph-based retrieval.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from kg_memory.graph import KnowledgeGraph
from kg_memory.persistence import load_graph, save_graph
from kg_memory.retrieval import Retriever
from kg_memory.tools import register_tools


class KGMemoryServer:
    """MCP server wrapping the in-memory knowledge graph."""

    def __init__(self) -> None:
        self._project_root = Path(os.environ.get("KG_PROJECT_ROOT", os.getcwd()))
        self._index_file = self._project_root / os.environ.get("KG_INDEX_FILE", ".kg-index.json")
        self._watch_enabled = os.environ.get("KG_WATCH_ENABLED", "true").lower() == "true"
        self._llm_enabled = os.environ.get("KG_LLM_ENABLED", "false").lower() == "true"
        self._llm_model = os.environ.get("KG_LLM_MODEL", "claude-sonnet-4-6")

        self._graph = KnowledgeGraph()
        self._retriever = Retriever(self._graph)
        self._tree_cache: dict[Path, Any] = {}
        self._watcher: Any = None
        self._extractor: Any = None
        self._last_indexed: datetime | None = None
        self._server = Server("kg-memory")

    @property
    def graph(self) -> KnowledgeGraph:
        return self._graph

    @property
    def retriever(self) -> Retriever:
        return self._retriever

    @property
    def extractor(self) -> Any:
        return self._extractor

    @property
    def project_root(self) -> Path:
        return self._project_root

    @property
    def last_indexed(self) -> datetime | None:
        return self._last_indexed

    @property
    def llm_model(self) -> str:
        return self._llm_model

    @property
    def llm_enabled(self) -> bool:
        return self._llm_enabled

    async def start(self) -> None:
        """Initialize: load or build index, start watcher, register tools."""
        # Try loading from cache
        cached_graph = load_graph(self._index_file)
        if cached_graph is not None:
            self._graph = cached_graph
            self._retriever = Retriever(self._graph)
            self._last_indexed = datetime.now(timezone.utc)
            print(
                f"[kg-memory] Loaded graph from cache: {self._graph.stats()['total_nodes']} nodes"
            )
        else:
            await self.reindex(run_llm=self._llm_enabled)

        # Initialize LLM extractor if enabled
        if self._llm_enabled:
            try:
                from kg_memory.extraction import LLMExtractor

                self._extractor = LLMExtractor(model_id=self._llm_model)
            except ImportError:
                print("[kg-memory] LLM extraction unavailable (litellm not installed)")

        # Start file watcher
        if self._watch_enabled:
            try:
                from kg_memory.watcher import GraphFileWatcher

                self._watcher = GraphFileWatcher(
                    graph=self._graph,
                    tree_cache=self._tree_cache,
                    project_root=self._project_root,
                    persistence_path=self._index_file,
                    llm_extractor=self._extractor,
                )
                self._watcher.start()
                print("[kg-memory] File watcher started")
            except ImportError:
                print("[kg-memory] File watcher unavailable (watchdog not installed)")

        # Register MCP tools
        register_tools(self._server, self)

    async def reindex(self, run_llm: bool = True) -> dict[str, Any]:
        """Full re-index of the codebase.

        1. Tree-sitter structural indexing (Python + Markdown)
        2. LLM semantic extraction (if enabled)
        3. Entity reconciliation
        4. Save to disk
        """
        start_time = time.monotonic()
        self._graph = KnowledgeGraph()
        self._retriever = Retriever(self._graph)
        self._tree_cache.clear()

        # Phase 1: Structural indexing
        try:
            from kg_memory.indexers.python_indexer import index_python_files

            src_dir = self._project_root / "src"
            if src_dir.exists():
                tree_cache = index_python_files(
                    self._graph, src_dir, project_root=self._project_root
                )
                self._tree_cache.update(tree_cache)
                print(f"[kg-memory] Indexed Python files: {len(tree_cache)} files")
        except Exception as exc:
            print(f"[kg-memory] Python indexing failed: {exc}")

        try:
            from kg_memory.indexers.adr_indexer import index_adr_files

            adr_dir = self._project_root / "docs" / "adr"
            if adr_dir.exists():
                index_adr_files(self._graph, adr_dir)
                print("[kg-memory] Indexed ADR files")
        except Exception as exc:
            print(f"[kg-memory] ADR indexing failed: {exc}")

        try:
            from kg_memory.indexers.config_indexer import index_config_files

            claude_md = self._project_root / "CLAUDE.md"
            if claude_md.exists():
                index_config_files(self._graph, claude_md)
                print("[kg-memory] Indexed CLAUDE.md")
        except Exception as exc:
            print(f"[kg-memory] Config indexing failed: {exc}")

        # Phase 2: LLM extraction (optional)
        if run_llm and self._extractor is not None:
            try:
                from kg_memory.extraction import apply_extraction_to_graph

                adr_nodes = self._graph.get_nodes_by_type("adr")
                for adr_node in adr_nodes:
                    adr_path = adr_node.properties.get("path", "")
                    full_path = self._project_root / adr_path
                    if full_path.exists():
                        adr_text = full_path.read_text()
                        extraction = await self._extractor.extract_adr(adr_text, adr_path)
                        apply_extraction_to_graph(self._graph, adr_node.id, extraction)
                print(f"[kg-memory] LLM extraction complete for {len(adr_nodes)} ADRs")
            except Exception as exc:
                print(f"[kg-memory] LLM extraction failed: {exc}")

        # Phase 3: Entity reconciliation
        try:
            from kg_memory.reconciliation import reconcile_graph

            results = await reconcile_graph(self._graph, extractor=self._extractor)
            print(f"[kg-memory] Reconciliation: {len(results)} links created")
        except Exception as exc:
            print(f"[kg-memory] Reconciliation failed: {exc}")

        # Save to disk
        save_graph(self._graph, self._index_file)
        self._last_indexed = datetime.now(timezone.utc)

        elapsed = time.monotonic() - start_time
        stats = self._graph.stats()
        print(
            f"[kg-memory] Reindex complete in {elapsed:.1f}s: "
            f"{stats['total_nodes']} nodes, {stats['total_edges']} edges"
        )
        return stats

    async def shutdown(self) -> None:
        """Stop watcher and save graph."""
        if self._watcher is not None:
            self._watcher.stop()
        save_graph(self._graph, self._index_file)
        print("[kg-memory] Shutdown complete")

    async def run(self) -> None:
        """Run the MCP server over stdio."""
        await self.start()
        try:
            async with stdio_server() as (read_stream, write_stream):
                init_options = self._server.create_initialization_options()
                await self._server.run(read_stream, write_stream, init_options)
        finally:
            await self.shutdown()


def main() -> None:
    """Entry point for `kg-memory-mcp` CLI command."""
    server = KGMemoryServer()
    asyncio.run(server.run())

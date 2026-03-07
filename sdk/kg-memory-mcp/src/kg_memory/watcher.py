"""File watcher for incremental graph updates.

Uses watchdog to monitor source files, ADRs, and CLAUDE.md for changes.
Python files get fast tree-sitter incremental re-parsing. Markdown files
also queue async LLM re-extraction when the extractor is available.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from kg_memory.graph import KnowledgeGraph
from kg_memory.persistence import save_graph

if TYPE_CHECKING:
    from kg_memory.extraction import LLMExtractor


# ---------------------------------------------------------------------------
# Debounced handler
# ---------------------------------------------------------------------------

_STRUCTURAL_DEBOUNCE_SEC = 0.5
_LLM_DEBOUNCE_SEC = 5.0


class _DebouncedHandler(FileSystemEventHandler):
    """Debounces rapid file changes and dispatches to the graph updater."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        tree_cache: dict[Path, Any],
        project_root: Path,
        persistence_path: Path,
        llm_extractor: LLMExtractor | None = None,
    ) -> None:
        self._graph = graph
        self._tree_cache = tree_cache
        self._project_root = project_root
        self._persistence_path = persistence_path
        self._llm_extractor = llm_extractor
        self._pending: dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._schedule(str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = str(event.src_path)
        rel_path = str(Path(path).relative_to(self._project_root))
        self._graph.remove_file_nodes(rel_path)
        self._tree_cache.pop(Path(path), None)
        save_graph(self._graph, self._persistence_path)

    def _schedule(self, abs_path: str) -> None:
        """Schedule a debounced re-index for the given file."""
        with self._lock:
            self._pending[abs_path] = time.monotonic()
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(_STRUCTURAL_DEBOUNCE_SEC, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        """Process all pending file changes."""
        with self._lock:
            pending = dict(self._pending)
            self._pending.clear()

        for abs_path in pending:
            path = Path(abs_path)
            if not path.exists():
                continue

            try:
                rel_path = str(path.relative_to(self._project_root))
            except ValueError:
                continue

            if path.suffix == ".py":
                self._reindex_python(path, rel_path)
            elif path.suffix == ".md":
                self._reindex_markdown(path, rel_path)

        save_graph(self._graph, self._persistence_path)

    def _reindex_python(self, abs_path: Path, rel_path: str) -> None:
        """Incremental re-index a Python file using tree-sitter."""
        try:
            from kg_memory.indexers.python_indexer import index_single_python_file

            # Remove old nodes for this file
            self._graph.remove_file_nodes(rel_path)

            old_tree = self._tree_cache.get(abs_path)
            new_tree = index_single_python_file(
                self._graph,
                abs_path,
                project_root=self._project_root,
                old_tree=old_tree,
            )
            self._tree_cache[abs_path] = new_tree
        except Exception as exc:
            print(f"[kg-memory] Watcher: Python re-index failed for {rel_path}: {exc}")

    def _reindex_markdown(self, abs_path: Path, rel_path: str) -> None:
        """Re-index a Markdown file (ADR or CLAUDE.md)."""
        try:
            # Remove old nodes for this file
            self._graph.remove_file_nodes(rel_path)

            if "adr" in rel_path.lower():
                from kg_memory.indexers.adr_indexer import index_single_adr

                index_single_adr(self._graph, abs_path)
            elif rel_path.endswith("CLAUDE.md"):
                from kg_memory.indexers.config_indexer import index_config_files

                index_config_files(self._graph, abs_path)
        except Exception as exc:
            print(f"[kg-memory] Watcher: Markdown re-index failed for {rel_path}: {exc}")


# ---------------------------------------------------------------------------
# File watcher
# ---------------------------------------------------------------------------


class GraphFileWatcher:
    """Watches project files and incrementally updates the knowledge graph."""

    def __init__(
        self,
        graph: KnowledgeGraph,
        tree_cache: dict[Path, Any],
        project_root: Path,
        persistence_path: Path,
        llm_extractor: LLMExtractor | None = None,
    ) -> None:
        self._project_root = project_root
        self._handler = _DebouncedHandler(
            graph=graph,
            tree_cache=tree_cache,
            project_root=project_root,
            persistence_path=persistence_path,
            llm_extractor=llm_extractor,
        )
        self._observer = Observer()

        # Watch directories
        src_dir = project_root / "src"
        adr_dir = project_root / "docs" / "adr"
        claude_md = project_root / "CLAUDE.md"

        if src_dir.exists():
            self._observer.schedule(self._handler, str(src_dir), recursive=True)
        if adr_dir.exists():
            self._observer.schedule(self._handler, str(adr_dir), recursive=True)
        if claude_md.exists():
            self._observer.schedule(self._handler, str(claude_md.parent), recursive=False)

    def start(self) -> None:
        """Start watching in a background thread."""
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        """Stop watching."""
        self._observer.stop()
        self._observer.join(timeout=2.0)

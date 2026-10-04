"""Hexagonal purity tests -- verify no route file imports from adapters/.

These tests ensure that all API routes use protocol types from ports/
and never directly import concrete adapter implementations.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

# Route modules to check
ROUTE_DIR = Path(__file__).resolve().parents[2] / "src" / "context_graph" / "api" / "routes"

ROUTE_FILES = [
    p for p in ROUTE_DIR.glob("*.py") if p.name != "__init__.py" and not p.name.startswith("_")
]


def _get_imports(filepath: Path) -> list[str]:
    """Extract all import module paths from a Python file's AST."""
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


@pytest.mark.parametrize(
    "route_file",
    ROUTE_FILES,
    ids=[p.stem for p in ROUTE_FILES],
)
class TestNoAdapterImports:
    """Route files must not import from context_graph.adapters."""

    def test_no_adapter_import(self, route_file: Path) -> None:
        """Verify no import from context_graph.adapters in route file."""
        imports = _get_imports(route_file)
        adapter_imports = [i for i in imports if "context_graph.adapters" in i]
        assert adapter_imports == [], f"{route_file.name} imports from adapters/: {adapter_imports}"


@pytest.mark.parametrize(
    "route_file",
    ROUTE_FILES,
    ids=[p.stem for p in ROUTE_FILES],
)
class TestNoInternalAccess:
    """Route files must not access _driver, _client, or _database attributes."""

    def test_no_private_attribute_access(self, route_file: Path) -> None:
        """Verify no ._driver, ._client, or ._database access in route source."""
        source = route_file.read_text()
        forbidden_patterns = ["._driver", "._client", "._database"]
        violations = [p for p in forbidden_patterns if p in source]
        assert violations == [], (
            f"{route_file.name} accesses private adapter internals: {violations}"
        )


class TestDependencyModuleUsesProtocols:
    """dependencies.py should return protocol types, not concrete adapters."""

    def test_dependencies_no_adapter_imports(self) -> None:
        deps_file = ROUTE_DIR.parent / "dependencies.py"
        imports = _get_imports(deps_file)
        adapter_imports = [i for i in imports if "context_graph.adapters" in i]
        assert adapter_imports == [], f"dependencies.py imports from adapters/: {adapter_imports}"


class TestProtocolModulesExist:
    """Verify all required port protocol modules exist and are importable."""

    @pytest.mark.parametrize(
        "module_name",
        [
            "context_graph.ports.event_store",
            "context_graph.ports.graph_store",
            "context_graph.ports.health",
            "context_graph.ports.maintenance",
            "context_graph.ports.retention",
            "context_graph.ports.user_store",
        ],
    )
    def test_protocol_module_importable(self, module_name: str) -> None:
        mod = importlib.import_module(module_name)
        assert mod is not None


class TestProtocolClassesExist:
    """Verify that each protocol module exports the expected protocol class."""

    def test_health_checkable(self) -> None:
        from context_graph.ports.health import HealthCheckable

        assert hasattr(HealthCheckable, "health_ping")

    def test_event_store_admin(self) -> None:
        from context_graph.ports.event_store import EventStoreAdmin

        assert hasattr(EventStoreAdmin, "health_ping")
        assert hasattr(EventStoreAdmin, "stream_length")

    def test_graph_maintenance(self) -> None:
        from context_graph.ports.maintenance import GraphMaintenance

        assert hasattr(GraphMaintenance, "get_session_event_counts")
        assert hasattr(GraphMaintenance, "get_graph_stats")
        assert hasattr(GraphMaintenance, "run_session_query")

    def test_user_store(self) -> None:
        from context_graph.ports.user_store import UserStore

        assert hasattr(UserStore, "get_user_profile")
        assert hasattr(UserStore, "delete_user_data")
        assert hasattr(UserStore, "export_user_data")


class TestRetentionPortExists:
    """Verify RetentionManager port protocol exists."""

    def test_retention_manager_importable(self) -> None:
        from context_graph.ports.retention import RetentionManager

        assert hasattr(RetentionManager, "trim_stream")
        assert hasattr(RetentionManager, "delete_expired_events")
        assert hasattr(RetentionManager, "cleanup_dedup_set")
        assert hasattr(RetentionManager, "cleanup_session_streams")


# =========================================================================
# ADR-0019 §8: storage backend import ban outside adapters/
# =========================================================================

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "src" / "context_graph"

# Backend client libraries. Only adapters/ may import these.
BANNED_BACKEND_LIBRARIES = ("redis", "neo4j", "google.cloud")

# Storage adapters. Outside adapters/, stores are opened through
# context_graph.adapters.registry and used through ports/.
BANNED_STORAGE_ADAPTERS = (
    "context_graph.adapters.redis",
    "context_graph.adapters.neo4j",
    "context_graph.adapters.fs",
    "context_graph.adapters.gcs",
)

NON_ADAPTER_FILES = sorted(
    p
    for p in PACKAGE_DIR.rglob("*.py")
    if "adapters" not in p.relative_to(PACKAGE_DIR).parts and "__pycache__" not in p.parts
)


def _is_banned(module: str, banned: tuple[str, ...]) -> bool:
    return any(module == name or module.startswith(f"{name}.") for name in banned)


@pytest.mark.parametrize(
    "module_file",
    NON_ADAPTER_FILES,
    ids=[str(p.relative_to(PACKAGE_DIR)) for p in NON_ADAPTER_FILES],
)
class TestStorageBackendImportBan:
    """No module outside adapters/ imports a storage backend (ADR-0019 §8)."""

    def test_no_backend_library_import(self, module_file: Path) -> None:
        imports = _get_imports(module_file)
        violations = [i for i in imports if _is_banned(i, BANNED_BACKEND_LIBRARIES)]
        assert violations == [], f"{module_file.name} imports backend libraries: {violations}"

    def test_no_storage_adapter_import(self, module_file: Path) -> None:
        imports = _get_imports(module_file)
        violations = [i for i in imports if _is_banned(i, BANNED_STORAGE_ADAPTERS)]
        assert violations == [], (
            f"{module_file.name} imports storage adapters by name "
            f"(use context_graph.adapters.registry): {violations}"
        )


class TestStoragePortsExist:
    """ADR-0019 step 1 ports are importable and declare their operations."""

    def test_subscription_port(self) -> None:
        from context_graph.ports.subscription import Subscription

        for name in ("ensure_group", "claim_orphaned", "read_pending", "read_new", "ack"):
            assert hasattr(Subscription, name)
        assert hasattr(Subscription, "dead_letter")

    def test_event_log_port(self) -> None:
        from context_graph.ports.event_log import EventLog

        for name in ("get_documents", "read_session_ids", "trim", "expire", "housekeep"):
            assert hasattr(EventLog, name)

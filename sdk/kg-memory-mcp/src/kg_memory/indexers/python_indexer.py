"""Tree-sitter based Python source indexer.

Parses Python files using tree-sitter-python, extracts structural
information (modules, classes, functions, imports, calls), and populates
the in-memory KnowledgeGraph with nodes and edges.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterator

import tree_sitter
import tree_sitter_python

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tree-sitter setup
# ---------------------------------------------------------------------------

_PYTHON_LANGUAGE = tree_sitter.Language(tree_sitter_python.language())


def _make_parser() -> tree_sitter.Parser:
    parser = tree_sitter.Parser(_PYTHON_LANGUAGE)
    return parser


_parser = _make_parser()

# ---------------------------------------------------------------------------
# CST helpers
# ---------------------------------------------------------------------------


def _walk(node: tree_sitter.Node) -> Iterator[tree_sitter.Node]:
    """Depth-first walk of a tree-sitter node tree."""
    yield node
    for child in node.children:
        yield from _walk(child)


def _get_docstring(body_node: tree_sitter.Node | None) -> str | None:
    """Extract the docstring from the first expression of a body block."""
    if body_node is None:
        return None
    for child in body_node.children:
        if child.type == "expression_statement":
            for sub in child.children:
                if sub.type == "string":
                    raw = sub.text.decode()
                    # Strip triple quotes
                    for quote in ('"""', "'''", '"', "'"):
                        if raw.startswith(quote) and raw.endswith(quote):
                            return raw[len(quote) : -len(quote)].strip()
                    return raw
            break
        # Skip pass, comments, newlines at the top of body
        if child.type not in ("comment", "pass_statement", "newline", "\n"):
            break
    return None


def _get_decorators(node: tree_sitter.Node) -> list[str]:
    """Extract decorator names from a decorated_definition or class/func node."""
    decorators: list[str] = []
    parent = node.parent
    if parent and parent.type == "decorated_definition":
        for child in parent.children:
            if child.type == "decorator":
                # The decorator text after '@'
                text = child.text.decode().lstrip("@").strip()
                decorators.append(text)
    return decorators


def _get_function_params(params_node: tree_sitter.Node | None) -> list[str]:
    """Extract parameter names from a parameters node."""
    if params_node is None:
        return []
    names: list[str] = []
    for child in params_node.children:
        if child.type == "identifier":
            names.append(child.text.decode())
        elif child.type in (
            "default_parameter",
            "typed_parameter",
            "typed_default_parameter",
        ):
            name_node = child.child_by_field_name("name")
            if name_node:
                names.append(name_node.text.decode())
        elif child.type in ("list_splat_pattern", "dictionary_splat_pattern"):
            for sub in child.children:
                if sub.type == "identifier":
                    names.append(sub.text.decode())
    return names


def _get_return_type(node: tree_sitter.Node) -> str | None:
    """Extract the return type annotation text from a function_definition."""
    ret = node.child_by_field_name("return_type")
    if ret:
        text = ret.text.decode()
        # tree-sitter includes the '-> ' prefix in some versions
        if text.startswith("->"):
            text = text[2:].strip()
        return text
    return None


def _get_base_classes(node: tree_sitter.Node) -> list[str]:
    """Extract base class names from a class_definition's superclasses."""
    superclasses = node.child_by_field_name("superclasses")
    if superclasses is None:
        # Also check argument_list which some tree-sitter versions use
        for child in node.children:
            if child.type == "argument_list":
                superclasses = child
                break
    if superclasses is None:
        return []
    bases: list[str] = []
    for child in superclasses.children:
        if child.type in ("identifier", "attribute"):
            bases.append(child.text.decode())
    return bases


# ---------------------------------------------------------------------------
# Path / module name helpers
# ---------------------------------------------------------------------------


def _relative_path(file_path: Path, project_root: Path) -> str:
    """Compute the relative path string from project_root."""
    try:
        return str(file_path.relative_to(project_root))
    except ValueError:
        return str(file_path)


def _dotted_module(relative_path_str: str) -> str:
    """Convert a relative file path to a dotted module name.

    e.g. 'src/context_graph/domain/models.py' -> 'src.context_graph.domain.models'
    """
    path = Path(relative_path_str)
    parts = list(path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
        if parts[-1] == "__init__":
            parts = parts[:-1]
    return ".".join(parts)


def _resolve_import_to_path(module_name: str, path_index: dict[str, str]) -> str | None:
    """Try to resolve a dotted import name to a node id via path_index.

    Converts 'context_graph.domain.models' -> tries paths like
    'src/context_graph/domain/models.py', 'context_graph/domain/models.py', etc.
    """
    parts = module_name.split(".")
    # Try the module as a file
    candidates = [
        "/".join(parts) + ".py",
        "/".join(parts) + "/__init__.py",
    ]
    # Also try with 'src/' prefix
    candidates += [
        "src/" + "/".join(parts) + ".py",
        "src/" + "/".join(parts) + "/__init__.py",
    ]

    for candidate in candidates:
        if candidate in path_index:
            return path_index[candidate]

    # Try partial matches — walk up the parts
    for i in range(len(parts), 0, -1):
        sub = "/".join(parts[:i])
        sub_file = sub + ".py"
        sub_init = sub + "/__init__.py"
        src_file = "src/" + sub_file
        src_init = "src/" + sub_init
        for p in (sub_file, sub_init, src_file, src_init):
            if p in path_index:
                return path_index[p]

    return None


# ---------------------------------------------------------------------------
# Extraction from a single file
# ---------------------------------------------------------------------------


def _extract_file(
    graph: KnowledgeGraph,
    file_path: Path,
    project_root: Path,
    source_bytes: bytes,
    tree: tree_sitter.Tree,
) -> None:
    """Extract nodes and edges from a parsed Python file into the graph."""
    rel_path = _relative_path(file_path, project_root)
    dotted = _dotted_module(rel_path)
    file_node_id = f"file:{rel_path}"
    line_count = source_bytes.count(b"\n") + 1

    # --- File node ---
    graph.add_node(
        Node(
            id=file_node_id,
            node_type=NodeType.FILE,
            name=file_path.name,
            properties={
                "path": rel_path,
                "language": "python",
                "size_lines": line_count,
            },
        )
    )

    root = tree.root_node

    # Track current class context for METHOD_OF edges
    class_stack: list[tuple[str, tree_sitter.Node]] = []

    # Collect call targets per function for CALLS edges
    function_calls: dict[str, list[str]] = {}
    current_function_id: str | None = None

    # --- Walk the tree ---
    for ts_node in _walk(root):
        # Skip nodes inside a class/function body if we already processed them
        # We handle classes and functions explicitly below

        if ts_node.type == "class_definition":
            _process_class(
                graph,
                ts_node,
                file_node_id,
                rel_path,
                dotted,
                class_stack,
            )

        elif ts_node.type == "function_definition":
            func_id = _process_function(
                graph,
                ts_node,
                file_node_id,
                rel_path,
                dotted,
                class_stack,
            )
            if func_id:
                current_function_id = func_id
                function_calls.setdefault(func_id, [])

        elif ts_node.type in ("import_statement", "import_from_statement"):
            _process_import(graph, ts_node, file_node_id, dotted)

        elif ts_node.type == "call" and current_function_id:
            # Best-effort call resolution
            call_name = _extract_call_name(ts_node)
            if call_name:
                function_calls.setdefault(current_function_id, []).append(call_name)

    # --- Resolve CALLS edges ---
    _resolve_calls(graph, function_calls, dotted)


def _process_class(
    graph: KnowledgeGraph,
    node: tree_sitter.Node,
    file_node_id: str,
    rel_path: str,
    dotted: str,
    class_stack: list[tuple[str, tree_sitter.Node]],
) -> str | None:
    """Extract a class node and its edges."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None

    class_name = name_node.text.decode()
    class_id = f"class:{dotted}.{class_name}"
    line = node.start_point[0] + 1
    bases = _get_base_classes(node)
    decorators = _get_decorators(node)
    body = node.child_by_field_name("body")
    docstring = _get_docstring(body)

    props: dict[str, Any] = {
        "path": rel_path,
        "line": line,
        "bases": bases,
        "decorators": decorators,
        "source_file": rel_path,
    }
    if docstring:
        props["docstring"] = docstring

    graph.add_node(
        Node(
            id=class_id,
            node_type=NodeType.CLASS,
            name=class_name,
            properties=props,
        )
    )

    # File CONTAINS class
    graph.add_edge(
        Edge(
            source=file_node_id,
            target=class_id,
            edge_type=EdgeType.CONTAINS,
        )
    )

    # INHERITS edges (best effort — resolve by name)
    for base in bases:
        base_id = f"class:{dotted}.{base}"
        # Check if target exists; if not, try graph name lookup
        if graph.get_node(base_id) is None:
            matches = graph.get_nodes_by_name(base)
            if matches:
                base_id = matches[0].id
            else:
                # Create a placeholder that may be resolved later
                continue
        graph.add_edge(
            Edge(
                source=class_id,
                target=base_id,
                edge_type=EdgeType.INHERITS,
            )
        )

    # Push onto class stack
    class_stack.append((class_id, node))

    return class_id


def _process_function(
    graph: KnowledgeGraph,
    node: tree_sitter.Node,
    file_node_id: str,
    rel_path: str,
    dotted: str,
    class_stack: list[tuple[str, tree_sitter.Node]],
) -> str | None:
    """Extract a function/method node and its edges."""
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return None

    func_name = name_node.text.decode()
    line = node.start_point[0] + 1
    params_node = node.child_by_field_name("parameters")
    params = _get_function_params(params_node)
    return_type = _get_return_type(node)
    decorators = _get_decorators(node)
    body = node.child_by_field_name("body")
    docstring = _get_docstring(body)

    # Determine if this is a method (inside a class body)
    enclosing_class_id = _find_enclosing_class(node, class_stack)
    is_method = enclosing_class_id is not None

    if is_method and enclosing_class_id:
        # Extract class name from class_id "class:module.ClassName"
        class_suffix = enclosing_class_id.split(":")[-1].split(".")[-1]
        func_id = f"func:{dotted}.{class_suffix}.{func_name}"
    else:
        func_id = f"func:{dotted}.{func_name}"

    props: dict[str, Any] = {
        "path": rel_path,
        "line": line,
        "params": params,
        "decorators": decorators,
        "is_method": is_method,
        "source_file": rel_path,
    }
    if return_type:
        props["returns"] = return_type
    if docstring:
        props["docstring"] = docstring

    graph.add_node(
        Node(
            id=func_id,
            node_type=NodeType.FUNCTION,
            name=func_name,
            properties=props,
        )
    )

    if is_method and enclosing_class_id:
        # METHOD_OF edge: function -> class
        graph.add_edge(
            Edge(
                source=func_id,
                target=enclosing_class_id,
                edge_type=EdgeType.METHOD_OF,
            )
        )
        # Class CONTAINS function
        graph.add_edge(
            Edge(
                source=enclosing_class_id,
                target=func_id,
                edge_type=EdgeType.CONTAINS,
            )
        )
    else:
        # File CONTAINS function
        graph.add_edge(
            Edge(
                source=file_node_id,
                target=func_id,
                edge_type=EdgeType.CONTAINS,
            )
        )

    return func_id


def _find_enclosing_class(
    node: tree_sitter.Node,
    class_stack: list[tuple[str, tree_sitter.Node]],
) -> str | None:
    """Walk up the tree-sitter parent chain to find an enclosing class."""
    current = node.parent
    while current is not None:
        if current.type == "class_definition":
            # Match against our class stack
            for class_id, class_node in reversed(class_stack):
                if class_node is current:
                    return class_id
            # Fallback: return None if we can't match (shouldn't happen)
            return None
        current = current.parent
    return None


def _process_import(
    graph: KnowledgeGraph,
    node: tree_sitter.Node,
    file_node_id: str,
    dotted: str,
) -> None:
    """Extract import edges from import statements."""
    if node.type == "import_statement":
        # import foo.bar
        for child in node.children:
            if child.type == "dotted_name":
                module_name = child.text.decode()
                _add_import_edge(graph, file_node_id, module_name)
            elif child.type == "aliased_import":
                name_node = child.child_by_field_name("name")
                if name_node:
                    module_name = name_node.text.decode()
                    _add_import_edge(graph, file_node_id, module_name)

    elif node.type == "import_from_statement":
        # from foo.bar import baz
        module_node = node.child_by_field_name("module_name")
        if module_node:
            module_name = module_node.text.decode()
            _add_import_edge(graph, file_node_id, module_name)


def _add_import_edge(
    graph: KnowledgeGraph,
    file_node_id: str,
    module_name: str,
) -> None:
    """Resolve an import module name and add an IMPORTS edge if found."""
    target_id = _resolve_import_to_path(module_name, graph.path_index)
    if target_id:
        graph.add_edge(
            Edge(
                source=file_node_id,
                target=target_id,
                edge_type=EdgeType.IMPORTS,
            )
        )


def _extract_call_name(node: tree_sitter.Node) -> str | None:
    """Extract the function name from a call node.

    Handles simple calls like `foo()` and attribute calls like `self.foo()`.
    """
    func = node.child_by_field_name("function")
    if func is None:
        return None
    if func.type == "identifier":
        return func.text.decode()
    if func.type == "attribute":
        attr = func.child_by_field_name("attribute")
        if attr:
            return attr.text.decode()
    return None


def _resolve_calls(
    graph: KnowledgeGraph,
    function_calls: dict[str, list[str]],
    dotted: str,
) -> None:
    """Resolve call names to function node ids and add CALLS edges."""
    for caller_id, call_names in function_calls.items():
        seen: set[str] = set()
        for call_name in call_names:
            if call_name in seen:
                continue
            seen.add(call_name)

            # Try to find a matching function node by name
            matches = graph.get_nodes_by_name(call_name)
            function_matches = [
                m for m in matches if m.node_type == NodeType.FUNCTION and m.id != caller_id
            ]
            if function_matches:
                # Prefer same-module match
                target = function_matches[0]
                for m in function_matches:
                    if m.id.startswith(f"func:{dotted}."):
                        target = m
                        break
                graph.add_edge(
                    Edge(
                        source=caller_id,
                        target=target.id,
                        edge_type=EdgeType.CALLS,
                    )
                )


# ---------------------------------------------------------------------------
# Module (package) discovery
# ---------------------------------------------------------------------------


def _discover_modules(
    graph: KnowledgeGraph,
    source_dir: Path,
    project_root: Path,
) -> None:
    """Create MODULE nodes for directories containing __init__.py."""
    for init_file in sorted(source_dir.rglob("__init__.py")):
        pkg_dir = init_file.parent
        rel_dir = _relative_path(pkg_dir, project_root)
        dotted = _dotted_module(rel_dir + "/__init__.py")
        module_id = f"module:{dotted}"

        # Read docstring from __init__.py if possible
        docstring = None
        try:
            init_bytes = init_file.read_bytes()
            init_tree = _parser.parse(init_bytes)
            docstring = _get_docstring(init_tree.root_node)
        except Exception:
            pass

        props: dict[str, Any] = {
            "path": rel_dir,
            "is_package": True,
        }
        if docstring:
            props["docstring"] = docstring

        graph.add_node(
            Node(
                id=module_id,
                node_type=NodeType.MODULE,
                name=dotted.split(".")[-1] if "." in dotted else dotted,
                properties=props,
            )
        )

        # Module CONTAINS its files
        for py_file in sorted(pkg_dir.glob("*.py")):
            file_rel = _relative_path(py_file, project_root)
            file_node_id = f"file:{file_rel}"
            if graph.get_node(file_node_id):
                graph.add_edge(
                    Edge(
                        source=module_id,
                        target=file_node_id,
                        edge_type=EdgeType.CONTAINS,
                    )
                )


# ---------------------------------------------------------------------------
# Post-processing: deferred INHERITS resolution
# ---------------------------------------------------------------------------


def _resolve_deferred_inherits(graph: KnowledgeGraph) -> None:
    """Second pass to resolve INHERITS edges that couldn't be resolved initially."""
    class_nodes = graph.get_nodes_by_type(NodeType.CLASS)
    for cls_node in class_nodes:
        bases = cls_node.properties.get("bases", [])
        for base_name in bases:
            # Check if edge already exists
            existing = graph.get_outgoing(cls_node.id, [EdgeType.INHERITS])
            already_linked = {e.target for e in existing}

            # Try to find the base class
            matches = graph.get_nodes_by_name(base_name)
            class_matches = [m for m in matches if m.node_type == NodeType.CLASS]
            for target in class_matches:
                if target.id not in already_linked and target.id != cls_node.id:
                    graph.add_edge(
                        Edge(
                            source=cls_node.id,
                            target=target.id,
                            edge_type=EdgeType.INHERITS,
                        )
                    )
                    break


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def index_python_files(
    graph: KnowledgeGraph,
    source_dir: Path,
    project_root: Path | None = None,
) -> dict[Path, Any]:
    """Index all Python files under source_dir into the graph.

    Returns a dict mapping file paths to their tree-sitter Tree objects
    (for incremental re-parsing by the file watcher).
    """
    if project_root is None:
        project_root = source_dir

    trees: dict[Path, Any] = {}

    # First pass: parse all files and create file/class/function nodes
    py_files = sorted(source_dir.rglob("*.py"))
    for py_file in py_files:
        try:
            tree = index_single_python_file(graph, py_file, project_root)
            trees[py_file] = tree
        except Exception:
            logger.exception("Failed to index %s", py_file)

    # Create module (package) nodes
    _discover_modules(graph, source_dir, project_root)

    # Second pass: resolve deferred INHERITS edges
    _resolve_deferred_inherits(graph)

    logger.info(
        "Indexed %d Python files: %s",
        len(trees),
        graph.stats(),
    )

    return trees


def index_single_python_file(
    graph: KnowledgeGraph,
    file_path: Path,
    project_root: Path,
    old_tree: Any | None = None,
) -> Any:
    """Index a single Python file. Returns the tree-sitter Tree.

    If old_tree is provided, uses incremental parsing.
    """
    source_bytes = file_path.read_bytes()

    if old_tree is not None:
        tree = _parser.parse(source_bytes, old_tree)
    else:
        tree = _parser.parse(source_bytes)

    # Remove stale nodes from this file before re-indexing
    rel_path = _relative_path(file_path, project_root)
    graph.remove_file_nodes(rel_path)

    _extract_file(graph, file_path, project_root, source_bytes, tree)

    return tree

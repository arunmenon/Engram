"""Tests for Personalized PageRank approximation (L5)."""

from __future__ import annotations

import math

from context_graph.domain.ppr import approximate_ppr


class TestApproximatePPREmpty:
    """Edge cases: empty or degenerate inputs."""

    def test_empty_graph(self) -> None:
        result = approximate_ppr({}, ["a"])
        assert result == {}

    def test_empty_seeds(self) -> None:
        result = approximate_ppr({"a": [("b", 1.0)]}, [])
        assert result == {}

    def test_invalid_seeds_ignored(self) -> None:
        """Seeds not in the adjacency graph are ignored."""
        result = approximate_ppr({"a": [("b", 1.0)]}, ["x", "y"])
        assert result == {}


class TestApproximatePPRSingleNode:
    """Single-node graph."""

    def test_single_node_self_loop(self) -> None:
        result = approximate_ppr({"a": [("a", 1.0)]}, ["a"])
        assert len(result) == 1
        assert math.isclose(result["a"], 1.0, rel_tol=1e-6)

    def test_single_node_no_edges(self) -> None:
        result = approximate_ppr({"a": []}, ["a"])
        # Dangling node with only itself as seed
        assert len(result) == 1
        assert math.isclose(result["a"], 1.0, rel_tol=1e-6)


class TestApproximatePPRTwoNodes:
    """Two-node graph with a single directed edge."""

    def test_two_nodes_one_edge(self) -> None:
        adj = {"a": [("b", 1.0)], "b": []}
        result = approximate_ppr(adj, ["a"])
        assert set(result.keys()) == {"a", "b"}
        # Seed "a" should still have some mass due to teleportation
        assert result["a"] > 0
        assert result["b"] > 0
        assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-6)


class TestApproximatePPRStarGraph:
    """Star graph: center connected to N leaves."""

    def test_star_graph_center_highest(self) -> None:
        """Center node seeded => center keeps highest PPR."""
        adj: dict[str, list[tuple[str, float]]] = {
            "center": [("l1", 1.0), ("l2", 1.0), ("l3", 1.0), ("l4", 1.0)],
            "l1": [],
            "l2": [],
            "l3": [],
            "l4": [],
        }
        result = approximate_ppr(adj, ["center"])
        # Center receives teleportation + dangling redistribution
        assert result["center"] > result["l1"]
        assert result["center"] > result["l2"]


class TestApproximatePPRChainGraph:
    """Chain graph: a -> b -> c -> d."""

    def test_chain_graph_seed_has_score(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [("c", 1.0)],
            "c": [("d", 1.0)],
            "d": [],
        }
        result = approximate_ppr(adj, ["a"])
        # Seed "a" gets teleportation mass + dangling redistribution from d
        assert result["a"] > 0
        # All nodes should have some score since mass flows through the chain
        assert all(v > 0 for v in result.values())
        assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-6)


class TestApproximatePPRCycleGraph:
    """Cycle graph: a -> b -> c -> a."""

    def test_cycle_graph_equal_scores(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [("c", 1.0)],
            "c": [("a", 1.0)],
        }
        # All nodes as seeds -> should converge to roughly equal
        result = approximate_ppr(adj, ["a", "b", "c"], iterations=20)
        scores = list(result.values())
        assert all(math.isclose(s, 1 / 3, abs_tol=0.01) for s in scores)


class TestApproximatePPRWeightedEdges:
    """Weighted edges influence score distribution."""

    def test_weighted_edges(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 9.0), ("c", 1.0)],
            "b": [],
            "c": [],
        }
        result = approximate_ppr(adj, ["a"])
        # Node b should get ~9x the propagated mass vs node c
        assert result["b"] > result["c"]


class TestApproximatePPRDamping:
    """Damping factor controls teleportation vs propagation."""

    def test_damping_zero_stays_on_seeds(self) -> None:
        """damping=0 => all mass stays on seeds via teleportation."""
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [("c", 1.0)],
            "c": [],
        }
        result = approximate_ppr(adj, ["a"], damping=0.0)
        assert math.isclose(result["a"], 1.0, rel_tol=1e-6)
        assert math.isclose(result["b"], 0.0, abs_tol=1e-6)
        assert math.isclose(result["c"], 0.0, abs_tol=1e-6)

    def test_damping_one_follows_edges(self) -> None:
        """damping=1.0 => no teleportation, pure propagation."""
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [("a", 1.0)],
        }
        # With damping=1.0, mass oscillates fully between a and b each iteration.
        # Odd iteration count: all mass on b. Even: all mass on a.
        result_odd = approximate_ppr(adj, ["a"], damping=1.0, iterations=1)
        assert math.isclose(result_odd["b"], 1.0, rel_tol=1e-6)

        result_even = approximate_ppr(adj, ["a"], damping=1.0, iterations=2)
        assert math.isclose(result_even["a"], 1.0, rel_tol=1e-6)

        # Sum always 1.0
        assert math.isclose(sum(result_odd.values()), 1.0, rel_tol=1e-6)
        assert math.isclose(sum(result_even.values()), 1.0, rel_tol=1e-6)


class TestApproximatePPRMultipleSeeds:
    """Multiple seed nodes."""

    def test_multiple_seeds(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("c", 1.0)],
            "b": [("c", 1.0)],
            "c": [],
        }
        result = approximate_ppr(adj, ["a", "b"])
        # Both seeds should have similar scores
        assert math.isclose(result["a"], result["b"], rel_tol=0.01)
        assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-6)


class TestApproximatePPRNormalization:
    """Scores should always sum to 1.0."""

    def test_scores_sum_to_one(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 2.0), ("c", 3.0)],
            "b": [("d", 1.0)],
            "c": [("d", 1.0), ("a", 0.5)],
            "d": [],
        }
        result = approximate_ppr(adj, ["a"])
        assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-6)


class TestApproximatePPRDisconnected:
    """Disconnected components."""

    def test_disconnected_components(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [],
            "c": [("d", 1.0)],
            "d": [],
        }
        result = approximate_ppr(adj, ["a"])
        # Seed a is disconnected from c,d — they get 0 propagation
        # but c and d are dangling so they redistribute to seed
        assert result["a"] > result["c"]
        assert result["a"] > result["d"]


class TestApproximatePPRConvergence:
    """More iterations should lead to convergence."""

    def test_convergence_with_iterations(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0)],
            "b": [("c", 1.0)],
            "c": [("a", 1.0)],
        }
        result_5 = approximate_ppr(adj, ["a"], iterations=5)
        result_50 = approximate_ppr(adj, ["a"], iterations=50)
        # With more iterations, scores should be closer together (more converged)
        diff_5 = max(result_5.values()) - min(result_5.values())
        diff_50 = max(result_50.values()) - min(result_50.values())
        # 50 iterations should converge more than 5
        assert diff_50 <= diff_5


class TestApproximatePPRDanglingNodes:
    """Dangling nodes (no outgoing edges) redistribute to seeds."""

    def test_dangling_nodes(self) -> None:
        adj: dict[str, list[tuple[str, float]]] = {
            "a": [("b", 1.0), ("c", 1.0)],
            "b": [],  # dangling
            "c": [],  # dangling
        }
        result = approximate_ppr(adj, ["a"])
        # Seed receives teleportation + dangling redistribution
        assert result["a"] > 0
        assert result["b"] > 0
        assert result["c"] > 0
        assert math.isclose(sum(result.values()), 1.0, rel_tol=1e-6)

"""Unit tests for transitive closure / entity clustering.

Tests the Union-Find based ``compute_transitive_closure`` function
in ``context_graph.domain.entity_resolution``.
"""

from __future__ import annotations

from context_graph.domain.entity_resolution import compute_transitive_closure


class TestEmptyAndTrivial:
    def test_empty_edges(self):
        result = compute_transitive_closure([])
        assert result == {}

    def test_single_edge_pair(self):
        result = compute_transitive_closure([("a", "b")])
        # Both should be in one cluster
        assert len(result) == 1
        canonical = next(iter(result))
        assert set(result[canonical]) == {"a", "b"}

    def test_self_edge_ignored(self):
        result = compute_transitive_closure([("a", "a")])
        # Self-edge creates a singleton cluster
        assert len(result) == 1
        assert "a" in result
        assert result["a"] == ["a"]


class TestTransitivity:
    def test_transitive_three_nodes(self):
        """A-B, B-C should yield a single cluster {A, B, C}."""
        result = compute_transitive_closure([("a", "b"), ("b", "c")])
        assert len(result) == 1
        members = set(next(iter(result.values())))
        assert members == {"a", "b", "c"}

    def test_transitive_chain(self):
        """A-B, B-C, C-D should yield one cluster of 4."""
        result = compute_transitive_closure([("a", "b"), ("b", "c"), ("c", "d")])
        assert len(result) == 1
        members = set(next(iter(result.values())))
        assert members == {"a", "b", "c", "d"}

    def test_cycle_handling(self):
        """A-B, B-C, C-A should yield one cluster (no infinite loop)."""
        result = compute_transitive_closure([("a", "b"), ("b", "c"), ("c", "a")])
        assert len(result) == 1
        members = set(next(iter(result.values())))
        assert members == {"a", "b", "c"}


class TestMultipleClusters:
    def test_multiple_clusters(self):
        edges = [("a", "b"), ("c", "d")]
        result = compute_transitive_closure(edges)
        assert len(result) == 2
        all_members = set()
        for members in result.values():
            all_members.update(members)
        assert all_members == {"a", "b", "c", "d"}

    def test_all_members_accounted(self):
        """Every node from the edges list must appear in exactly one cluster."""
        edges = [("x", "y"), ("y", "z"), ("p", "q")]
        result = compute_transitive_closure(edges)
        all_members = []
        for members in result.values():
            all_members.extend(members)
        assert sorted(all_members) == ["p", "q", "x", "y", "z"]
        # No duplicates
        assert len(all_members) == len(set(all_members))


class TestCanonicalSelection:
    def test_canonical_highest_mention_count(self):
        edges = [("a", "b"), ("b", "c")]
        counts = {"a": 1, "b": 5, "c": 2}
        result = compute_transitive_closure(edges, mention_counts=counts)
        assert len(result) == 1
        # "b" has the highest mention count
        assert "b" in result
        assert set(result["b"]) == {"a", "b", "c"}

    def test_canonical_alphabetical_tiebreak(self):
        edges = [("beta", "alpha"), ("alpha", "gamma")]
        counts = {"alpha": 3, "beta": 3, "gamma": 3}
        result = compute_transitive_closure(edges, mention_counts=counts)
        assert len(result) == 1
        # All have same count, "alpha" wins alphabetically
        assert "alpha" in result

    def test_no_mention_counts_fallback(self):
        """Without mention_counts, canonical is alphabetically first."""
        edges = [("zebra", "apple")]
        result = compute_transitive_closure(edges)
        assert len(result) == 1
        assert "apple" in result
        assert set(result["apple"]) == {"apple", "zebra"}

    def test_canonical_in_cluster_list(self):
        """The canonical entity must be included in its own cluster members."""
        edges = [("a", "b")]
        counts = {"a": 10, "b": 1}
        result = compute_transitive_closure(edges, mention_counts=counts)
        canonical = next(iter(result))
        assert canonical in result[canonical]


class TestDuplicatesAndLargeInput:
    def test_duplicate_edges(self):
        edges = [("a", "b"), ("a", "b"), ("b", "a")]
        result = compute_transitive_closure(edges)
        assert len(result) == 1
        members = set(next(iter(result.values())))
        assert members == {"a", "b"}

    def test_large_cluster(self):
        """Chain of 50 nodes should produce a single cluster."""
        nodes = [f"entity:{i}" for i in range(50)]
        edges = [(nodes[i], nodes[i + 1]) for i in range(49)]
        result = compute_transitive_closure(edges)
        assert len(result) == 1
        members = set(next(iter(result.values())))
        assert len(members) == 50
        assert all(n in members for n in nodes)

"""
Phase 0 Infrastructure Validation: Neo4j Capabilities
======================================================

Validates every Neo4j capability assumed by ADR-0003, ADR-0005, ADR-0008,
ADR-0009, and ADR-0011 before any application code is written.

Run with:
    source .venv/bin/activate && pytest tests/infra/test_neo4j.py -v

Requires:
    - neo4j:5-community running on bolt://localhost:7687
    - Auth: neo4j / engram-dev-password
"""

from __future__ import annotations

import time
import uuid

import neo4j
import pytest
from neo4j import AsyncGraphDatabase

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "engram-dev-password")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def driver():
    """Create an async Neo4j driver for each test."""
    async_driver = AsyncGraphDatabase.driver(
        NEO4J_URI,
        auth=NEO4J_AUTH,
    )
    # Verify connectivity and print version info
    server_info = await async_driver.get_server_info()
    print(f"\nNeo4j Server: {server_info.agent}")
    print(f"Protocol version: {server_info.protocol_version}")
    yield async_driver
    await async_driver.close()


@pytest.fixture
async def session(driver):
    """Provide an async session that is closed after each test."""
    async with driver.session(database="neo4j") as session:
        yield session


@pytest.fixture(autouse=True)
async def cleanup_test_data(driver):
    """Clean up all test-labelled nodes after each test."""
    yield
    async with driver.session(database="neo4j") as session:
        # Remove all nodes created during tests using test-specific labels
        await session.run(
            "MATCH (n) WHERE any(label IN labels(n) WHERE label STARTS WITH 'Test') "
            "DETACH DELETE n"
        )
        # Also clean up nodes with test-specific event_id prefixes
        await session.run(
            "MATCH (n) WHERE n.event_id STARTS WITH 'test-' "
            "OR n.event_id STARTS WITH 'evt-batch-' "
            "OR n.event_id STARTS WITH 'evt-perf-' "
            "DETACH DELETE n"
        )


# ---------------------------------------------------------------------------
# Capability 1: MERGE with properties (ADR-0009)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_merge_idempotent_node_creation(session):
    """
    ADR-0009: MERGE-based idempotent node creation.
    Running MERGE twice with the same key must produce exactly one node.
    """
    event_id = f"test-merge-{uuid.uuid4().hex[:8]}"

    merge_query = """
    MERGE (e:TestEvent:Event {event_id: $event_id})
    ON CREATE SET
        e.event_type = $event_type,
        e.occurred_at = $occurred_at,
        e.session_id = $session_id,
        e.global_position = $global_position,
        e.created_count = 1
    ON MATCH SET
        e.created_count = coalesce(e.created_count, 0) + 1
    RETURN e.created_count AS count
    """
    params = {
        "event_id": event_id,
        "event_type": "tool.execute",
        "occurred_at": "2026-02-12T10:00:00Z",
        "session_id": "sess-merge-001",
        "global_position": "1770808200000-0",
    }

    # First MERGE -- creates the node
    result_1 = await session.run(merge_query, params)
    record_1 = await result_1.single()
    assert record_1["count"] == 1, "First MERGE should set created_count to 1"

    # Second MERGE -- matches existing, increments counter
    result_2 = await session.run(merge_query, params)
    record_2 = await result_2.single()
    assert record_2["count"] == 2, "Second MERGE should increment created_count to 2"

    # Verify exactly one node exists
    count_result = await session.run(
        "MATCH (e:TestEvent {event_id: $event_id}) RETURN count(e) AS total",
        {"event_id": event_id},
    )
    count_record = await count_result.single()
    assert count_record["total"] == 1, "Only one node should exist after two MERGEs"


# ---------------------------------------------------------------------------
# Capability 2: CREATE CONSTRAINT (uniqueness + NOT NULL) (ADR-0011)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_constraints_from_constraints_cypher(session):
    """
    ADR-0011 Section 7: Verify that all constraints defined in
    docker/neo4j/constraints.cypher can be created and exist in the database.

    NOTE: Neo4j Community Edition only supports UNIQUENESS constraints.
    Property existence (IS NOT NULL) constraints require Enterprise Edition.
    NOT NULL enforcement is handled at the application layer.
    """
    # Create all uniqueness constraints (Community Edition supports these)
    constraint_statements = [
        "CREATE CONSTRAINT event_pk IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE",
        "CREATE CONSTRAINT entity_pk IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE",
        "CREATE CONSTRAINT summary_pk IF NOT EXISTS FOR (s:Summary) REQUIRE s.summary_id IS UNIQUE",
    ]
    for stmt in constraint_statements:
        await session.run(stmt)

    expected_constraints = {
        "event_pk",
        "entity_pk",
        "summary_pk",
    }

    result = await session.run("SHOW CONSTRAINTS")
    records = [record async for record in result]

    existing_constraint_names = {record["name"] for record in records}

    missing = expected_constraints - existing_constraint_names
    assert not missing, (
        f"Missing constraints: {missing}. "
        f"Existing constraints: {existing_constraint_names}"
    )
    print(f"\nAll {len(expected_constraints)} uniqueness constraints created and verified:")
    for name in sorted(expected_constraints):
        print(f"  - {name}")

    # Verify that NOT NULL constraints are NOT available in Community Edition
    try:
        await session.run(
            "CREATE CONSTRAINT test_not_null_check IF NOT EXISTS "
            "FOR (t:TestNotNull) REQUIRE t.name IS NOT NULL"
        )
        # If we get here, we're on Enterprise — clean up
        await session.run("DROP CONSTRAINT test_not_null_check IF EXISTS")
        print("  NOTE: NOT NULL constraints available (Enterprise Edition detected)")
    except neo4j.exceptions.DatabaseError:
        print("  NOT NULL constraints NOT available (Community Edition confirmed)")
        print("  -> NOT NULL enforcement delegated to application layer (Pydantic + projection worker)")


@pytest.mark.infra
async def test_uniqueness_constraint_enforcement(session):
    """
    Verify uniqueness constraints actually prevent duplicate key insertion.
    Uses TestEvent label to avoid polluting real Event data.
    """
    # Ensure constraint exists first
    await session.run(
        "CREATE CONSTRAINT event_pk IF NOT EXISTS FOR (e:Event) REQUIRE e.event_id IS UNIQUE"
    )

    event_id = f"test-unique-{uuid.uuid4().hex[:8]}"

    # Create first node (using Event label to trigger constraint)
    await session.run(
        """
        CREATE (e:TestEvent:Event {
            event_id: $event_id,
            event_type: 'test.constraint',
            occurred_at: '2026-02-12T10:00:00Z',
            session_id: 'sess-constraint-001',
            global_position: '1770808200000-0'
        })
        """,
        {"event_id": event_id},
    )

    # Attempt to CREATE (not MERGE) a second node with same event_id
    with pytest.raises(neo4j.exceptions.ConstraintError):
        result = await session.run(
            """
            CREATE (e:TestEvent:Event {
                event_id: $event_id,
                event_type: 'test.constraint.dup',
                occurred_at: '2026-02-12T10:01:00Z',
                session_id: 'sess-constraint-002',
                global_position: '1770808200000-1'
            })
            """,
            {"event_id": event_id},
        )
        # Force the driver to consume the result and raise the error
        await result.consume()


@pytest.mark.infra
async def test_not_null_constraint_community_limitation(session):
    """
    Verify that NOT NULL (property existence) constraints are NOT available
    in Neo4j Community Edition. This is a known limitation — NOT NULL
    enforcement must be handled at the application layer.
    """
    with pytest.raises(neo4j.exceptions.DatabaseError, match="Enterprise Edition"):
        await session.run(
            "CREATE CONSTRAINT test_existence IF NOT EXISTS "
            "FOR (e:Event) REQUIRE e.event_type IS NOT NULL"
        )
    print("\nConfirmed: NOT NULL constraints require Enterprise Edition")
    print("  -> Application layer (Pydantic + projection worker) handles NOT NULL enforcement")


# ---------------------------------------------------------------------------
# Capability 3: Typed relationships (ADR-0009 — 5 edge types)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_typed_relationships(session):
    """
    ADR-0009: Create all five relationship types defined in the architecture:
    FOLLOWS, CAUSED_BY, SIMILAR_TO, REFERENCES, SUMMARIZES.
    """
    prefix = f"test-rel-{uuid.uuid4().hex[:8]}"
    edge_types = ["FOLLOWS", "CAUSED_BY", "SIMILAR_TO", "REFERENCES", "SUMMARIZES"]

    # Create pairs of nodes and connect them with each relationship type
    for rel_type in edge_types:
        source_id = f"{prefix}-{rel_type}-src"
        target_id = f"{prefix}-{rel_type}-tgt"
        query = f"""
        CREATE (a:TestNode {{node_id: $source_id}})
        CREATE (b:TestNode {{node_id: $target_id}})
        CREATE (a)-[r:{rel_type}]->(b)
        RETURN type(r) AS rel_type
        """
        result = await session.run(query, {"source_id": source_id, "target_id": target_id})
        record = await result.single()
        assert record["rel_type"] == rel_type, f"Expected {rel_type}, got {record['rel_type']}"

    # Verify all relationship types exist
    result = await session.run(
        """
        MATCH (a:TestNode)-[r]->(b:TestNode)
        WHERE a.node_id STARTS WITH $prefix
        RETURN DISTINCT type(r) AS rel_type
        ORDER BY rel_type
        """,
        {"prefix": prefix},
    )
    records = [record async for record in result]
    found_types = {record["rel_type"] for record in records}
    assert found_types == set(edge_types), (
        f"Expected all 5 edge types, found: {found_types}"
    )
    print(f"\nAll 5 relationship types verified: {sorted(found_types)}")


# ---------------------------------------------------------------------------
# Capability 4: Variable-length path traversal (ADR-0009 — lineage)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_variable_length_path_traversal(session):
    """
    ADR-0009: Variable-length path traversal for lineage queries.
    Creates a causal chain A -> B -> C -> D -> E via CAUSED_BY edges,
    then traverses with depth bounds.
    """
    prefix = f"test-lineage-{uuid.uuid4().hex[:8]}"
    chain_ids = [f"{prefix}-{letter}" for letter in "ABCDE"]

    # Create causal chain: A --CAUSED_BY--> B --CAUSED_BY--> C --> D --> E
    for node_id in chain_ids:
        await session.run(
            "CREATE (e:TestLineage {event_id: $event_id})",
            {"event_id": node_id},
        )

    for i in range(len(chain_ids) - 1):
        await session.run(
            """
            MATCH (a:TestLineage {event_id: $source})
            MATCH (b:TestLineage {event_id: $target})
            CREATE (a)-[:CAUSED_BY]->(b)
            """,
            {"source": chain_ids[i], "target": chain_ids[i + 1]},
        )

    # Query full chain from A with depth 1..5
    result = await session.run(
        """
        MATCH path = (a:TestLineage {event_id: $start})-[:CAUSED_BY*1..5]->(b:TestLineage)
        RETURN b.event_id AS reached_node, length(path) AS depth
        ORDER BY depth
        """,
        {"start": chain_ids[0]},
    )
    records = [record async for record in result]

    reached_nodes = [record["reached_node"] for record in records]
    depths = [record["depth"] for record in records]

    # Should reach B (depth 1), C (depth 2), D (depth 3), E (depth 4)
    assert len(records) == 4, f"Expected 4 reachable nodes, got {len(records)}"
    assert reached_nodes == chain_ids[1:], (
        f"Expected chain {chain_ids[1:]}, got {reached_nodes}"
    )
    assert depths == [1, 2, 3, 4], f"Expected depths [1,2,3,4], got {depths}"

    # Verify bounded traversal: depth 1..2 should only reach B and C
    bounded_result = await session.run(
        """
        MATCH path = (a:TestLineage {event_id: $start})-[:CAUSED_BY*1..2]->(b:TestLineage)
        RETURN b.event_id AS reached_node, length(path) AS depth
        ORDER BY depth
        """,
        {"start": chain_ids[0]},
    )
    bounded_records = [record async for record in bounded_result]
    assert len(bounded_records) == 2, (
        f"Bounded query (depth 1..2) should reach 2 nodes, got {len(bounded_records)}"
    )
    print("\nLineage traversal verified: chain of 5 nodes, depth bounds working")


# ---------------------------------------------------------------------------
# Capability 5: UNWIND + MERGE batch pattern (ADR-0005)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_unwind_merge_batch_pattern(session):
    """
    ADR-0005: Batch projection using UNWIND + MERGE.
    Verifies that a batch of events can be atomically merged.
    """
    events = [
        {
            "event_id": f"evt-batch-{i}",
            "event_type": "tool.execute",
            "occurred_at": "2026-02-12T10:30:00Z",
            "session_id": "sess-batch-001",
            "global_position": f"1770808200000-{i}",
        }
        for i in range(20)
    ]

    # Batch UNWIND + MERGE
    batch_query = """
    UNWIND $events AS evt
    MERGE (e:TestBatch:Event {event_id: evt.event_id})
    ON CREATE SET
        e.event_type = evt.event_type,
        e.occurred_at = evt.occurred_at,
        e.session_id = evt.session_id,
        e.global_position = evt.global_position
    RETURN count(e) AS merged_count
    """
    result = await session.run(batch_query, {"events": events})
    record = await result.single()
    assert record["merged_count"] == 20, (
        f"Expected 20 merged nodes, got {record['merged_count']}"
    )

    # Run the same batch again -- should be idempotent
    result_2 = await session.run(batch_query, {"events": events})
    record_2 = await result_2.single()
    assert record_2["merged_count"] == 20, "Idempotent re-run should return same count"

    # Verify exactly 20 nodes exist (not 40)
    count_result = await session.run(
        "MATCH (e:TestBatch) RETURN count(e) AS total"
    )
    count_record = await count_result.single()
    assert count_record["total"] == 20, (
        f"Expected exactly 20 nodes after idempotent batch, got {count_record['total']}"
    )
    print("\nBatch UNWIND+MERGE verified: 20 events, idempotent on re-run")


# ---------------------------------------------------------------------------
# Capability 6: Node property lists (ADR-0009 — keywords, embedding)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_node_property_lists(session):
    """
    ADR-0009: Store LIST<STRING> (keywords) and LIST<FLOAT> (embedding)
    properties on nodes and verify correct retrieval.
    """
    node_id = f"test-lists-{uuid.uuid4().hex[:8]}"
    keywords = ["python", "neo4j", "graph", "traceability"]
    embedding = [0.123, 0.456, 0.789, -0.321, 0.654]

    await session.run(
        """
        CREATE (n:TestListNode {
            node_id: $node_id,
            keywords: $keywords,
            embedding: $embedding
        })
        """,
        {"node_id": node_id, "keywords": keywords, "embedding": embedding},
    )

    result = await session.run(
        """
        MATCH (n:TestListNode {node_id: $node_id})
        RETURN n.keywords AS keywords, n.embedding AS embedding,
               size(n.keywords) AS keyword_count, size(n.embedding) AS embedding_dim
        """,
        {"node_id": node_id},
    )
    record = await result.single()

    assert list(record["keywords"]) == keywords, (
        f"Keywords mismatch: expected {keywords}, got {record['keywords']}"
    )
    assert record["keyword_count"] == len(keywords)

    # Float comparison with tolerance
    retrieved_embedding = list(record["embedding"])
    assert len(retrieved_embedding) == len(embedding)
    for expected_val, actual_val in zip(embedding, retrieved_embedding):
        assert abs(expected_val - actual_val) < 1e-6, (
            f"Embedding value mismatch: expected {expected_val}, got {actual_val}"
        )
    assert record["embedding_dim"] == len(embedding)

    print(f"\nProperty lists verified: {len(keywords)} keywords, {len(embedding)}-dim embedding")


# ---------------------------------------------------------------------------
# Capability 7: Async driver (ADR-0002 — async stack)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_async_driver_connectivity(driver):
    """
    ADR-0002: Verify async Neo4j driver works end-to-end.
    Connects, runs a query, and verifies the result.
    """
    # Verify the driver is actually the async variant
    assert isinstance(driver, neo4j.AsyncDriver), (
        f"Expected AsyncDriver, got {type(driver).__name__}"
    )

    # Run a simple query to verify connectivity
    async with driver.session(database="neo4j") as session:
        result = await session.run("RETURN 1 AS value")
        record = await result.single()
        assert record["value"] == 1

    # Get server info
    server_info = await driver.get_server_info()
    assert server_info.agent is not None, "Server agent string should not be None"
    print(f"\nAsync driver verified: server agent = {server_info.agent}")


# ---------------------------------------------------------------------------
# Capability 8: Degree centrality via Cypher (ADR-0008)
# Community Edition does NOT have GDS, so we compute centrality with Cypher.
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_degree_centrality_via_cypher(session):
    """
    ADR-0008: Centrality-based importance scoring.
    Since Community Edition lacks GDS, we compute in-degree centrality
    using plain Cypher aggregation.

    Test graph (directed edges show REFERENCES):
        A <-- B
        A <-- C
        A <-- D
        B <-- D
        C <-- E
    Expected in-degrees: A=3, B=1, C=1, D=0, E=0
    """
    prefix = f"test-centrality-{uuid.uuid4().hex[:8]}"
    nodes = {letter: f"{prefix}-{letter}" for letter in "ABCDE"}

    # Create nodes
    for letter, node_id in nodes.items():
        await session.run(
            "CREATE (n:TestCentrality {node_id: $node_id, label: $label})",
            {"node_id": node_id, "label": letter},
        )

    # Create directed edges (source REFERENCES target)
    edges = [
        ("B", "A"),  # B references A
        ("C", "A"),  # C references A
        ("D", "A"),  # D references A
        ("D", "B"),  # D references B
        ("E", "C"),  # E references C
    ]
    for source_label, target_label in edges:
        await session.run(
            """
            MATCH (s:TestCentrality {node_id: $source})
            MATCH (t:TestCentrality {node_id: $target})
            CREATE (s)-[:REFERENCES]->(t)
            """,
            {"source": nodes[source_label], "target": nodes[target_label]},
        )

    # Compute in-degree centrality using plain Cypher
    result = await session.run(
        """
        MATCH (n:TestCentrality)
        WHERE n.node_id STARTS WITH $prefix
        OPTIONAL MATCH (n)<-[r:REFERENCES]-()
        RETURN n.label AS label, n.node_id AS node_id, count(r) AS in_degree
        ORDER BY in_degree DESC, label ASC
        """,
        {"prefix": prefix},
    )
    records = [record async for record in result]

    centrality_map = {record["label"]: record["in_degree"] for record in records}

    assert centrality_map["A"] == 3, f"Node A should have in-degree 3, got {centrality_map['A']}"
    assert centrality_map["B"] == 1, f"Node B should have in-degree 1, got {centrality_map['B']}"
    assert centrality_map["C"] == 1, f"Node C should have in-degree 1, got {centrality_map['C']}"
    assert centrality_map["D"] == 0, f"Node D should have in-degree 0, got {centrality_map['D']}"
    assert centrality_map["E"] == 0, f"Node E should have in-degree 0, got {centrality_map['E']}"

    # Verify the most central node
    most_central = records[0]
    assert most_central["label"] == "A", (
        f"Most central node should be A, got {most_central['label']}"
    )
    print(f"\nDegree centrality verified via Cypher: {centrality_map}")


# ---------------------------------------------------------------------------
# Capability 9: Transaction functions (execute_write / execute_read)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_transaction_functions(driver):
    """
    Verify session.execute_write() and session.execute_read() work
    correctly in async mode.
    """
    node_id = f"test-txfn-{uuid.uuid4().hex[:8]}"

    async def create_node(tx):
        result = await tx.run(
            """
            CREATE (n:TestTxNode {node_id: $node_id, value: 42})
            RETURN n.node_id AS node_id, n.value AS value
            """,
            {"node_id": node_id},
        )
        return await result.single()

    async def read_node(tx):
        result = await tx.run(
            """
            MATCH (n:TestTxNode {node_id: $node_id})
            RETURN n.node_id AS node_id, n.value AS value
            """,
            {"node_id": node_id},
        )
        return await result.single()

    async with driver.session(database="neo4j") as session:
        # execute_write -- creates a node
        write_record = await session.execute_write(create_node)
        assert write_record["node_id"] == node_id
        assert write_record["value"] == 42

        # execute_read -- reads it back
        read_record = await session.execute_read(read_node)
        assert read_record["node_id"] == node_id
        assert read_record["value"] == 42

    print("\nTransaction functions verified: execute_write + execute_read")


# ---------------------------------------------------------------------------
# Capability 10: Performance — 1000-node MERGE batch (< 5 seconds)
# ---------------------------------------------------------------------------


@pytest.mark.infra
async def test_performance_1000_node_merge_batch(session):
    """
    Performance baseline: batch MERGE 1000 nodes and verify completion
    within 5 seconds.
    """
    events = [
        {
            "event_id": f"evt-perf-{i:04d}",
            "event_type": "tool.execute",
            "occurred_at": "2026-02-12T11:00:00Z",
            "session_id": "sess-perf-001",
            "global_position": f"1770808200000-{i}",
        }
        for i in range(1000)
    ]

    start_time = time.perf_counter()

    result = await session.run(
        """
        UNWIND $events AS evt
        MERGE (e:TestPerf {event_id: evt.event_id})
        ON CREATE SET
            e.event_type = evt.event_type,
            e.occurred_at = evt.occurred_at,
            e.session_id = evt.session_id,
            e.global_position = evt.global_position
        RETURN count(e) AS merged_count
        """,
        {"events": events},
    )
    record = await result.single()

    elapsed = time.perf_counter() - start_time

    assert record["merged_count"] == 1000, (
        f"Expected 1000 merged nodes, got {record['merged_count']}"
    )
    assert elapsed < 5.0, (
        f"1000-node MERGE took {elapsed:.2f}s, exceeds 5s threshold"
    )

    # Verify node count
    count_result = await session.run(
        "MATCH (e:TestPerf) RETURN count(e) AS total"
    )
    count_record = await count_result.single()
    assert count_record["total"] == 1000

    print(f"\nPerformance: 1000-node MERGE batch completed in {elapsed:.3f} seconds")

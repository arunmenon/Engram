"""In-memory reference backend for every storage port (ADR-0019 §6).

Used by the conformance suite as the reference, by fast tests, and as
proof that nothing above the ports depends on Redis or Neo4j. Not
durable and not shared between processes.
"""

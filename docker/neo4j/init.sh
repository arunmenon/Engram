#!/bin/bash
# Apply constraints from constraints.cypher on Neo4j startup
# This script is mounted to /docker-entrypoint-initdb.d/

echo "Applying Neo4j constraints..."
cypher-shell -u neo4j -p engram-dev-password -f /var/lib/neo4j/constraints/constraints.cypher
echo "Neo4j constraints applied."

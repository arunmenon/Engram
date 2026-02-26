#!/usr/bin/env bash
# Engram — Full Fly.io deployment script
#
# Prerequisites:
#   - flyctl installed (https://fly.io/docs/flyctl/install/)
#   - Authenticated: fly auth login
#
# Usage:
#   ./fly/deploy.sh              # Deploy everything
#   ./fly/deploy.sh api          # Deploy only the API
#   ./fly/deploy.sh redis        # Deploy only Redis
#   ./fly/deploy.sh neo4j        # Deploy only Neo4j

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REGION="${FLY_REGION:-sjc}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Check flyctl is installed
if ! command -v fly &> /dev/null; then
    error "flyctl not found. Install it: https://fly.io/docs/flyctl/install/"
    exit 1
fi

# ---- Deploy Redis Stack ----
deploy_redis() {
    info "Deploying Redis Stack..."

    # Create app if it doesn't exist
    if ! fly apps list | grep -q "engram-redis"; then
        fly apps create engram-redis --org personal
    fi

    # Create volume if it doesn't exist
    if ! fly volumes list -a engram-redis 2>/dev/null | grep -q "redis_data"; then
        fly volumes create redis_data --region "$REGION" --size 10 -a engram-redis -y
    fi

    # Set Redis password
    if [ -z "${REDIS_PASSWORD:-}" ]; then
        REDIS_PASSWORD=$(openssl rand -hex 16)
        warn "Generated REDIS_PASSWORD=$REDIS_PASSWORD — save this!"
    fi
    fly secrets set REDIS_PASSWORD="$REDIS_PASSWORD" -a engram-redis

    fly deploy --config "$SCRIPT_DIR/redis.toml" --region "$REGION" -a engram-redis

    info "Redis Stack deployed at engram-redis.internal:6379"
}

# ---- Deploy Neo4j ----
deploy_neo4j() {
    info "Deploying Neo4j..."

    if ! fly apps list | grep -q "engram-neo4j"; then
        fly apps create engram-neo4j --org personal
    fi

    if ! fly volumes list -a engram-neo4j 2>/dev/null | grep -q "neo4j_data"; then
        fly volumes create neo4j_data --region "$REGION" --size 10 -a engram-neo4j -y
    fi

    # Set Neo4j auth
    if [ -z "${NEO4J_PASSWORD:-}" ]; then
        NEO4J_PASSWORD=$(openssl rand -hex 16)
        warn "Generated NEO4J_PASSWORD=$NEO4J_PASSWORD — save this!"
    fi
    fly secrets set NEO4J_AUTH="neo4j/$NEO4J_PASSWORD" -a engram-neo4j

    fly deploy --config "$SCRIPT_DIR/neo4j.toml" --region "$REGION" -a engram-neo4j

    info "Neo4j deployed at engram-neo4j.internal:7687"
}

# ---- Deploy API + Workers ----
deploy_api() {
    info "Deploying API + Workers..."

    if ! fly apps list | grep -q "engram-api"; then
        fly apps create engram-api --org personal
    fi

    # Set secrets (if not already set)
    if [ -n "${REDIS_PASSWORD:-}" ]; then
        fly secrets set CG_REDIS_PASSWORD="$REDIS_PASSWORD" -a engram-api
    fi
    if [ -n "${NEO4J_PASSWORD:-}" ]; then
        fly secrets set CG_NEO4J_PASSWORD="$NEO4J_PASSWORD" -a engram-api
    fi

    cd "$PROJECT_DIR"
    fly deploy --config fly.toml --region "$REGION" -a engram-api

    info "API deployed. Check: fly status -a engram-api"
    info "Open: fly open -a engram-api"
}

# ---- Main ----
TARGET="${1:-all}"

case "$TARGET" in
    redis)
        deploy_redis
        ;;
    neo4j)
        deploy_neo4j
        ;;
    api)
        deploy_api
        ;;
    all)
        deploy_redis
        deploy_neo4j
        info "Waiting 15s for databases to initialize..."
        sleep 15
        deploy_api
        echo ""
        info "Deployment complete!"
        info "  API:   https://engram-api.fly.dev/v1/health"
        info "  Redis: engram-redis.internal:6379 (private)"
        info "  Neo4j: engram-neo4j.internal:7687 (private)"
        ;;
    *)
        error "Unknown target: $TARGET"
        echo "Usage: $0 [all|redis|neo4j|api]"
        exit 1
        ;;
esac

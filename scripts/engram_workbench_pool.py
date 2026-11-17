"""Inspect a pool allowlist, or explicitly create NEW dedicated sandbox databases.

No database deletion, adoption, IAM change, instance creation or schema repair.
With no --create flag this prints the plan without contacting Google Cloud.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from context_graph.adapters.spanner.lifecycle import close_database, prepare_cleanup
from context_graph.adapters.spanner.schema import schema_statements
from context_graph.adapters.spanner.tenant_control import TENANT_CONTROL_DDL
from context_graph.settings import Settings
from context_graph.workbench.pool_config import PoolConfig
from context_graph.workbench.spanner_pool import POOL_DDL, DedicatedSlot


def create_new(config: PoolConfig) -> list[dict[str, Any]]:
    import os

    from google.cloud import spanner
    from google.cloud.spanner_v1.pool import BurstyPool

    if os.environ.get("SPANNER_EMULATOR_HOST"):
        raise ValueError("Real sandbox provisioning cannot use an emulator endpoint")
    slots = []
    try:
        for resource in config.resources:
            _, project, _, instance, _, name = resource.split("/")
            client = spanner.Client(project=project)
            pool = BurstyPool()
            database = client.instance(instance).database(
                name,
                ddl_statements=[
                    *schema_statements(Settings().spanner.embedding_dimensions),
                    TENANT_CONTROL_DDL,
                    POOL_DDL,
                ],
                pool=pool,
            )
            prepare_cleanup(database, client, pool)
            slots.append(DedicatedSlot(database, resource=resource, pool_id=config.pool_id))
            if database.exists():
                raise ValueError("Refusing existing database; provisioning never adopts or resets")
        results = []
        for slot in slots:
            # Concurrent creation is rejected by the server. Never fall through
            # from AlreadyExists to registration of someone else's database.
            slot.database.create().result(timeout=300)
            slot.register_empty()
            results.append(slot.status())
        return results
    finally:
        for slot in slots:
            close_database(slot.database)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--create", action="store_true", help="Create only absent database targets")
    args = parser.parse_args()
    config = PoolConfig.model_validate_json(args.config.read_text())
    if not args.create:
        print(json.dumps({"mode": "plan_only", **config.model_dump()}, indent=2))
        return
    try:
        results = create_new(config)
    except Exception as exc:
        # SDK exception messages may include credentials or sensitive metadata.
        print(
            json.dumps(
                {
                    "status": "incomplete",
                    "error_type": type(exc).__name__,
                    "note": "No deletion attempted. Inspect targets before retrying.",
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps({"status": "registered", "slots": results}, default=str, indent=2))


if __name__ == "__main__":
    main()

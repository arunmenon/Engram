"""Explicit server-owned sandbox allowlist. Never creates or adopts databases."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from context_graph.adapters.spanner.lifecycle import close_database, open_owned_database
from context_graph.settings import Settings
from context_graph.workbench.execution import SpannerExecution
from context_graph.workbench.spanner_pool import DedicatedSlot, SandboxPool

if TYPE_CHECKING:
    from pathlib import Path

Resource = Annotated[
    str,
    StringConstraints(pattern=r"^projects/[a-z0-9-]+/instances/[a-z0-9-]+/databases/[a-z0-9-]+$"),
]


class PoolConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pool_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
    resources: list[Resource] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def distinct(self) -> PoolConfig:
        if len(set(self.resources)) != len(self.resources):
            raise ValueError("Sandbox database resources must be distinct")
        return self


def configured_execution(path: Path) -> SpannerExecution:
    """Validate local JSON before credentials/network; open only registered slots."""
    config = PoolConfig.model_validate_json(path.read_text())
    if os.environ.get("SPANNER_EMULATOR_HOST"):
        raise ValueError("Real Spanner sandbox configuration cannot use an emulator endpoint")

    slots = []
    try:
        for resource in config.resources:
            _, project, _, instance, _, name = resource.split("/")
            database = open_owned_database(project, instance, name)
            slot = DedicatedSlot(database, resource=resource, pool_id=config.pool_id)
            slots.append(slot)
            # Ownership validation is read-only. No register_empty/create/schema calls.
            slot.status()
        return SpannerExecution(SandboxPool(tuple(slots)), Settings(), owns_handles=True)
    except Exception:
        for slot in slots:
            close_database(slot.database)
        raise

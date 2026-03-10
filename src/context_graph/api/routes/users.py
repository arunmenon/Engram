"""User endpoints for profile, preferences, skills, patterns, and GDPR ops.

GET    /v1/users/{user_id}/profile      -- user profile
GET    /v1/users/{user_id}/preferences   -- active preferences (optional category filter)
GET    /v1/users/{user_id}/skills        -- skills with proficiency
GET    /v1/users/{user_id}/patterns      -- behavioral patterns
GET    /v1/users/{user_id}/interests     -- user interests
GET    /v1/users/{user_id}/data-export   -- GDPR data export
DELETE /v1/users/{user_id}               -- GDPR cascade erasure

Source: ADR-0012 S10.4
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse

from context_graph.api.dependencies import TenantContext, get_user_store, require_tenant
from context_graph.ports.user_store import UserStore  # noqa: TCH001 — runtime: Depends

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])

UserStoreDep = Annotated[UserStore, Depends(get_user_store)]
TenantDep = Annotated[TenantContext, Depends(require_tenant)]


@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """Return the profile for a given user, or 404 if not found."""
    profile = await user_store.get_user_profile(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return ORJSONResponse(
        content=profile,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.get("/{user_id}/preferences")
async def get_user_preferences(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
    category: str | None = Query(default=None),
) -> ORJSONResponse:
    """Return active preferences for a user, optionally filtered by category."""
    preferences = await user_store.get_user_preferences(
        user_id,
        active_only=True,
        tenant_id=tenant.tenant_id,
    )
    if category is not None:
        preferences = [p for p in preferences if p.get("category") == category]
    return ORJSONResponse(
        content=preferences,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.get("/{user_id}/skills")
async def get_user_skills(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """Return skills with proficiency for a user."""
    skills = await user_store.get_user_skills(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    return ORJSONResponse(
        content=skills,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.get("/{user_id}/patterns")
async def get_user_patterns(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """Return behavioral patterns for a user."""
    patterns = await user_store.get_user_patterns(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    return ORJSONResponse(
        content=patterns,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.get("/{user_id}/interests")
async def get_user_interests(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """Return interests for a user."""
    interests = await user_store.get_user_interests(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    return ORJSONResponse(
        content=interests,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.get("/{user_id}/data-export")
async def export_user_data(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """GDPR data export -- return all stored data for a user."""
    data = await user_store.export_user_data(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    logger.info("user_data_exported", user_id=user_id)
    return ORJSONResponse(
        content=data,
        headers={"X-Tenant-ID": tenant.tenant_id},
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    user_store: UserStoreDep,
    tenant: TenantDep,
) -> ORJSONResponse:
    """GDPR cascade erasure -- delete all data associated with a user."""
    deleted_count = await user_store.delete_user_data(
        user_id,
        tenant_id=tenant.tenant_id,
    )
    logger.info("user_data_erased", user_id=user_id, deleted_count=deleted_count)
    return ORJSONResponse(
        content={"deleted_count": deleted_count, "status": "erased"},
        headers={"X-Tenant-ID": tenant.tenant_id},
    )

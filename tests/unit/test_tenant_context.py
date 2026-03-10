"""Tests for TenantContext extraction and validation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from context_graph.api.dependencies import TenantContext, require_tenant


def _make_request(headers: dict[str, str] | None = None, tenant_enabled: bool = True) -> MagicMock:
    """Build a mock Request with app.state.settings wired up."""
    from context_graph.settings import Settings, TenantSettings

    tenant_settings = TenantSettings(enabled=tenant_enabled)
    settings = Settings(tenant=tenant_settings)

    request = MagicMock()
    request.app.state.settings = settings
    request.headers = headers or {}
    return request


@pytest.mark.asyncio
async def test_require_tenant_disabled_returns_default() -> None:
    """When tenancy is disabled, require_tenant returns the default tenant."""
    request = _make_request(tenant_enabled=False)
    ctx = await require_tenant(request)
    assert isinstance(ctx, TenantContext)
    assert ctx.tenant_id == "default"


@pytest.mark.asyncio
async def test_require_tenant_missing_header_returns_400() -> None:
    """When tenancy is enabled and header is missing, raise 400."""
    from fastapi import HTTPException

    request = _make_request(headers={}, tenant_enabled=True)
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant(request)
    assert exc_info.value.status_code == 400
    assert "X-Tenant-ID" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_tenant_invalid_format_returns_400() -> None:
    """Invalid tenant ID (uppercase, special chars) raises 400."""
    from fastapi import HTTPException

    # Uppercase
    request = _make_request(headers={"X-Tenant-ID": "INVALID"}, tenant_enabled=True)
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant(request)
    assert exc_info.value.status_code == 400
    assert "Invalid tenant ID format" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_tenant_too_short_returns_400() -> None:
    """Tenant ID shorter than 3 chars raises 400."""
    from fastapi import HTTPException

    request = _make_request(headers={"X-Tenant-ID": "ab"}, tenant_enabled=True)
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant(request)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_require_tenant_valid_header() -> None:
    """Valid tenant ID is extracted correctly."""
    request = _make_request(headers={"X-Tenant-ID": "acme-corp"}, tenant_enabled=True)
    ctx = await require_tenant(request)
    assert ctx.tenant_id == "acme-corp"


@pytest.mark.asyncio
async def test_require_tenant_custom_header_name() -> None:
    """Custom header name is respected."""
    from context_graph.settings import Settings, TenantSettings

    tenant_settings = TenantSettings(enabled=True, header_name="X-Org-ID")
    settings = Settings(tenant=tenant_settings)

    request = MagicMock()
    request.app.state.settings = settings
    request.headers = {"X-Org-ID": "acme-corp"}

    ctx = await require_tenant(request)
    assert ctx.tenant_id == "acme-corp"


@pytest.mark.asyncio
async def test_require_tenant_custom_header_name_missing() -> None:
    """Custom header name missing raises 400 with correct header name."""
    from fastapi import HTTPException

    from context_graph.settings import Settings, TenantSettings

    tenant_settings = TenantSettings(enabled=True, header_name="X-Org-ID")
    settings = Settings(tenant=tenant_settings)

    request = MagicMock()
    request.app.state.settings = settings
    request.headers = {}

    with pytest.raises(HTTPException) as exc_info:
        await require_tenant(request)
    assert exc_info.value.status_code == 400
    assert "X-Org-ID" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_tenant_context_is_frozen() -> None:
    """TenantContext is immutable (frozen dataclass)."""
    ctx = TenantContext(tenant_id="test")
    with pytest.raises(AttributeError):
        ctx.tenant_id = "other"  # type: ignore[misc]

"""E2E tests for security, auth, and header handling.

Covers:
1.  Health endpoint requires no auth (public)
2.  Events endpoint works without auth when CG_AUTH_API_KEY is unset (dev mode)
3.  CORS response headers on OPTIONS preflight
4.  Error responses do not leak exception class names
5.  422 validation errors have structured format
6.  Health response body does not contain credential strings
7.  Error responses do not contain credential strings
8.  X-Request-ID is generated when missing
9.  X-Request-ID is echoed back when provided
10. X-Request-Time-Ms header is present with numeric value

Prerequisites:
    - docker-compose up (redis, neo4j, api)
    - CG_AUTH_API_KEY must NOT be set (default dev mode)

Usage:
    python -m pytest tests/e2e/test_e2e_security.py -v
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
import pytest

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://localhost:8000"

# Known credential strings that must NEVER appear in responses
CREDENTIAL_STRINGS = [
    "engram-dev-password",
    "CG_AUTH_API_KEY",
    "CG_AUTH_ADMIN_KEY",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(session_id: str = "e2e-security-session") -> dict:
    """Create a valid event dict for ingestion."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "tool.execute",
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        "session_id": session_id,
        "agent_id": "e2e-security-agent",
        "trace_id": str(uuid.uuid4()),
        "payload_ref": f"ref://{uuid.uuid4().hex[:8]}",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Tier 0 — Auth & Headers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_no_auth_required(client: httpx.AsyncClient):
    """GET /v1/health works without any Authorization header (health is public)."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "status" in body
    assert body["status"] == "healthy"


@pytest.mark.asyncio
async def test_events_no_auth_when_disabled(client: httpx.AsyncClient):
    """POST /v1/events works without auth when CG_AUTH_API_KEY is not set (dev mode)."""
    event = make_event()
    resp = await client.post("/v1/events", json=event)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["event_id"] == event["event_id"]
    assert "global_position" in body
    assert body["global_position"] != ""


@pytest.mark.asyncio
async def test_cors_response_headers(client: httpx.AsyncClient):
    """OPTIONS preflight returns correct CORS headers."""
    resp = await client.options(
        "/v1/events",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type,X-Request-ID",
        },
    )
    # CORS preflight should return 200
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    # Verify Access-Control-Allow-Methods
    allow_methods = resp.headers.get("access-control-allow-methods", "")
    for method in ["GET", "POST", "DELETE", "OPTIONS"]:
        assert (
            method in allow_methods
        ), f"Missing {method} in Access-Control-Allow-Methods: {allow_methods}"

    # Verify Access-Control-Allow-Headers
    allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
    for header in ["authorization", "content-type", "x-request-id"]:
        assert (
            header in allow_headers
        ), f"Missing {header} in Access-Control-Allow-Headers: {allow_headers}"


@pytest.mark.asyncio
async def test_error_response_no_exception_type(client: httpx.AsyncClient):
    """Error responses must not leak exception class names in a 'type' field."""
    # Send event with missing required fields to trigger a 422
    bad_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "tool.execute",
        # Missing: occurred_at, session_id, agent_id, trace_id, payload_ref
    }
    resp = await client.post("/v1/events", json=bad_event)
    assert resp.status_code == 422

    # The response should NOT have a top-level "type" field exposing exception class name
    # Pydantic/FastAPI sometimes adds "type" to validation error details
    body_text = resp.text
    for dangerous_type in ["ValidationError", "RequestValidationError", "TypeError", "ValueError"]:
        assert (
            dangerous_type not in body_text or body_text.count(dangerous_type) == 0
        ), f"Exception class name '{dangerous_type}' leaked in error response"


@pytest.mark.asyncio
async def test_422_validation_error_format(client: httpx.AsyncClient):
    """422 validation error has structured format with 'detail' field."""
    bad_event = {
        "event_id": "not-a-valid-uuid",
        "event_type": "tool.execute",
        "occurred_at": datetime.now(tz=UTC).isoformat(),
        "session_id": "e2e-security-bad-format",
        "agent_id": "e2e-security-agent",
        "trace_id": str(uuid.uuid4()),
        "payload_ref": "ref://test",
    }
    resp = await client.post("/v1/events", json=bad_event)
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "detail" in body, "422 response must have 'detail' field"
    assert isinstance(body["detail"], list), "'detail' should be a list of error objects"
    assert len(body["detail"]) > 0, "'detail' should contain at least one error"


# ---------------------------------------------------------------------------
# Tier 1 — SecretStr / Credential leakage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_response_no_credentials(client: httpx.AsyncClient):
    """GET /v1/health response body must not contain any credential strings."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    body_text = resp.text
    for credential in CREDENTIAL_STRINGS:
        assert (
            credential not in body_text
        ), f"Credential string '{credential}' found in health response"


@pytest.mark.asyncio
async def test_error_responses_no_credentials(client: httpx.AsyncClient):
    """Error responses must not contain any credential strings."""
    # Trigger a 422 error
    bad_event = {"event_id": "bad"}
    resp = await client.post("/v1/events", json=bad_event)

    body_text = resp.text
    for credential in CREDENTIAL_STRINGS:
        assert (
            credential not in body_text
        ), f"Credential string '{credential}' found in error response"

    # Trigger a 404 error
    resp_404 = await client.get("/v1/entities/nonexistent-entity-security-test")
    body_404_text = resp_404.text
    for credential in CREDENTIAL_STRINGS:
        assert (
            credential not in body_404_text
        ), f"Credential string '{credential}' found in 404 response"


# ---------------------------------------------------------------------------
# Request ID (Tier 0)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(client: httpx.AsyncClient):
    """Requests without X-Request-ID get a generated UUID4 in the response."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    request_id = resp.headers.get("x-request-id")
    assert request_id is not None, "Missing X-Request-ID header in response"

    # Validate it is a valid UUID4
    parsed = uuid.UUID(request_id, version=4)
    assert str(parsed) == request_id, f"X-Request-ID is not a valid UUID4: {request_id}"


@pytest.mark.asyncio
async def test_request_id_echoed_back(client: httpx.AsyncClient):
    """When X-Request-ID is sent, the same value is echoed in the response."""
    custom_id = "my-custom-id-123"
    resp = await client.get(
        "/v1/health",
        headers={"X-Request-ID": custom_id},
    )
    assert resp.status_code == 200

    returned_id = resp.headers.get("x-request-id")
    assert returned_id == custom_id, f"Expected X-Request-ID '{custom_id}', got '{returned_id}'"


@pytest.mark.asyncio
async def test_request_time_header_present(client: httpx.AsyncClient):
    """Every response includes X-Request-Time-Ms header with a numeric value."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200

    time_ms = resp.headers.get("x-request-time-ms")
    assert time_ms is not None, "Missing X-Request-Time-Ms header"

    # Should be parseable as a float
    parsed_time = float(time_ms)
    assert parsed_time >= 0, f"X-Request-Time-Ms should be non-negative, got {parsed_time}"

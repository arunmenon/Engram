from __future__ import annotations

import asyncio
import math
import re
import uuid
from typing import Any

import httpx

from engram.config import EngramConfig
from engram.exceptions import (
    AuthenticationError,
    EngramError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TransportError,
    ValidationError,
)

_CREDENTIAL_PATTERNS = [
    re.compile(
        r'(?:api[_-]?key|admin[_-]?key|password|secret|token|authorization)'
        r'["\s:=]+["\']?[\w\-\.]+',
        re.IGNORECASE,
    ),
    re.compile(r'(?:redis|neo4j|postgres|mysql)://[^\s]+', re.IGNORECASE),
]


def _scrub_credentials(text: str) -> str:
    """Remove credential-like patterns from error messages."""
    result = text
    for pattern in _CREDENTIAL_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


class Transport:
    """HTTP transport with retry, rate-limit awareness, and request-ID propagation."""

    def __init__(self, config: EngramConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create the httpx client with connection pooling."""
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.AsyncClient(
                    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                    timeout=httpx.Timeout(self._config.timeout),
                    trust_env=False,
                )
            return self._client

    def _auth_headers(self, admin: bool = False) -> dict[str, str]:
        """Build Authorization header from config. Uses admin_key for admin=True."""
        key = self._config.admin_key if admin else self._config.api_key
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        admin: bool = False,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with retry and error mapping."""
        client = await self._ensure_client()
        url = self._config.effective_base_url() + path

        headers = self._auth_headers(admin=admin)
        headers["X-Request-ID"] = str(uuid.uuid4())

        request_timeout = httpx.Timeout(timeout) if timeout else None
        max_attempts = self._config.max_retries + 1

        last_exception: Exception | None = None

        for attempt in range(max_attempts):
            try:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                    timeout=request_timeout,
                )

                if response.status_code < 400:
                    return response

                # Retryable status codes
                if response.status_code == 429 and attempt < max_attempts - 1:
                    retry_after = self._parse_retry_after(response)
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code == 503 and attempt < max_attempts - 1:
                    backoff = 2**attempt
                    await asyncio.sleep(backoff)
                    continue

                # Non-retryable error
                raise self._map_error(response)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < max_attempts - 1:
                    backoff = 2**attempt
                    await asyncio.sleep(backoff)
                    continue
                raise TransportError(
                    f"Connection failed after {max_attempts} attempts: {exc}"
                ) from exc

        # Should not reach here, but handle the edge case
        if last_exception:
            raise TransportError(str(last_exception)) from last_exception
        raise TransportError("Request failed after all retry attempts")  # pragma: no cover

    MAX_RETRY_AFTER = 60.0

    def _parse_retry_after(self, response: httpx.Response) -> float:
        """Parse Retry-After header, defaulting to 1.0 second. Capped at 60s."""
        header = response.headers.get("Retry-After")
        if header:
            try:
                value = float(header)
                if value != value:  # NaN check
                    return 1.0
                if not math.isfinite(value):
                    return self.MAX_RETRY_AFTER
                if value <= 0:
                    return 1.0
                return min(value, self.MAX_RETRY_AFTER)
            except (ValueError, TypeError):
                pass
        return 1.0

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        admin: bool = False,
    ) -> httpx.Response:
        """Convenience GET."""
        return await self.request("GET", path, params=params, admin=admin)

    async def post(
        self,
        path: str,
        *,
        json: Any = None,
        admin: bool = False,
    ) -> httpx.Response:
        """Convenience POST."""
        return await self.request("POST", path, json=json, admin=admin)

    async def delete(
        self,
        path: str,
        *,
        admin: bool = False,
    ) -> httpx.Response:
        """Convenience DELETE."""
        return await self.request("DELETE", path, admin=admin)

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _map_error(self, response: httpx.Response) -> EngramError:
        """Map an HTTP error response to the appropriate SDK exception."""
        try:
            body = response.json()
        except Exception:
            body = None

        message = ""
        if isinstance(body, dict):
            message = body.get("detail", "") or body.get("message", "")
        if not message:
            message = f"HTTP {response.status_code}"

        # Scrub credentials from error messages and response body
        message = _scrub_credentials(str(message))
        scrubbed_body = body
        if isinstance(body, dict):
            scrubbed_body = {
                k: _scrub_credentials(str(v)) if isinstance(v, str) else v
                for k, v in body.items()
            }

        status = response.status_code

        if status == 401:
            return AuthenticationError(
                message, status_code=status, response_body=scrubbed_body
            )

        if status == 404:
            return NotFoundError(str(message))

        if status == 422:
            errors = None
            if isinstance(scrubbed_body, dict):
                errors = (
                    scrubbed_body.get("detail")
                    if isinstance(scrubbed_body.get("detail"), list)
                    else None
                )
            return ValidationError(str(message), errors=errors)

        if status == 429:
            retry_after = self._parse_retry_after(response)
            return RateLimitError(
                message, retry_after=retry_after, response_body=scrubbed_body
            )

        if status >= 500:
            return ServerError(
                message, status_code=status, response_body=scrubbed_body
            )

        return TransportError(
            message, status_code=status, response_body=scrubbed_body
        )

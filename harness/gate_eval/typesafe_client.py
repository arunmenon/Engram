"""Minimal TypeSafe System One client (urllib only) with full call logging.

Every call records the exact request bytes, their sha256, the response, billed
tokens, latency and the reported model version. No retries are hidden: a
failed call is logged as failed and re-raised to the caller, which decides
whether the run stops.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .common import PreflightError, sha256_bytes

DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone"


@dataclass
class CallResult:
    request_sha256: str
    request_bytes_len: int
    status: str
    http_status: int | None
    response: dict | None
    model_reported: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    error: str | None = None


class TypeSafeClient:
    def __init__(self, api_key: str, endpoint: str = DEFAULT_ENDPOINT, timeout_s: float = 60.0,
                 pinned_model_version: str | None = None) -> None:
        if not api_key:
            raise PreflightError("TYPESAFE_API_KEY is not set; the harness never embeds a key")
        self._api_key = api_key
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.pinned_model_version = pinned_model_version

    def call(self, body: bytes) -> CallResult:
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        digest = sha256_bytes(body)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as resp:
                raw = resp.read()
                http_status = resp.status
        except urllib.error.HTTPError as exc:
            latency = (time.perf_counter() - started) * 1000
            detail = exc.read().decode("utf-8", "replace")[:2000]
            return CallResult(digest, len(body), "failed", exc.code, None, None, None, None, latency, detail)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            latency = (time.perf_counter() - started) * 1000
            return CallResult(digest, len(body), "failed", None, None, None, None, None, latency, str(exc))
        latency = (time.perf_counter() - started) * 1000
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return CallResult(digest, len(body), "failed", http_status, None, None, None, None, latency, f"bad json: {exc}")
        usage = payload.get("usage") or {}
        model_reported = payload.get("model")
        if self.pinned_model_version and model_reported != self.pinned_model_version:
            return CallResult(
                digest, len(body), "version_mismatch", http_status, payload, model_reported,
                usage.get("input_tokens"), usage.get("output_tokens"), latency,
                f"reported model {model_reported!r} differs from pinned {self.pinned_model_version!r}",
            )
        return CallResult(
            digest, len(body), "ok", http_status, payload, model_reported,
            usage.get("input_tokens"), usage.get("output_tokens"), latency,
        )

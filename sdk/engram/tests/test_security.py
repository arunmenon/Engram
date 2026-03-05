"""Security tests for the Engram SDK — credential leakage, key validation, HTTPS, env coercion."""

from __future__ import annotations

import os
import warnings
from unittest.mock import patch

import httpx
import pytest

from engram.config import EngramConfig, _config_from_env, reset_config
from engram.exceptions import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    ServerError,
    TransportError,
)
from engram.transport import Transport, _scrub_credentials

# ---------------------------------------------------------------------------
# TestCredentialLeakage
# ---------------------------------------------------------------------------


class TestCredentialLeakage:
    """Ensure credentials never leak through error messages or repr/str."""

    def test_auth_error_no_key_in_str(self):
        secret = "sk-secret-key-abc123"
        err = AuthenticationError(
            "Invalid credentials",
            status_code=401,
            response_body={"detail": f"Invalid api_key={secret}"},
        )
        assert secret not in str(err)

    def test_auth_error_no_key_in_repr(self):
        secret = "sk-secret-key-abc123"
        err = AuthenticationError(
            "Invalid credentials",
            status_code=401,
            response_body={"detail": f"api_key={secret}"},
        )
        assert secret not in repr(err)

    def test_config_repr_redacted(self):
        config = EngramConfig(api_key="sk-secret-123")
        r = repr(config)
        assert "sk-secret-123" not in r
        assert "***" in r

    def test_config_str_redacted(self):
        config = EngramConfig(api_key="sk-secret-123")
        s = str(config)
        assert "sk-secret-123" not in s
        assert "***" in s

    def test_admin_key_redacted_in_config(self):
        config = EngramConfig(admin_key="admin-super-secret")
        r = repr(config)
        assert "admin-super-secret" not in r
        assert "***" in r

    def test_rate_limit_error_body_scrubbed(self):
        """RateLimitError with api_key in response_body should have it scrubbed via transport."""
        transport = Transport(EngramConfig())
        response = httpx.Response(
            429,
            json={"detail": "Rate limit exceeded, api_key=sk-secret-xyz"},
            headers={"Retry-After": "5"},
            request=httpx.Request("GET", "http://test:8000/v1/test"),
        )
        err = transport._map_error(response)
        assert isinstance(err, RateLimitError)
        assert "sk-secret-xyz" not in str(err)
        body = err.response_body or {}
        for v in body.values():
            if isinstance(v, str):
                assert "sk-secret-xyz" not in v

    def test_server_error_body_scrubbed(self):
        """ServerError with credentials in response_body should have them scrubbed."""
        transport = Transport(EngramConfig())
        response = httpx.Response(
            500,
            json={"detail": "Internal error api_key=sk-compromised-key"},
            request=httpx.Request("GET", "http://test:8000/v1/test"),
        )
        err = transport._map_error(response)
        assert isinstance(err, ServerError)
        assert "sk-compromised-key" not in str(err)

    def test_transport_error_body_scrubbed(self):
        """TransportError response_body with credentials should be scrubbed."""
        transport = Transport(EngramConfig())
        response = httpx.Response(
            400,
            json={"detail": "Bad request, token=my-secret-token-val"},
            request=httpx.Request("GET", "http://test:8000/v1/test"),
        )
        err = transport._map_error(response)
        assert isinstance(err, TransportError)
        assert "my-secret-token-val" not in str(err)


# ---------------------------------------------------------------------------
# TestScrubCredentials
# ---------------------------------------------------------------------------


class TestScrubCredentials:
    """Unit tests for the _scrub_credentials helper."""

    def test_scrub_api_key(self):
        result = _scrub_credentials("Error: api_key=sk-12345 was invalid")
        assert "sk-12345" not in result
        assert "[REDACTED]" in result

    def test_scrub_connection_string(self):
        result = _scrub_credentials("Failed to connect to redis://user:pass@host:6379")
        assert "user:pass" not in result
        assert "[REDACTED]" in result

    def test_scrub_neo4j_connection(self):
        result = _scrub_credentials("Connection to neo4j://admin:secret@db:7687 failed")
        assert "admin:secret" not in result

    def test_no_false_positive_on_normal_text(self):
        text = "Query returned 42 nodes in 15ms"
        assert _scrub_credentials(text) == text


# ---------------------------------------------------------------------------
# TestAPIKeyValidation
# ---------------------------------------------------------------------------


class TestAPIKeyValidation:
    """Test API key normalization and validation."""

    def test_empty_string_api_key(self):
        config = _config_from_env(api_key="")
        assert config.api_key is None

    def test_whitespace_only_api_key(self):
        config = _config_from_env(api_key="   ")
        assert config.api_key is None

    def test_newline_in_api_key(self):
        with pytest.raises(ConfigurationError, match="newlines"):
            _config_from_env(api_key="key\nheader-injection")

    def test_bearer_prefix_stripped(self):
        config = _config_from_env(api_key="Bearer sk-123")
        assert config.api_key == "sk-123"

    def test_valid_api_key_accepted(self):
        config = _config_from_env(api_key="sk-valid-key")
        assert config.api_key == "sk-valid-key"


# ---------------------------------------------------------------------------
# TestHTTPSEnforcement
# ---------------------------------------------------------------------------


class TestHTTPSEnforcement:
    """Warn when using HTTP for non-local hosts."""

    def test_http_prod_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _config_from_env(base_url="http://prod.example.com")
        warning_messages = [str(w.message) for w in caught]
        assert any("HTTP" in m for m in warning_messages)

    def test_https_no_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _config_from_env(base_url="https://prod.example.com")
        warning_messages = [str(w.message) for w in caught]
        assert not any("HTTP" in m for m in warning_messages)

    def test_http_localhost_exempt(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _config_from_env(base_url="http://localhost:8000")
        warning_messages = [str(w.message) for w in caught]
        assert not any("HTTP" in m for m in warning_messages)

    def test_http_127_exempt(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _config_from_env(base_url="http://127.0.0.1:8000")
        warning_messages = [str(w.message) for w in caught]
        assert not any("HTTP" in m for m in warning_messages)


# ---------------------------------------------------------------------------
# TestConfigEnvCoercion
# ---------------------------------------------------------------------------


class TestConfigEnvCoercion:
    """Env var coercion errors should raise ConfigurationError, not raw ValueError."""

    def test_timeout_non_numeric_env(self):
        with patch.dict(os.environ, {"ENGRAM_TIMEOUT": "not-a-number"}, clear=False):
            reset_config()
            with pytest.raises(ConfigurationError, match="ENGRAM_TIMEOUT"):
                _config_from_env()

    def test_max_retries_non_numeric_env(self):
        with patch.dict(os.environ, {"ENGRAM_MAX_RETRIES": "abc"}, clear=False):
            reset_config()
            with pytest.raises(ConfigurationError, match="ENGRAM_MAX_RETRIES"):
                _config_from_env()

    def test_negative_timeout(self):
        with pytest.raises(ConfigurationError, match="timeout must be positive"):
            _config_from_env(timeout=-5.0)

    def test_negative_retries(self):
        with pytest.raises(ConfigurationError, match="max_retries must be non-negative"):
            _config_from_env(max_retries=-1)


# ---------------------------------------------------------------------------
# TestAdminKeyUsage
# ---------------------------------------------------------------------------


class TestAdminKeyUsage:
    """Verify correct key selection for admin vs regular endpoints."""

    @pytest.fixture
    def config_both_keys(self):
        return EngramConfig(
            base_url="http://test:8000",
            api_key="user-api-key",
            admin_key="admin-secret-key",
        )

    def test_admin_endpoint_without_admin_key(self):
        config = EngramConfig(base_url="http://test:8000", api_key="user-key")
        transport = Transport(config)
        headers = transport._auth_headers(admin=True)
        # No admin_key set, so no Authorization header for admin
        assert "Authorization" not in headers

    def test_admin_endpoint_with_admin_key(self):
        config = EngramConfig(base_url="http://test:8000", admin_key="admin-key-123")
        transport = Transport(config)
        headers = transport._auth_headers(admin=True)
        assert headers["Authorization"] == "Bearer admin-key-123"

    def test_regular_endpoint_uses_api_key(self, config_both_keys):
        transport = Transport(config_both_keys)
        headers = transport._auth_headers(admin=False)
        assert headers["Authorization"] == "Bearer user-api-key"
        assert "admin-secret-key" not in headers["Authorization"]

    def test_both_keys_set(self, config_both_keys):
        transport = Transport(config_both_keys)
        regular_headers = transport._auth_headers(admin=False)
        admin_headers = transport._auth_headers(admin=True)
        assert regular_headers["Authorization"] == "Bearer user-api-key"
        assert admin_headers["Authorization"] == "Bearer admin-secret-key"

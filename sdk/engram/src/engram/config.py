from __future__ import annotations

import os
import threading
import warnings
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from engram.exceptions import ConfigurationError


class EngramConfig(BaseModel):
    """SDK configuration. Read from env vars or set explicitly."""

    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field(default="http://localhost:8000")
    api_key: str | None = Field(default=None)
    admin_key: str | None = Field(default=None)
    timeout: float = Field(default=30.0)
    max_retries: int = Field(default=3)

    def effective_base_url(self) -> str:
        """Return base_url with trailing slash stripped, plus /v1 prefix."""
        return self.base_url.rstrip("/") + "/v1"

    def __repr__(self) -> str:
        """Repr that redacts sensitive fields."""
        api_display = "***" if self.api_key else "None"
        admin_display = "***" if self.admin_key else "None"
        return (
            f"EngramConfig(base_url={self.base_url!r}, api_key={api_display!r}, "
            f"admin_key={admin_display!r}, timeout={self.timeout}, "
            f"max_retries={self.max_retries})"
        )

    def __str__(self) -> str:
        return self.__repr__()


_config_lock = threading.Lock()
_global_config: EngramConfig | None = None

# Hosts exempt from HTTPS warnings (local development)
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]"}  # noqa: S104


def _config_from_env(**overrides: Any) -> EngramConfig:
    """Build config from environment variables with optional overrides."""
    values: dict[str, Any] = {}
    env_map = {
        "base_url": "ENGRAM_BASE_URL",
        "api_key": "ENGRAM_API_KEY",
        "admin_key": "ENGRAM_ADMIN_KEY",
        "timeout": "ENGRAM_TIMEOUT",
        "max_retries": "ENGRAM_MAX_RETRIES",
    }
    for field_name, env_var in env_map.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            if field_name == "timeout":
                try:
                    values[field_name] = float(env_val)
                except ValueError as exc:
                    raise ConfigurationError(
                        f"ENGRAM_TIMEOUT must be a number, got {env_val!r}"
                    ) from exc
            elif field_name == "max_retries":
                try:
                    values[field_name] = int(env_val)
                except ValueError as exc:
                    raise ConfigurationError(
                        f"ENGRAM_MAX_RETRIES must be an integer, got {env_val!r}"
                    ) from exc
            else:
                values[field_name] = env_val

    # Overrides take precedence
    for key, val in overrides.items():
        if val is not None:
            values[key] = val

    config = EngramConfig(**values)

    # Normalize empty/whitespace api_key to None; reject newlines
    if config.api_key is not None:
        stripped = config.api_key.strip()
        if not stripped:
            config = config.model_copy(update={"api_key": None})
        elif "\n" in config.api_key or "\r" in config.api_key:
            raise ConfigurationError("API key must not contain newlines")
        elif stripped.startswith("Bearer "):
            config = config.model_copy(
                update={"api_key": stripped.removeprefix("Bearer ").strip()}
            )

    # Normalize empty/whitespace admin_key to None; reject newlines
    if config.admin_key is not None:
        stripped = config.admin_key.strip()
        if not stripped:
            config = config.model_copy(update={"admin_key": None})
        elif "\n" in config.admin_key or "\r" in config.admin_key:
            raise ConfigurationError("Admin key must not contain newlines")

    # Validate numeric bounds
    if config.timeout <= 0:
        raise ConfigurationError(
            f"timeout must be positive, got {config.timeout}"
        )
    if config.max_retries < 0:
        raise ConfigurationError(
            f"max_retries must be non-negative, got {config.max_retries}"
        )

    # Warn on non-HTTPS for non-local hosts
    if config.base_url.startswith("http://"):
        from urllib.parse import urlparse

        parsed = urlparse(config.base_url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in _LOCAL_HOSTS:
            warnings.warn(
                f"Engram base_url uses HTTP ({config.base_url}). "
                "Use HTTPS in production.",
                UserWarning,
                stacklevel=2,
            )

    return config


def get_config() -> EngramConfig:
    """Return the global config, creating from env vars if needed."""
    global _global_config  # noqa: PLW0603
    with _config_lock:
        if _global_config is None:
            _global_config = _config_from_env()
        return _global_config


def configure(
    base_url: str | None = None,
    api_key: str | None = None,
    admin_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> EngramConfig:
    """Set global config explicitly. Returns the config for chaining."""
    global _global_config  # noqa: PLW0603
    with _config_lock:
        _global_config = _config_from_env(
            base_url=base_url,
            api_key=api_key,
            admin_key=admin_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        return _global_config


def reset_config() -> None:
    """Reset global config to None (forces re-read from env). For testing."""
    global _global_config  # noqa: PLW0603
    with _config_lock:
        _global_config = None

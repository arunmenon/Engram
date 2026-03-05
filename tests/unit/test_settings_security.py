"""Tests for H9 fix: SecretStr credential handling."""

from __future__ import annotations

from pydantic import SecretStr

from context_graph.settings import Neo4jSettings, RedisSettings


class TestNeo4jSecretStr:
    """Neo4j password is SecretStr."""

    def test_password_is_secret_str(self) -> None:
        settings = Neo4jSettings()
        assert isinstance(settings.password, SecretStr)

    def test_password_default_value(self) -> None:
        settings = Neo4jSettings()
        assert settings.password.get_secret_value() == "engram-dev-password"

    def test_password_not_in_repr(self) -> None:
        settings = Neo4jSettings()
        assert "engram-dev-password" not in repr(settings)

    def test_password_from_env(self, monkeypatch: object) -> None:
        import pytest

        mp = pytest.MonkeyPatch()
        mp.setenv("CG_NEO4J_PASSWORD", "prod-secret")
        try:
            settings = Neo4jSettings()
            assert settings.password.get_secret_value() == "prod-secret"
        finally:
            mp.undo()


class TestRedisSecretStr:
    """Redis password is SecretStr | None."""

    def test_password_default_is_none(self) -> None:
        settings = RedisSettings()
        assert settings.password is None

    def test_password_from_env(self, monkeypatch: object) -> None:
        import pytest

        mp = pytest.MonkeyPatch()
        mp.setenv("CG_REDIS_PASSWORD", "redis-secret")
        try:
            settings = RedisSettings()
            assert isinstance(settings.password, SecretStr)
            assert settings.password.get_secret_value() == "redis-secret"
        finally:
            mp.undo()

    def test_none_password_not_in_repr(self) -> None:
        settings = RedisSettings()
        r = repr(settings)
        # None password should not leak any sensitive data
        assert "redis-secret" not in r

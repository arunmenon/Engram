from __future__ import annotations

import os
from unittest.mock import patch

from engram.config import EngramConfig, configure, get_config, reset_config


class TestEngramConfig:
    def test_config_defaults(self):
        config = EngramConfig()
        assert config.base_url == "http://localhost:8000"
        assert config.api_key is None
        assert config.admin_key is None
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_config_from_env(self):
        env = {
            "ENGRAM_BASE_URL": "http://prod:9000",
            "ENGRAM_API_KEY": "key-123",
            "ENGRAM_ADMIN_KEY": "admin-456",
            "ENGRAM_TIMEOUT": "60.0",
            "ENGRAM_MAX_RETRIES": "5",
        }
        with patch.dict(os.environ, env, clear=False):
            reset_config()
            config = get_config()
            assert config.base_url == "http://prod:9000"
            assert config.api_key == "key-123"
            assert config.admin_key == "admin-456"
            assert config.timeout == 60.0
            assert config.max_retries == 5

    def test_configure_explicit(self):
        env = {"ENGRAM_BASE_URL": "http://from-env:8000"}
        with patch.dict(os.environ, env, clear=False):
            config = configure(base_url="http://explicit:9000", api_key="my-key")
            assert config.base_url == "http://explicit:9000"
            assert config.api_key == "my-key"

    def test_effective_base_url(self):
        config = EngramConfig(base_url="http://localhost:8000/")
        assert config.effective_base_url() == "http://localhost:8000/v1"
        config2 = EngramConfig(base_url="http://localhost:8000")
        assert config2.effective_base_url() == "http://localhost:8000/v1"

    def test_reset_config(self):
        configure(base_url="http://first:8000")
        c1 = get_config()
        assert c1.base_url == "http://first:8000"
        reset_config()
        c2 = get_config()
        # After reset, should pick defaults (no env override in this test)
        assert c2.base_url == "http://localhost:8000"

    def test_get_config_lazy(self):
        reset_config()
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

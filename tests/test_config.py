"""Tests for load_config() and AppConfig defaults."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobfinder.config import AppConfig, load_config


class TestAppConfigDefaults:
    def test_default_model_provider(self):
        cfg = AppConfig()
        assert cfg.model_provider == "anthropic"

    def test_default_browser_agent_fields(self):
        cfg = AppConfig()
        assert cfg.browser_agent_max_time_minutes == 15
        assert cfg.browser_agent_max_steps == 100
        assert cfg.browser_agent_rate_limit_max_retries == 5
        assert cfg.browser_agent_rate_limit_initial_wait == 5

    def test_default_rpm_limit(self):
        assert AppConfig().rpm_limit == 4

    def test_default_write_preference(self):
        assert AppConfig().write_preference == "overwrite"

    def test_role_filters_none_by_default(self):
        assert AppConfig().role_filters is None


class TestLoadConfig:
    def test_reads_json_file(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"max_companies": 42, "rpm_limit": 0}))
        cfg = load_config(config_path=str(cfg_file))
        assert cfg.max_companies == 42
        assert cfg.rpm_limit == 0

    def test_overrides_win(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"max_companies": 10}))
        cfg = load_config(config_path=str(cfg_file), max_companies=99)
        assert cfg.max_companies == 99

    def test_none_override_ignored(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"max_companies": 10}))
        # Passing None for override should leave file value intact
        cfg = load_config(config_path=str(cfg_file), max_companies=None)
        assert cfg.max_companies == 10

    def test_missing_config_file_uses_defaults(self, tmp_path: Path):
        cfg = load_config(config_path=str(tmp_path / "nonexistent.json"))
        assert cfg.model_provider == "anthropic"

    def test_invalid_model_provider_raises(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"model_provider": "openai"}))
        with pytest.raises(SystemExit):
            load_config(config_path=str(cfg_file))

    def test_gemini_provider_accepted(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"model_provider": "gemini"}))
        cfg = load_config(config_path=str(cfg_file))
        assert cfg.model_provider == "gemini"

    def test_role_filters_parsed(self, tmp_path: Path):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({
            "role_filters": {"title": "Engineer", "confidence": "high"}
        }))
        cfg = load_config(config_path=str(cfg_file))
        assert cfg.role_filters is not None
        assert cfg.role_filters.title == "Engineer"

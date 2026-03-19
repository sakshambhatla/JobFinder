"""Tests for StorageManager and api_profiles helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from jobfinder.storage.store import StorageManager
from jobfinder.storage.api_profiles import (
    load_profile,
    save_profile,
    all_profiles,
    _domain_key,
    _validate_profile_domain,
)


# ── StorageManager ──────────────────────────────────────────────────────────────

class TestStorageManager:
    def test_write_then_read_dict(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        data = {"key": "value", "num": 42}
        store.write("test.json", data)
        result = store.read("test.json")
        assert result == data

    def test_write_then_read_list(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        data = [{"id": 1}, {"id": 2}]
        store.write("list.json", data)
        result = store.read("list.json")
        assert result == data

    def test_read_missing_file_returns_none(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        assert store.read("nonexistent.json") is None

    def test_exists_true(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        store.write("exists.json", {})
        assert store.exists("exists.json") is True

    def test_exists_false(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        assert store.exists("missing.json") is False

    def test_write_creates_parent_dirs(self, tmp_path: Path):
        store = StorageManager(tmp_path / "nested" / "dir")
        store.write("file.json", {"ok": True})
        assert (tmp_path / "nested" / "dir" / "file.json").exists()

    def test_overwrite_updates_value(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        store.write("data.json", {"v": 1})
        store.write("data.json", {"v": 2})
        assert store.read("data.json") == {"v": 2}


# ── API profiles ────────────────────────────────────────────────────────────────

class TestDomainKey:
    def test_extracts_netloc(self):
        assert _domain_key("https://explore.jobs.netflix.net/careers") == "explore.jobs.netflix.net"

    def test_strips_path(self):
        assert _domain_key("https://jobs.example.com/open-roles?foo=bar") == "jobs.example.com"

    def test_simple_domain(self):
        assert _domain_key("https://example.com") == "example.com"


class TestApiProfiles:
    def test_save_then_load(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://explore.jobs.netflix.net/careers"
        profile = {
            "platform": "Eightfold AI",
            "endpoints": [{"method": "POST", "path": "/api/jobs"}],
        }
        save_profile(url, "Netflix", profile, store)
        loaded = load_profile(url, store)
        assert loaded is not None
        assert loaded["platform"] == "Eightfold AI"
        assert "Netflix" in loaded["companies"]

    def test_load_unknown_domain_returns_none(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        result = load_profile("https://unknown.example.com", store)
        assert result is None

    def test_save_merges_companies(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://jobs.example.com"
        save_profile(url, "Company A", {"platform": "X"}, store)
        save_profile(url, "Company B", {"platform": "X"}, store)
        loaded = load_profile(url, store)
        assert "Company A" in loaded["companies"]
        assert "Company B" in loaded["companies"]

    def test_save_upserts_fields(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://jobs.example.com"
        save_profile(url, "Co", {"platform": "Old", "extra": "keep"}, store)
        save_profile(url, "Co", {"platform": "New"}, store)
        loaded = load_profile(url, store)
        # New fields win
        assert loaded["platform"] == "New"
        # Old extra field preserved (merging)
        assert loaded["extra"] == "keep"

    def test_all_profiles_returns_all(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        save_profile("https://a.com", "A", {"p": 1}, store)
        save_profile("https://b.com", "B", {"p": 2}, store)
        profiles = all_profiles(store)
        assert "a.com" in profiles
        assert "b.com" in profiles

    def test_all_profiles_empty_when_no_file(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        assert all_profiles(store) == {}

    def test_save_rejects_foreign_absolute_url(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://jobs.netflix.com/careers"
        profile = {
            "endpoints": [{"method": "POST", "path": "https://evil.com/steal"}],
        }
        save_profile(url, "Netflix", profile, store)
        assert load_profile(url, store) is None  # not written

    def test_save_allows_relative_path(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://jobs.netflix.com/careers"
        profile = {
            "endpoints": [{"method": "POST", "path": "/api/apply/v2/jobs"}],
        }
        save_profile(url, "Netflix", profile, store)
        loaded = load_profile(url, store)
        assert loaded is not None
        assert loaded["endpoints"][0]["path"] == "/api/apply/v2/jobs"

    def test_save_allows_same_domain_absolute_url(self, tmp_path: Path):
        store = StorageManager(tmp_path)
        url = "https://jobs.netflix.com/careers"
        profile = {
            "endpoints": [{"method": "GET", "path": "https://jobs.netflix.com/api/jobs"}],
        }
        save_profile(url, "Netflix", profile, store)
        loaded = load_profile(url, store)
        assert loaded is not None


# ── Domain validation unit tests ───────────────────────────────────────────────

class TestValidateProfileDomain:
    def test_relative_path_accepted(self):
        assert _validate_profile_domain(
            "https://jobs.example.com",
            {"endpoints": [{"path": "/api/jobs"}]},
        ) is True

    def test_same_domain_accepted(self):
        assert _validate_profile_domain(
            "https://jobs.example.com",
            {"endpoints": [{"path": "https://jobs.example.com/api/jobs"}]},
        ) is True

    def test_foreign_domain_rejected(self):
        assert _validate_profile_domain(
            "https://jobs.example.com",
            {"endpoints": [{"path": "https://evil.com/steal"}]},
        ) is False

    def test_empty_url_rejected(self):
        assert _validate_profile_domain(
            "",
            {"endpoints": [{"path": "/api/jobs"}]},
        ) is False

    def test_no_endpoints_accepted(self):
        assert _validate_profile_domain(
            "https://jobs.example.com",
            {"platform": "Custom"},
        ) is True

    def test_mixed_paths_one_foreign_rejected(self):
        assert _validate_profile_domain(
            "https://jobs.example.com",
            {"endpoints": [
                {"path": "/api/jobs"},
                {"path": "https://evil.com/phish"},
            ]},
        ) is False

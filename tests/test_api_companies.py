"""Tests for /api/companies endpoint using FastAPI TestClient."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _seed_companies(tmp_data_dir: Path, companies: list[dict] | None = None) -> None:
    """Write a minimal companies.json to the temp data dir."""
    data = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "source_resume_hash": "abc123",
        "companies": companies or [],
    }
    (tmp_data_dir / "companies.json").write_text(json.dumps(data))


class TestGetCompanies:
    def test_no_data_returns_404(self, client):
        response = client.get("/api/companies")
        assert response.status_code == 404

    def test_returns_seeded_data(self, client, tmp_data_dir):
        company = {
            "name": "Acme Corp",
            "reason": "Great data team",
            "career_page_url": "https://acme.com/careers",
            "ats_type": "greenhouse",
            "ats_board_token": "acme",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "roles_fetched": False,
        }
        _seed_companies(tmp_data_dir, [company])

        response = client.get("/api/companies")
        assert response.status_code == 200
        body = response.json()
        assert "companies" in body
        assert len(body["companies"]) == 1
        assert body["companies"][0]["name"] == "Acme Corp"

    def test_returns_correct_metadata(self, client, tmp_data_dir):
        _seed_companies(tmp_data_dir)
        body = client.get("/api/companies").json()
        assert "discovered_at" in body
        assert "companies" in body


class TestGetCompanyRegistry:
    def test_returns_registry_list(self, client):
        """Registry is empty on startup but endpoint returns a list."""
        response = client.get("/api/companies/registry")
        assert response.status_code == 200
        body = response.json()
        assert "companies" in body
        assert isinstance(body["companies"], list)

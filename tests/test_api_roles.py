"""Tests for /api/roles endpoint using FastAPI TestClient."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _seed_roles(tmp_data_dir: Path, roles: list[dict] | None = None) -> None:
    """Write a minimal roles.json to the temp data dir."""
    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_roles": len(roles or []),
        "roles_after_filter": len(roles or []),
        "companies_fetched": 1,
        "companies_flagged": 0,
        "flagged_companies": [],
        "roles": roles or [],
    }
    (tmp_data_dir / "roles.json").write_text(json.dumps(data))


class TestGetRoles:
    def test_no_data_returns_404(self, client):
        response = client.get("/api/roles")
        assert response.status_code == 404

    def test_returns_seeded_data(self, client, tmp_data_dir):
        role = {
            "company_name": "Acme",
            "title": "Staff Data Engineer",
            "location": "Remote",
            "url": "https://acme.com/jobs/1",
            "ats_type": "greenhouse",
            "ats_job_id": None,
            "department": "Engineering",
            "team": None,
            "commitment": None,
            "workplace_type": None,
            "employment_type": None,
            "is_remote": True,
            "posted_at": None,
            "updated_at": None,
            "published_at": None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "relevance_score": 9,
            "summary": "Great role",
        }
        _seed_roles(tmp_data_dir, [role])

        response = client.get("/api/roles")
        assert response.status_code == 200
        body = response.json()
        assert "roles" in body
        assert len(body["roles"]) == 1
        assert body["roles"][0]["title"] == "Staff Data Engineer"

    def test_returns_correct_metadata(self, client, tmp_data_dir):
        _seed_roles(tmp_data_dir)
        body = client.get("/api/roles").json()
        assert "fetched_at" in body
        assert "total_roles" in body
        assert "companies_fetched" in body
        assert "flagged_companies" in body

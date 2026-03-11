"""Tests for /api/resume endpoints using FastAPI TestClient."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RESUME_TXT = (FIXTURES_DIR / "resume.txt").read_text()


class TestUploadResume:
    def test_upload_valid_txt_returns_200(self, client):
        response = client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", RESUME_TXT.encode(), "text/plain")},
        )
        assert response.status_code == 200
        body = response.json()
        assert "resumes" in body
        assert len(body["resumes"]) == 1

    def test_upload_returns_skills(self, client):
        response = client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", RESUME_TXT.encode(), "text/plain")},
        )
        resumes = response.json()["resumes"]
        skills_lower = [s.lower() for s in resumes[0]["skills"]]
        assert any("python" in s for s in skills_lower)

    def test_upload_non_txt_returns_400(self, client):
        response = client.post(
            "/api/resume/upload",
            files={"file": ("resume.pdf", b"fake pdf content", "application/pdf")},
        )
        assert response.status_code == 400

    def test_upload_no_extension_returns_400(self, client):
        response = client.post(
            "/api/resume/upload",
            files={"file": ("resume", b"some text", "text/plain")},
        )
        assert response.status_code == 400


class TestGetResume:
    def test_get_without_data_returns_404(self, client):
        response = client.get("/api/resume")
        assert response.status_code == 404

    def test_get_after_upload_returns_200(self, client):
        # Upload first
        client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", RESUME_TXT.encode(), "text/plain")},
        )
        # Then GET
        response = client.get("/api/resume")
        assert response.status_code == 200
        assert "resumes" in response.json()

    def test_get_returns_list_of_resumes(self, client):
        client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", RESUME_TXT.encode(), "text/plain")},
        )
        data = client.get("/api/resume").json()
        resumes = data["resumes"]
        assert isinstance(resumes, list)
        assert len(resumes) >= 1

    def test_get_resume_has_expected_keys(self, client):
        client.post(
            "/api/resume/upload",
            files={"file": ("resume.txt", RESUME_TXT.encode(), "text/plain")},
        )
        resume = client.get("/api/resume").json()["resumes"][0]
        for key in ("filename", "skills", "job_titles", "companies_worked_at", "education", "parsed_at"):
            assert key in resume, f"Missing key: {key}"

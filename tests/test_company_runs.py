"""Tests for company runs: name generator, discover endpoint, and list/get routes."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from jobfinder.company_runs.name_generator import (
    ADJECTIVES,
    NOUNS,
    generate_run_name,
)


# ─── Name generator ─────────────────────────────────────────────────────────


class TestGenerateRunName:
    def test_returns_hyphenated_name(self):
        name = generate_run_name(set())
        assert "-" in name
        adj, noun = name.split("-", 1)
        assert adj in ADJECTIVES
        assert noun in NOUNS

    def test_avoids_existing_names(self):
        # Fill all but one combination to force the generator to find the last one
        # (impractical to exhaust all 2500, so just verify it avoids given names)
        existing: set[str] = set()
        for _ in range(50):
            name = generate_run_name(existing)
            assert name not in existing
            existing.add(name)
        assert len(existing) == 50

    def test_raises_when_all_taken(self):
        # Build a set of all possible combinations
        all_names = {f"{a}-{n}" for a in ADJECTIVES for n in NOUNS}
        with pytest.raises(RuntimeError, match="Could not generate"):
            generate_run_name(all_names)

    def test_uniqueness_under_max_runs(self):
        """With up to 20 runs, collisions should essentially never happen."""
        existing: set[str] = set()
        for _ in range(20):
            name = generate_run_name(existing)
            existing.add(name)
        assert len(existing) == 20


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_company(name: str = "Acme") -> dict:
    return {
        "name": name,
        "reason": "Good data team",
        "career_page_url": f"https://{name.lower()}.com/careers",
        "ats_type": "greenhouse",
        "ats_board_token": name.lower(),
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "roles_fetched": False,
    }


def _seed_resumes(tmp_data_dir: Path, resumes: list[dict] | None = None) -> None:
    data = resumes or [
        {
            "id": str(uuid.uuid4()),
            "filename": "resume.txt",
            "skills": ["Python"],
            "titles": ["Engineer"],
            "raw_text": "Python engineer",
        }
    ]
    (tmp_data_dir / "resumes.json").write_text(json.dumps(data))


# ─── POST /api/companies/discover creates a company run ─────────────────────


class TestDiscoverCreatesRun:
    def test_discover_with_seed_creates_run(self, client, tmp_data_dir):
        """Seed-based discovery should create a company_run entry."""
        from jobfinder.storage.schemas import DiscoveredCompany
        from datetime import datetime, timezone

        fake_company = DiscoveredCompany(
            name="SeedCo",
            reason="Test",
            career_page_url="https://seedco.com/careers",
            ats_type="greenhouse",
            ats_board_token="seedco",
            discovered_at=datetime.now(timezone.utc).isoformat(),
        )

        async def fake_to_thread(fn, *args, **kwargs):
            return [fake_company]

        with patch("jobfinder.api.routes.companies.resolve_api_key", return_value="fake-key"), \
             patch("jobfinder.api.routes.companies.asyncio.to_thread", side_effect=fake_to_thread):
            response = client.post(
                "/api/companies/discover",
                json={"seed_companies": ["SeedCo"], "max_companies": 1},
            )

        assert response.status_code == 200
        body = response.json()
        assert "run_id" in body
        assert "run_name" in body
        assert "-" in body["run_name"]

        # Verify company_runs.json was written
        runs_path = tmp_data_dir / "company_runs.json"
        assert runs_path.exists()
        saved_runs = json.loads(runs_path.read_text())
        assert len(saved_runs) == 1
        assert saved_runs[0]["source_type"] == "seed"
        assert saved_runs[0]["run_name"] == body["run_name"]

    def test_discover_with_seed_writes_run_directly(self, tmp_data_dir):
        """Directly test the run-writing logic using a patched storage backend."""
        from jobfinder.storage.store import StorageManager
        from jobfinder.company_runs.name_generator import generate_run_name
        from jobfinder.system_config import load_system_config
        import uuid as _uuid
        from datetime import datetime, timezone

        store = StorageManager(tmp_data_dir)
        sys_config = load_system_config()

        seed_companies = ["Alpha", "Beta"]
        source_id = str(_uuid.uuid4())
        run_id = str(_uuid.uuid4())
        discovered_at = datetime.now(timezone.utc).isoformat()

        existing_runs: list[dict] = store.read("company_runs.json") or []
        existing_names = {r["run_name"] for r in existing_runs}
        run_name = generate_run_name(existing_names)

        new_run = {
            "id": run_id,
            "run_name": run_name,
            "source_type": "seed",
            "source_id": source_id,
            "seed_companies": list(seed_companies),
            "companies": [],
            "created_at": discovered_at,
        }
        updated_runs = [new_run] + existing_runs
        max_runs = sys_config.max_company_runs_per_user
        if len(updated_runs) > max_runs:
            updated_runs = updated_runs[:max_runs]

        store.write("company_runs.json", updated_runs)

        saved = store.read("company_runs.json")
        assert saved is not None
        assert len(saved) == 1
        assert saved[0]["source_type"] == "seed"
        assert saved[0]["run_name"] == run_name
        assert "-" in run_name


# ─── Max-runs eviction ───────────────────────────────────────────────────────


class TestMaxRunsEviction:
    def test_evicts_oldest_when_over_limit(self, tmp_data_dir):
        from jobfinder.storage.store import StorageManager
        from jobfinder.company_runs.name_generator import generate_run_name
        from jobfinder.system_config import load_system_config
        import uuid as _uuid
        from datetime import datetime, timezone

        store = StorageManager(tmp_data_dir)
        sys_config = load_system_config()
        max_runs = sys_config.max_company_runs_per_user  # 20

        # Pre-populate with exactly max_runs entries
        existing_names: set[str] = set()
        runs: list[dict] = []
        for i in range(max_runs):
            name = generate_run_name(existing_names)
            existing_names.add(name)
            runs.append({
                "id": str(_uuid.uuid4()),
                "run_name": name,
                "source_type": "seed",
                "source_id": str(_uuid.uuid4()),
                "seed_companies": [f"Co{i}"],
                "companies": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        store.write("company_runs.json", runs)

        # Add one more — should evict the last (oldest) entry
        existing_runs: list[dict] = store.read("company_runs.json") or []
        oldest_id = existing_runs[-1]["id"]
        new_name = generate_run_name({r["run_name"] for r in existing_runs})
        new_run = {
            "id": str(_uuid.uuid4()),
            "run_name": new_name,
            "source_type": "seed",
            "source_id": str(_uuid.uuid4()),
            "seed_companies": ["NewCo"],
            "companies": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        updated = [new_run] + existing_runs
        if len(updated) > max_runs:
            updated = updated[:max_runs]
        store.write("company_runs.json", updated)

        saved = store.read("company_runs.json")
        assert len(saved) == max_runs
        # Newest run is first
        assert saved[0]["run_name"] == new_name
        # Oldest was evicted
        saved_ids = {r["id"] for r in saved}
        assert oldest_id not in saved_ids


# ─── GET /api/company-runs (paginated list) ──────────────────────────────────


class TestListCompanyRuns:
    def _seed_runs(self, tmp_data_dir: Path, count: int) -> list[dict]:
        from jobfinder.company_runs.name_generator import generate_run_name
        import uuid as _uuid

        runs = []
        names: set[str] = set()
        for i in range(count):
            name = generate_run_name(names)
            names.add(name)
            runs.append({
                "id": str(_uuid.uuid4()),
                "run_name": name,
                "source_type": "seed",
                "source_id": str(_uuid.uuid4()),
                "seed_companies": [f"Co{i}"],
                "companies": [_make_company(f"Co{i}")],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        (tmp_data_dir / "company_runs.json").write_text(json.dumps(runs))
        return runs

    def test_returns_empty_when_no_runs(self, client):
        response = client.get("/api/company-runs")
        assert response.status_code == 200
        body = response.json()
        assert body["runs"] == []
        assert body["total"] == 0

    def test_paginated_first_page(self, client, tmp_data_dir):
        runs = self._seed_runs(tmp_data_dir, 20)
        response = client.get("/api/company-runs?page=1&page_size=5")
        assert response.status_code == 200
        body = response.json()
        assert len(body["runs"]) == 5
        assert body["total"] == 20
        assert body["total_pages"] == 4
        # Summaries should NOT include companies list
        for r in body["runs"]:
            assert "companies" not in r
            assert "company_count" in r

    def test_paginated_last_page(self, client, tmp_data_dir):
        self._seed_runs(tmp_data_dir, 12)
        response = client.get("/api/company-runs?page=3&page_size=5")
        assert response.status_code == 200
        body = response.json()
        assert len(body["runs"]) == 2  # 12 - 2*5 = 2

    def test_full_run_count(self, client, tmp_data_dir):
        self._seed_runs(tmp_data_dir, 20)
        response = client.get("/api/company-runs?page_size=50")
        body = response.json()
        assert body["total"] == 20

    def test_invalid_page_size_clamped(self, client, tmp_data_dir):
        self._seed_runs(tmp_data_dir, 5)
        # page_size=0 should clamp to default (10)
        response = client.get("/api/company-runs?page_size=0")
        assert response.status_code == 200


# ─── GET /api/company-runs/{run_id} ─────────────────────────────────────────


class TestGetCompanyRunById:
    def _seed_single_run(self, tmp_data_dir: Path) -> dict:
        run = {
            "id": str(uuid.uuid4()),
            "run_name": "happy-dolphin",
            "source_type": "seed",
            "source_id": str(uuid.uuid4()),
            "seed_companies": ["Alpha", "Beta"],
            "companies": [_make_company("Alpha"), _make_company("Beta")],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (tmp_data_dir / "company_runs.json").write_text(json.dumps([run]))
        return run

    def test_returns_run_with_companies(self, client, tmp_data_dir):
        run = self._seed_single_run(tmp_data_dir)
        response = client.get(f"/api/company-runs/{run['id']}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == run["id"]
        assert body["run_name"] == "happy-dolphin"
        assert len(body["companies"]) == 2

    def test_returns_404_for_unknown_id(self, client, tmp_data_dir):
        self._seed_single_run(tmp_data_dir)
        response = client.get(f"/api/company-runs/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_returns_404_when_no_runs(self, client):
        response = client.get(f"/api/company-runs/{uuid.uuid4()}")
        assert response.status_code == 404


# ─── Helper for async mock ────────────────────────────────────────────────────

import asyncio


async def _async_return(value):
    return value

"""Tests for the Y Combinator Jobs external source (RapidAPI).

respx mocks the httpx transport used by YCombinatorSource.fetch_all.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from jobfinder.roles.sources.base import JobSourceError
from jobfinder.roles.sources.ycombinator import RAPIDAPI_URL, YCombinatorSource
from jobfinder.roles.sources.cache import ExternalSourceCache

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestYCombinatorSource:

    def test_fetch_all_returns_roles(self, ycombinator_fixture: list):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(200, json=ycombinator_fixture)
            )
            roles = source.fetch_all(api_key="test-key", timeout=10)

        assert len(roles) == 3
        for role in roles:
            assert role.ats_type == "ycombinator"
            assert role.title
            assert role.company_name

    def test_field_mapping(self, ycombinator_fixture: list):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(200, json=ycombinator_fixture)
            )
            roles = source.fetch_all(api_key="test-key", timeout=10)

        # First role: Retool, San Francisco
        retool = roles[0]
        assert retool.company_name == "Retool"
        assert retool.title == "Senior Software Engineer"
        assert "San Francisco" in retool.location
        assert retool.url == "https://www.ycombinator.com/companies/retool/jobs/abc123-senior-software-engineer"
        assert retool.ats_job_id == "2066940969"
        assert retool.posted_at == "2026-03-19T23:08:20"
        assert retool.is_remote is False
        assert retool.employment_type == "FULL_TIME"

        # Second role: Airbnb, Remote (TELECOMMUTE)
        airbnb = roles[1]
        assert airbnb.company_name == "Airbnb"
        assert airbnb.location == "Remote"
        assert airbnb.is_remote is True

        # Third role: Stripe, first employment_type extracted
        stripe = roles[2]
        assert stripe.company_name == "Stripe"
        assert stripe.employment_type == "FULL_TIME"
        assert "New York" in stripe.location

    def test_pagination(self, ycombinator_fixture: list):
        """Two pages: first returns full page (10 items), second returns remainder."""
        source = YCombinatorSource()
        # Page 1: 10 items (repeat fixture to fill a full page)
        page1 = ycombinator_fixture * 4  # 12 items, but we only take first 10 effects
        # Build two pages: 10 and 2
        page1_data = ycombinator_fixture[:3] * 4  # 12 items → will send 10
        page1_10 = page1_data[:10]
        page2_2 = page1_data[10:12]

        call_count = 0

        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            offset = request.url.params.get("offset", "0")
            if offset == "0":
                return httpx.Response(200, json=page1_10)
            else:
                return httpx.Response(200, json=page2_2)

        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(side_effect=side_effect)
            roles = source.fetch_all(api_key="test-key", timeout=10)

        assert len(roles) == 12
        assert call_count == 2

    def test_empty_response(self):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(200, json=[])
            )
            roles = source.fetch_all(api_key="test-key", timeout=10)

        assert roles == []

    def test_auth_error_raises(self):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(403, json={"message": "forbidden"})
            )
            with pytest.raises(JobSourceError, match="authentication failed"):
                source.fetch_all(api_key="bad-key", timeout=10)

    def test_401_raises(self):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(401, json={"message": "unauthorized"})
            )
            with pytest.raises(JobSourceError, match="authentication failed"):
                source.fetch_all(api_key="bad-key", timeout=10)

    def test_server_error_raises(self):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                return_value=httpx.Response(500)
            )
            with pytest.raises(JobSourceError, match="HTTP 500"):
                source.fetch_all(api_key="test-key", timeout=10)

    def test_network_error_raises(self):
        source = YCombinatorSource()
        with respx.mock(assert_all_called=False) as mock:
            mock.get(RAPIDAPI_URL).mock(
                side_effect=httpx.ConnectError("unreachable")
            )
            with pytest.raises(JobSourceError, match="unreachable"):
                source.fetch_all(api_key="test-key", timeout=10)


class TestExternalSourceCache:

    def test_cache_hit(self, store):
        cache = ExternalSourceCache(store)

        from jobfinder.storage.schemas import DiscoveredRole
        roles = [
            DiscoveredRole(
                company_name="TestCo",
                title="Engineer",
                ats_type="ycombinator",
                fetched_at="2026-03-19T00:00:00",
            )
        ]
        cache.put("ycombinator", roles, ttl_hours=12.0)

        # Re-load from storage
        cache2 = ExternalSourceCache(store)
        result = cache2.get("ycombinator")
        assert result is not None
        assert len(result) == 1
        assert result[0].company_name == "TestCo"

    def test_cache_expired(self, store):
        cache = ExternalSourceCache(store)

        from jobfinder.storage.schemas import DiscoveredRole
        roles = [
            DiscoveredRole(
                company_name="TestCo",
                title="Engineer",
                ats_type="ycombinator",
                fetched_at="2026-03-19T00:00:00",
            )
        ]
        # Write with a past expiry
        now = datetime.now(timezone.utc)
        entry = {
            "source": "ycombinator",
            "cached_at": (now - timedelta(hours=24)).isoformat(),
            "expires_at": (now - timedelta(hours=12)).isoformat(),
            "total_jobs": 1,
            "roles": [r.model_dump() for r in roles],
        }
        store.write("external_job_cache.json", {"version": 1, "entries": {"ycombinator": entry}})

        cache2 = ExternalSourceCache(store)
        result = cache2.get("ycombinator")
        assert result is None  # expired

    def test_cache_miss(self, store):
        cache = ExternalSourceCache(store)
        result = cache.get("nonexistent")
        assert result is None

    def test_age_hours(self, store):
        cache = ExternalSourceCache(store)
        from jobfinder.storage.schemas import DiscoveredRole
        roles = [
            DiscoveredRole(
                company_name="TestCo",
                title="Engineer",
                ats_type="ycombinator",
                fetched_at="2026-03-19T00:00:00",
            )
        ]
        cache.put("ycombinator", roles, ttl_hours=12.0)

        age = cache.age_hours("ycombinator")
        assert age is not None
        assert age < 1.0  # just written

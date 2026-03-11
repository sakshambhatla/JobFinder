"""Tests for Greenhouse, Lever, and Ashby ATS fetchers with mocked HTTP.

respx mocks the httpx transport used by jobfinder.utils.http.get_json.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from jobfinder.roles.ats.base import ATSFetchError
from jobfinder.roles.ats.greenhouse import GreenhouseFetcher
from jobfinder.roles.ats.lever import LeverFetcher
from jobfinder.roles.ats.ashby import AshbyFetcher
from jobfinder.storage.schemas import DiscoveredCompany

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_company(name: str, token: str, ats_type: str = "greenhouse") -> DiscoveredCompany:
    return DiscoveredCompany(
        name=name,
        reason="test",
        career_page_url=f"https://{name.lower()}.com/careers",
        ats_type=ats_type,
        ats_board_token=token,
    )


# ── Greenhouse ──────────────────────────────────────────────────────────────────

class TestGreenhouseFetcher:
    def test_returns_roles(self, greenhouse_fixture: dict):
        company = _make_company("Anthropic", "anthropic")
        fetcher = GreenhouseFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs"
            ).mock(return_value=httpx.Response(200, json=greenhouse_fixture))

            roles = fetcher.fetch(company, timeout=10)

        assert len(roles) > 0
        # All roles must have required fields
        for role in roles:
            assert role.company_name == "Anthropic"
            assert role.ats_type == "greenhouse"
            assert role.title  # non-empty

    def test_url_populated(self, greenhouse_fixture: dict):
        company = _make_company("Anthropic", "anthropic")
        fetcher = GreenhouseFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs"
            ).mock(return_value=httpx.Response(200, json=greenhouse_fixture))
            roles = fetcher.fetch(company, timeout=10)

        # At least some roles should have a URL
        urls = [r.url for r in roles if r.url]
        assert len(urls) > 0

    def test_404_raises_ats_fetch_error(self):
        company = _make_company("BadCo", "badco")
        fetcher = GreenhouseFetcher()

        with respx.mock() as mock:
            mock.get(
                "https://boards-api.greenhouse.io/v1/boards/badco/jobs"
            ).mock(return_value=httpx.Response(404))

            with pytest.raises(ATSFetchError):
                fetcher.fetch(company, timeout=10)

    def test_network_error_raises_ats_fetch_error(self):
        company = _make_company("BadCo", "badco")
        fetcher = GreenhouseFetcher()

        with respx.mock() as mock:
            mock.get(
                "https://boards-api.greenhouse.io/v1/boards/badco/jobs"
            ).mock(side_effect=httpx.ConnectError("unreachable"))

            with pytest.raises(ATSFetchError):
                fetcher.fetch(company, timeout=10)

    def test_missing_token_raises(self):
        company = _make_company("NoCo", "", "greenhouse")
        company = DiscoveredCompany(
            name="NoCo",
            reason="test",
            career_page_url="https://noco.com",
            ats_type="greenhouse",
            ats_board_token=None,
        )
        fetcher = GreenhouseFetcher()
        with pytest.raises(ATSFetchError):
            fetcher.fetch(company, timeout=10)


# ── Lever ───────────────────────────────────────────────────────────────────────

class TestLeverFetcher:
    def test_returns_roles(self, lever_fixture: list):
        company = _make_company("Acme", "acme", "lever")
        fetcher = LeverFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.lever.co/v0/postings/acme"
            ).mock(return_value=httpx.Response(200, json=lever_fixture))

            roles = fetcher.fetch(company, timeout=10)

        assert len(roles) == 2
        assert roles[0].title == "Senior Software Engineer"
        assert roles[0].ats_type == "lever"

    def test_location_from_categories(self, lever_fixture: list):
        company = _make_company("Acme", "acme", "lever")
        fetcher = LeverFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.lever.co/v0/postings/acme"
            ).mock(return_value=httpx.Response(200, json=lever_fixture))
            roles = fetcher.fetch(company, timeout=10)

        assert roles[0].location == "San Francisco, CA"
        assert roles[1].location == "Remote"

    def test_url_populated(self, lever_fixture: list):
        company = _make_company("Acme", "acme", "lever")
        fetcher = LeverFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.lever.co/v0/postings/acme"
            ).mock(return_value=httpx.Response(200, json=lever_fixture))
            roles = fetcher.fetch(company, timeout=10)

        for role in roles:
            assert role.url.startswith("https://jobs.lever.co/")

    def test_404_raises_ats_fetch_error(self):
        company = _make_company("BadCo", "badco", "lever")
        fetcher = LeverFetcher()

        with respx.mock() as mock:
            mock.get(
                "https://api.lever.co/v0/postings/badco"
            ).mock(return_value=httpx.Response(404))

            with pytest.raises(ATSFetchError):
                fetcher.fetch(company, timeout=10)

    def test_non_list_response_returns_empty(self):
        company = _make_company("Acme", "acme", "lever")
        fetcher = LeverFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.lever.co/v0/postings/acme"
            ).mock(return_value=httpx.Response(200, json={"error": "bad"}))
            roles = fetcher.fetch(company, timeout=10)

        assert roles == []


# ── Ashby ───────────────────────────────────────────────────────────────────────

class TestAshbyFetcher:
    def test_returns_roles(self, ashby_fixture: dict):
        company = _make_company("Cursor", "cursor", "ashby")
        fetcher = AshbyFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.ashbyhq.com/posting-api/job-board/cursor"
            ).mock(return_value=httpx.Response(200, json=ashby_fixture))

            roles = fetcher.fetch(company, timeout=10)

        assert len(roles) > 0
        for role in roles:
            assert role.company_name == "Cursor"
            assert role.ats_type == "ashby"

    def test_url_populated(self, ashby_fixture: dict):
        company = _make_company("Cursor", "cursor", "ashby")
        fetcher = AshbyFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.ashbyhq.com/posting-api/job-board/cursor"
            ).mock(return_value=httpx.Response(200, json=ashby_fixture))
            roles = fetcher.fetch(company, timeout=10)

        urls = [r.url for r in roles if r.url]
        assert len(urls) > 0

    def test_404_raises_ats_fetch_error(self):
        company = _make_company("BadCo", "badco", "ashby")
        fetcher = AshbyFetcher()

        with respx.mock() as mock:
            mock.get(
                "https://api.ashbyhq.com/posting-api/job-board/badco"
            ).mock(return_value=httpx.Response(404))

            with pytest.raises(ATSFetchError):
                fetcher.fetch(company, timeout=10)

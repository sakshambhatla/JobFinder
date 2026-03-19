"""API profile storage — remembers discovered career-page endpoints keyed by domain.

Profiles are persisted in ``data/api_profiles.json`` and linked to companies via the
domain of their ``career_page_url``.  When the browser agent runs for a company whose
domain already has a profile, the known endpoint is injected into the task prompt so the
agent skips re-discovery and goes straight to extraction.

Schema (one entry per domain)::

    {
      "explore.jobs.netflix.net": {
        "platform": "Eightfold AI",
        "discovered_at": "2026-03-10T...",
        "companies": ["Netflix"],
        "endpoints": [{
          "method": "POST",
          "path": "/api/apply/v2/jobs",
          "body_template": {"domain": "netflix.com", "num_rec": 100, "offset": 0},
          "csrf_selector": "meta[name='_csrf']",
          "rate_limit_rpm_observed": 3,
          "batch_size": 100
        }]
      }
    }
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from jobfinder.storage.backend import StorageBackend

_FILENAME = "api_profiles.json"
log = logging.getLogger(__name__)


def _domain_key(url: str) -> str:
    """Return the netloc (host) of *url*, used as the profile dict key.

    >>> _domain_key("https://explore.jobs.netflix.net/careers")
    'explore.jobs.netflix.net'
    """
    return urlparse(url).netloc


def _validate_profile_domain(career_page_url: str, profile: dict) -> bool:
    """Check that endpoint paths are relative or same-domain.

    Rejects profiles containing absolute URLs that point to a different domain
    than *career_page_url* — prevents a poisoning attack where a malicious
    profile redirects browser agents to an attacker-controlled URL.
    """
    expected = _domain_key(career_page_url)
    if not expected:
        return False
    for ep in profile.get("endpoints", []):
        path = ep.get("path", "")
        if path.startswith("http://") or path.startswith("https://"):
            if _domain_key(path) != expected:
                return False
    return True


def load_profile(career_page_url: str, store: StorageBackend) -> dict | None:
    """Return the stored API profile for the domain of *career_page_url*, or None."""
    profiles: dict = store.read(_FILENAME) or {}
    return profiles.get(_domain_key(career_page_url))


def save_profile(
    career_page_url: str,
    company_name: str,
    profile: dict,
    store: StorageBackend,
) -> None:
    """Upsert *profile* for the domain of *career_page_url*.

    Merges new data on top of any existing entry; always keeps the full set of
    associated company names (deduped).  Rejects profiles with endpoints
    pointing to foreign domains.
    """
    if not _validate_profile_domain(career_page_url, profile):
        log.warning(
            "Rejected api_profile for %s (%s): endpoint domain mismatch",
            company_name,
            career_page_url,
        )
        return
    key = _domain_key(career_page_url)
    profiles: dict = store.read(_FILENAME) or {}
    existing = profiles.get(key, {})
    companies = list(set(existing.get("companies", []) + [company_name]))
    profiles[key] = {**existing, **profile, "companies": companies}
    store.write(_FILENAME, profiles)


def all_profiles(store: StorageBackend) -> dict:
    """Return the full api_profiles dict (keyed by domain)."""
    return store.read(_FILENAME) or {}

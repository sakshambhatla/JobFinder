"""Y Combinator Jobs source via the free RapidAPI endpoint.

Returns jobs posted to the YC job board in the last 7 days.
The API refreshes 2x per day; each call returns 10 jobs paginated via ``offset``.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from jobfinder.roles.sources.base import BaseJobSource, JobSourceError
from jobfinder.storage.schemas import DiscoveredRole

RAPIDAPI_HOST = "free-y-combinator-jobs-api.p.rapidapi.com"
RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/active-jb-7d"
PAGE_SIZE = 10
MAX_ROLES = 1000  # Safety cap: stop paginating after this many roles


class YCombinatorSource(BaseJobSource):

    @property
    def name(self) -> str:
        return "Y Combinator Jobs"

    @property
    def cache_ttl_hours(self) -> float:
        return 12.0  # API refreshes 2x/day

    def fetch_all(
        self,
        *,
        api_key: str,
        timeout: int = 30,
    ) -> list[DiscoveredRole]:
        headers = {
            "X-Rapidapi-Key": api_key,
            "X-Rapidapi-Host": RAPIDAPI_HOST,
            "Content-Type": "application/json",
        }
        all_roles: list[DiscoveredRole] = []
        offset = 0
        now = datetime.now(timezone.utc).isoformat()

        while True:
            params: dict[str, str] = {}
            if offset > 0:
                params["offset"] = str(offset)

            try:
                response = httpx.get(
                    RAPIDAPI_URL,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                )
                if response.status_code in (401, 403):
                    raise JobSourceError(
                        f"RapidAPI authentication failed (HTTP {response.status_code}). "
                        "Check your RAPIDAPI_KEY."
                    )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise JobSourceError(
                    f"YC Jobs API returned HTTP {exc.response.status_code}"
                ) from exc
            except httpx.TransportError as exc:
                raise JobSourceError(
                    f"YC Jobs API unreachable: {exc}"
                ) from exc

            jobs = response.json()
            if not isinstance(jobs, list) or not jobs:
                break

            for job in jobs:
                role = _map_job(job, now)
                all_roles.append(role)

            offset += PAGE_SIZE
            if len(jobs) < PAGE_SIZE or len(all_roles) >= MAX_ROLES:
                break

        return all_roles


def _map_job(job: dict, fetched_at: str) -> DiscoveredRole:
    """Map a YC Jobs API response object to a DiscoveredRole."""
    # Location: prefer derived locations, fall back to raw
    location = "Unknown"
    locations_derived = job.get("locations_derived")
    if locations_derived and isinstance(locations_derived, list):
        location = ", ".join(locations_derived)
    elif job.get("location_type") == "TELECOMMUTE":
        location = "Remote"

    # Employment type: API returns a list like ["FULL_TIME"]
    employment_type = None
    emp_raw = job.get("employment_type")
    if isinstance(emp_raw, list) and emp_raw:
        employment_type = emp_raw[0]

    return DiscoveredRole(
        company_name=job.get("organization", "Unknown"),
        title=job.get("title", "Untitled"),
        location=location,
        url=job.get("url", ""),
        ats_type="ycombinator",
        ats_job_id=str(job.get("id", "")),
        posted_at=job.get("date_posted"),
        is_remote=job.get("remote_derived"),
        employment_type=employment_type,
        workplace_type=job.get("location_type"),
        fetched_at=fetched_at,
    )

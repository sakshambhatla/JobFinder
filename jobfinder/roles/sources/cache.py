"""Cache for external job board sources with per-source TTL.

Separate from the per-company RolesCache (roles/cache.py) because external
sources return roles across many companies in a single call.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from jobfinder.storage.backend import StorageBackend
from jobfinder.storage.schemas import DiscoveredRole, ExternalJobCacheEntry

CACHE_FILENAME = "external_job_cache.json"


class ExternalSourceCache:
    """Read/write cache for external job source results."""

    def __init__(self, store: StorageBackend) -> None:
        self._store = store
        raw = store.read(CACHE_FILENAME)
        if isinstance(raw, dict):
            self._entries: dict[str, dict] = raw.get("entries", {})
        else:
            self._entries = {}

    def get(self, source: str) -> list[DiscoveredRole] | None:
        """Return cached roles if within TTL, else None."""
        entry = self._entries.get(source)
        if entry is None:
            return None

        expires_at = entry.get("expires_at", "")
        if not expires_at:
            return None

        try:
            expiry = datetime.fromisoformat(expires_at)
        except (ValueError, TypeError):
            return None

        now = datetime.now(timezone.utc)
        if now >= expiry:
            return None  # expired

        roles_raw = entry.get("roles", [])
        return [DiscoveredRole.model_validate(r) for r in roles_raw]

    def age_hours(self, source: str) -> float | None:
        """Return hours since cache was written, or None if not cached."""
        entry = self._entries.get(source)
        if entry is None:
            return None
        cached_at = entry.get("cached_at", "")
        if not cached_at:
            return None
        try:
            ts = datetime.fromisoformat(cached_at)
        except (ValueError, TypeError):
            return None
        return (datetime.now(timezone.utc) - ts).total_seconds() / 3600

    def put(self, source: str, roles: list[DiscoveredRole], ttl_hours: float) -> None:
        """Write cache entry with explicit TTL."""
        now = datetime.now(timezone.utc)
        entry = ExternalJobCacheEntry(
            source=source,
            cached_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
            total_jobs=len(roles),
            roles=roles,
        )
        self._entries[source] = entry.model_dump()
        self._flush()

    def _flush(self) -> None:
        self._store.write(CACHE_FILENAME, {"version": 1, "entries": self._entries})

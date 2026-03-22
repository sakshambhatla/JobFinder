from __future__ import annotations

from abc import ABC, abstractmethod

from jobfinder.storage.schemas import DiscoveredRole


class JobSourceError(Exception):
    """Raised when fetching from an external job source fails."""


class BaseJobSource(ABC):
    """Abstract base for external job board sources (e.g. YC Jobs via RapidAPI).

    Unlike ATS fetchers (per-company), job sources return roles across many
    companies in a single call.
    """

    @abstractmethod
    def fetch_all(
        self,
        *,
        api_key: str,
        timeout: int = 30,
    ) -> list[DiscoveredRole]:
        """Fetch all available jobs from this source."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable source name for logging."""
        ...

    @property
    @abstractmethod
    def cache_ttl_hours(self) -> float:
        """How long cached results should be considered fresh."""
        ...

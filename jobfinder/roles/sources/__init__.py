"""External job board sources — aggregator APIs that return roles across companies.

Registry pattern mirrors ``ats/__init__.py``.  Each source is keyed by a short
name (e.g. ``"ycombinator"``) and controlled by a config flag.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jobfinder.roles.sources.base import BaseJobSource
from jobfinder.roles.sources.ycombinator import YCombinatorSource

if TYPE_CHECKING:
    from jobfinder.config import AppConfig

_REGISTRY: dict[str, BaseJobSource] = {
    "ycombinator": YCombinatorSource(),
}


def get_source(name: str) -> BaseJobSource | None:
    """Look up a job source by name."""
    return _REGISTRY.get(name)


def get_enabled_sources(config: AppConfig) -> list[tuple[str, BaseJobSource]]:
    """Return ``(name, source)`` pairs for sources enabled in *config*."""
    enabled: list[tuple[str, BaseJobSource]] = []
    if config.enable_yc_jobs:
        src = _REGISTRY.get("ycombinator")
        if src:
            enabled.append(("ycombinator", src))
    return enabled

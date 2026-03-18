"""System-level configuration — not editable by end users.

These values govern platform limits and operational constraints.
Read from ``system_config.json`` in the working directory (if present),
falling back to hard-coded defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class SystemConfig(BaseModel):
    # Maximum number of company-discovery runs stored per user.
    # Oldest runs are evicted when this limit is exceeded.
    max_company_runs_per_user: int = 20


_cached: SystemConfig | None = None


def load_system_config(config_path: str | None = None) -> SystemConfig:
    """Load system config, caching for the lifetime of the process."""
    global _cached
    if _cached is not None:
        return _cached

    resolved = config_path or "system_config.json"
    values: dict = {}
    if Path(resolved).exists():
        with open(resolved) as f:
            values = json.load(f)

    _cached = SystemConfig(**values)
    return _cached

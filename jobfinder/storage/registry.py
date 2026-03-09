from __future__ import annotations

from datetime import datetime, timezone

from jobfinder.storage.schemas import DiscoveredCompany
from jobfinder.storage.store import StorageManager

REGISTRY_FILENAME = "company_registry.json"


def load_or_bootstrap_registry(store: StorageManager) -> list[dict]:
    """Return registry entries, seeding from companies.json on first run."""
    if store.exists(REGISTRY_FILENAME):
        return (store.read(REGISTRY_FILENAME) or {}).get("companies", [])
    # First-run bootstrap: seed from the last discover-companies result
    data = store.read("companies.json") or {}
    entries = [
        {
            "name": c["name"],
            "ats_type": c.get("ats_type", "unknown"),
            "ats_board_token": c.get("ats_board_token"),
            "career_page_url": c.get("career_page_url", ""),
        }
        for c in data.get("companies", [])
    ]
    store.write(
        REGISTRY_FILENAME,
        {"updated_at": datetime.now(timezone.utc).isoformat(), "companies": entries},
    )
    return entries


def upsert_registry(store: StorageManager, new_companies: list[DiscoveredCompany]) -> None:
    """Merge *new_companies* into the registry (new entry wins; registry never shrinks)."""
    existing = (store.read(REGISTRY_FILENAME) or {}).get("companies", [])
    seen: dict[str, dict] = {e["name"].lower(): e for e in existing}
    for c in new_companies:
        seen[c.name.lower()] = {
            "name": c.name,
            "ats_type": c.ats_type,
            "ats_board_token": c.ats_board_token,
            "career_page_url": c.career_page_url,
        }
    store.write(
        REGISTRY_FILENAME,
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "companies": list(seen.values()),
        },
    )

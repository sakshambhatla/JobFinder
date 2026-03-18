from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from jobfinder.api.auth import get_current_user
from jobfinder.storage import get_storage_backend

router = APIRouter()

_DEFAULT_PAGE_SIZE = 10


@router.get("/company-runs")
async def list_company_runs(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    user_id: str | None = Depends(get_current_user),
) -> dict:
    """Return a paginated list of company runs (newest first)."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = _DEFAULT_PAGE_SIZE

    store = get_storage_backend(user_id)
    all_runs: list[dict] = store.read("company_runs.json") or []

    total = len(all_runs)
    start = (page - 1) * page_size
    end = start + page_size
    page_runs = all_runs[start:end]

    # Return runs without the full companies list (summary view)
    summaries = [
        {
            "id": r["id"],
            "run_name": r["run_name"],
            "source_type": r["source_type"],
            "source_id": r["source_id"],
            "company_count": len(r.get("companies", [])),
            "created_at": r["created_at"],
        }
        for r in page_runs
    ]

    return {
        "runs": summaries,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/company-runs/{run_id}")
async def get_company_run(
    run_id: str,
    user_id: str | None = Depends(get_current_user),
) -> dict:
    """Return a single company run including its full companies list."""
    store = get_storage_backend(user_id)
    all_runs: list[dict] = store.read("company_runs.json") or []

    for run in all_runs:
        if run.get("id") == run_id:
            return run

    raise HTTPException(status_code=404, detail=f"Company run '{run_id}' not found.")

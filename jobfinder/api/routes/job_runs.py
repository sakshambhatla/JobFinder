from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from jobfinder.api.auth import get_current_user
from jobfinder.storage import get_storage_backend
from jobfinder.utils.log_stream import get_logs_for_run

router = APIRouter()

_DEFAULT_PAGE_SIZE = 10


@router.get("/job-runs")
async def list_job_runs(
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Return a paginated list of job runs (newest first).

    Summary view — ``metrics`` is included but ``log_entries`` are omitted
    for performance (logs can be large).
    """
    user_id, jwt_token = _auth if _auth else (None, None)

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = _DEFAULT_PAGE_SIZE

    store = get_storage_backend(user_id, jwt_token)
    all_runs: list[dict] = store.read("job_runs.json") or []

    total = len(all_runs)
    start = (page - 1) * page_size
    end = start + page_size
    page_runs = all_runs[start:end]

    summaries = [
        {
            "id": r["id"],
            "run_name": r.get("run_name", ""),
            "company_run_id": r.get("company_run_id"),
            "parent_job_run_id": r.get("parent_job_run_id"),
            "run_type": r.get("run_type", "api"),
            "status": r.get("status", "completed"),
            "companies_input": r.get("companies_input", []),
            "metrics": r.get("metrics", {}),
            "created_at": r.get("created_at", ""),
            "completed_at": r.get("completed_at"),
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


@router.get("/job-runs/{run_id}")
async def get_job_run(
    run_id: str,
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Return a single job run including metrics and buffered log entries."""
    user_id, jwt_token = _auth if _auth else (None, None)
    store = get_storage_backend(user_id, jwt_token)
    all_runs: list[dict] = store.read("job_runs.json") or []

    for run in all_runs:
        if run.get("id") == run_id:
            # Attach live log entries from the ring buffer (if still available)
            run["log_entries"] = get_logs_for_run(run_id)
            return run

    raise HTTPException(status_code=404, detail=f"Job run '{run_id}' not found.")

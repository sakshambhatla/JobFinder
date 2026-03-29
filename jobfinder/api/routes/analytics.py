from __future__ import annotations

import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from jobfinder.api.auth import get_current_user, get_optional_user
from jobfinder.api.models import PageViewRequest
from jobfinder.api.rbac import require_role_minimum

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/pageview")
async def record_pageview(
    req: PageViewRequest,
    _auth: tuple[str, str] | None = Depends(get_optional_user),
) -> dict:
    """Record a page view. Best-effort — never fails the request."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        return {"status": "ok"}

    user_id = _auth[0] if _auth else None

    row = {
        "session_id": req.session_id[:100],
        "page_path": req.page_path[:500],
        "referrer": req.referrer[:2000] if req.referrer else None,
        "user_agent": req.user_agent[:1000] if req.user_agent else None,
        "screen_width": req.screen_width,
        "screen_height": req.screen_height,
    }
    if user_id:
        row["user_id"] = user_id

    try:
        from supabase import create_client

        client = create_client(supabase_url, supabase_key)
        client.table("page_views").insert(row).execute()
    except Exception:
        logger.exception("Failed to record page view")

    return {"status": "ok"}


@router.get("/summary")
async def analytics_summary(
    days: int = Query(default=30, ge=1, le=90),
    _auth: tuple[str, str] | None = Depends(get_current_user),
    _role_check: str = Depends(require_role_minimum("devtest")),
) -> dict:
    """Aggregated analytics summary. Requires devtest+ role."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        return _empty_summary(days)

    from supabase import create_client

    client = create_client(supabase_url, supabase_key)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    resp = (
        client.table("page_views")
        .select("user_id, session_id, page_path, referrer, created_at")
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(10000)
        .execute()
    )

    rows = resp.data or []

    # Aggregate
    sessions: set[str] = set()
    users: set[str] = set()
    page_counter: Counter[str] = Counter()
    referrer_counter: Counter[str] = Counter()
    day_counter: Counter[str] = Counter()

    for r in rows:
        sessions.add(r["session_id"])
        if r.get("user_id"):
            users.add(r["user_id"])
        page_counter[r["page_path"]] += 1
        if r.get("referrer"):
            referrer_counter[r["referrer"]] += 1
        day_str = r["created_at"][:10]  # YYYY-MM-DD
        day_counter[day_str] += 1

    # Build views_over_time sorted by date
    views_over_time = sorted(
        [{"date": d, "views": c} for d, c in day_counter.items()],
        key=lambda x: x["date"],
    )

    return {
        "days": days,
        "total_views": len(rows),
        "unique_sessions": len(sessions),
        "unique_users": len(users),
        "views_per_page": [
            {"page": p, "views": c} for p, c in page_counter.most_common(20)
        ],
        "top_referrers": [
            {"referrer": r, "count": c} for r, c in referrer_counter.most_common(10)
        ],
        "views_over_time": views_over_time,
    }


def _empty_summary(days: int) -> dict:
    return {
        "days": days,
        "total_views": 0,
        "unique_sessions": 0,
        "unique_users": 0,
        "views_per_page": [],
        "top_referrers": [],
        "views_over_time": [],
    }

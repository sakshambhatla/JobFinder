from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

router = APIRouter()

NOTIFY_EMAIL = "lithodoralabs@gmail.com"


class WaitlistRequest(BaseModel):
    email: EmailStr


@router.post("/waitlist")
async def join_waitlist(req: WaitlistRequest) -> dict:
    """Add an email to the waitlist and send a notification."""
    email = req.email.lower().strip()

    # Store in Supabase if configured
    stored = await _store_email(email)
    if stored == "duplicate":
        return {"status": "duplicate", "message": "Already on the waitlist"}

    # Send notification (best-effort — don't fail the request)
    try:
        await _send_notification(email)
    except Exception:
        logger.exception("Failed to send waitlist notification for %s", email)

    return {"status": "ok", "message": "Added to waitlist"}


async def _store_email(email: str) -> str:
    """Insert into waitlist table. Returns 'ok' or 'duplicate'."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        logger.info("Supabase not configured — skipping waitlist storage for %s", email)
        return "ok"

    try:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        client.table("waitlist").insert({"email": email}).execute()
        return "ok"
    except Exception as exc:
        # Unique constraint violation → duplicate
        if "duplicate" in str(exc).lower() or "23505" in str(exc):
            return "duplicate"
        logger.exception("Failed to store waitlist email %s", email)
        raise HTTPException(status_code=500, detail="Failed to save email") from exc


async def _send_notification(email: str) -> None:
    """Send a notification email via Resend."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.info("RESEND_API_KEY not set — skipping notification email")
        return

    import resend
    resend.api_key = api_key

    resend.Emails.send({
        "from": "Verdant AI <onboarding@resend.dev>",
        "to": [NOTIFY_EMAIL],
        "subject": f"New Waitlist Signup: {email}",
        "text": f"New waitlist signup from: {email}\n\nThis person has expressed interest in Verdant AI.",
    })
    logger.info("Sent waitlist notification for %s", email)

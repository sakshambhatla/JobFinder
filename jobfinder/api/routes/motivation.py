"""API routes for the motivation chat feature.

Endpoints:
  POST /api/motivation/chat   — send a message, get LLM reply
  GET  /api/motivation        — get current motivation (chat history + summary)
  DELETE /api/motivation      — reset/delete current motivation
  POST /api/motivation/finalize — force-generate summary from existing conversation
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from jobfinder.api.auth import get_current_user
from jobfinder.api.models import MotivationChatRequest
from jobfinder.config import load_config, resolve_api_key
from jobfinder.motivation.chat import generate_summary, motivation_chat_turn
from jobfinder.storage import get_storage_backend

router = APIRouter()


def _load_motivation(store) -> dict | None:
    """Load the user's current motivation from storage."""
    try:
        return store.read("user_motivation.json")
    except Exception:
        return None  # Table may not exist yet


def _save_motivation(store, motivation: dict) -> None:
    """Save the user's motivation to storage."""
    motivation["updated_at"] = datetime.now(timezone.utc).isoformat()
    store.write("user_motivation.json", motivation)


@router.post("/motivation/chat")
async def motivation_chat_endpoint(
    req: MotivationChatRequest,
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Process one turn of the motivation chat."""
    user_id, jwt_token = _auth if _auth else (None, None)
    store = get_storage_backend(user_id, jwt_token)

    overrides: dict = {}
    if req.model_provider is not None:
        overrides["model_provider"] = req.model_provider
    config = load_config(**overrides)

    try:
        api_key = resolve_api_key(config.model_provider, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Load or create motivation
    motivation = _load_motivation(store)
    if motivation is None:
        motivation = {
            "resume_id": req.resume_id,
            "chat_history": [],
            "summary": "",
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": "",
        }

    if motivation.get("status") == "completed":
        raise HTTPException(
            status_code=400,
            detail="Motivation already completed. Delete it first to start a new chat.",
        )

    # Append user message
    motivation["chat_history"].append({"role": "user", "content": req.message})

    # Optionally load resume for context
    resume_summary: str | None = None
    resume_id = req.resume_id or motivation.get("resume_id")
    if resume_id:
        all_resumes = store.read("resumes.json") or []
        matched = [r for r in all_resumes if r.get("id") == resume_id]
        if matched:
            r = matched[0]
            parts = []
            if r.get("skills"):
                parts.append(f"Skills: {', '.join(r['skills'])}")
            if r.get("job_titles"):
                parts.append(f"Recent titles: {', '.join(r['job_titles'])}")
            if r.get("companies_worked_at"):
                parts.append(f"Previous employers: {', '.join(r['companies_worked_at'])}")
            resume_summary = "; ".join(parts) if parts else None
        # Update resume_id in case it was provided this turn
        if req.resume_id:
            motivation["resume_id"] = req.resume_id

    # Call LLM
    result = await asyncio.to_thread(
        motivation_chat_turn,
        motivation["chat_history"],
        config,
        resume_summary=resume_summary,
        api_key=api_key,
    )

    # Append assistant reply
    motivation["chat_history"].append({"role": "assistant", "content": result["reply"]})

    # If ready, store summary and mark completed
    if result["ready"] and result.get("summary"):
        motivation["summary"] = result["summary"]
        motivation["status"] = "completed"

    _save_motivation(store, motivation)

    return {
        "reply": result["reply"],
        "ready": result["ready"],
        "summary": result.get("summary"),
        "status": motivation["status"],
        "chat_history": motivation["chat_history"],
    }


@router.get("/motivation")
async def get_motivation_endpoint(
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Return the user's current motivation."""
    user_id, jwt_token = _auth if _auth else (None, None)
    store = get_storage_backend(user_id, jwt_token)

    motivation = _load_motivation(store)
    if motivation is None:
        raise HTTPException(status_code=404, detail="No motivation found.")
    return motivation


@router.delete("/motivation")
async def delete_motivation_endpoint(
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Delete the user's current motivation (reset)."""
    user_id, jwt_token = _auth if _auth else (None, None)
    store = get_storage_backend(user_id, jwt_token)

    if store.exists("user_motivation.json"):
        store.delete("user_motivation.json")

    return {"deleted": True}


@router.post("/motivation/finalize")
async def finalize_motivation_endpoint(
    _auth: tuple[str, str] | None = Depends(get_current_user),
) -> dict:
    """Force-finalize the current motivation by generating a summary."""
    user_id, jwt_token = _auth if _auth else (None, None)
    store = get_storage_backend(user_id, jwt_token)

    config = load_config()

    try:
        api_key = resolve_api_key(config.model_provider, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    motivation = _load_motivation(store)
    if motivation is None:
        raise HTTPException(status_code=404, detail="No motivation found.")

    if motivation.get("status") == "completed":
        return motivation

    # Generate summary from existing conversation
    summary = await asyncio.to_thread(
        generate_summary,
        motivation["chat_history"],
        config,
        api_key=api_key,
    )

    motivation["summary"] = summary
    motivation["status"] = "completed"
    _save_motivation(store, motivation)

    return motivation

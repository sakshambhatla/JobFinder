from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from jobfinder.api.auth import get_current_user
from jobfinder.config import load_config
from jobfinder.resume.parser import parse_resumes
from jobfinder.storage import get_storage_backend

router = APIRouter()


@router.post("/resume/upload")
async def upload_resume(
    file: UploadFile,
    user_id: str | None = Depends(get_current_user),
) -> dict:
    """Upload a .txt resume file. Appends to existing resumes (multi-resume)."""
    # Sanitize: strip any directory components to prevent path traversal.
    safe_filename = Path(file.filename or "").name
    if not safe_filename or not safe_filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt resume files are supported.")

    content = await file.read()
    if len(content) > 512_000:
        raise HTTPException(status_code=413, detail="Resume file too large. Maximum size is 500 KB.")

    config = load_config()
    resume_dir = config.resume_dir
    resume_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded file (overwrites if same filename exists)
    dest = resume_dir / safe_filename
    dest.write_bytes(content)

    # Parse ALL resumes in the directory (multi-resume mode)
    all_parsed = await asyncio.to_thread(parse_resumes, resume_dir)

    store = get_storage_backend(user_id)

    # Preserve existing resume IDs for files that haven't changed
    existing_data = store.read("resumes.json") or []
    existing_by_filename: dict[str, dict] = {}
    if isinstance(existing_data, list):
        for r in existing_data:
            existing_by_filename[r.get("filename", "")] = r

    result = []
    for r in all_parsed:
        dumped = r.model_dump()
        # Reuse existing UUID if this filename was already uploaded
        if r.filename in existing_by_filename:
            dumped["id"] = existing_by_filename[r.filename].get("id", dumped["id"])
        result.append(dumped)

    store.write("resumes.json", result)
    return {"resumes": result}


@router.get("/resume")
async def get_resume(user_id: str | None = Depends(get_current_user)) -> dict:
    """Return the most recently parsed resume data."""
    store = get_storage_backend(user_id)
    data = store.read("resumes.json")
    if data is None:
        raise HTTPException(status_code=404, detail="No resume found. Upload one first.")
    return {"resumes": data}


@router.delete("/resume/{filename}")
async def delete_resume(
    filename: str,
    user_id: str | None = Depends(get_current_user),
) -> dict:
    """Remove a resume entry from resumes.json and delete its .txt file if present."""
    config = load_config()
    store = get_storage_backend(user_id)
    data = store.read("resumes.json") or []

    updated = [r for r in data if r.get("filename") != filename]
    if len(updated) == len(data):
        raise HTTPException(status_code=404, detail=f"Resume '{filename}' not found.")

    store.write("resumes.json", updated)

    # Best-effort: delete the .txt file if it still exists.
    # Sanitize filename to prevent path traversal (e.g. "../../config.json").
    safe_filename = Path(filename).name
    txt_path = config.resume_dir / safe_filename
    if txt_path.exists():
        txt_path.unlink()

    return {"resumes": updated}

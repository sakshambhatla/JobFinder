"""Supabase Vault helpers for per-user encrypted API key storage.

All operations go through SECURITY DEFINER SQL functions defined in
``supabase/migrations/003_vault_api_keys.sql``.  The Supabase client is
created with the service_role key so it can call these privileged functions.
"""

from __future__ import annotations

import os
from typing import Any


def _supabase_client():
    """Lazy import + client creation (mirrors supabase_backend.py)."""
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    return create_client(url, key)


def store_api_key(user_id: str, provider: str, api_key: str) -> None:
    """Encrypt and store an LLM API key for *user_id* / *provider*."""
    client = _supabase_client()
    client.rpc(
        "store_user_api_key",
        {"p_user_id": user_id, "p_provider": provider, "p_api_key": api_key},
    ).execute()


def get_api_key(user_id: str, provider: str) -> str | None:
    """Return the decrypted API key, or ``None`` if not stored."""
    client = _supabase_client()
    resp = client.rpc(
        "get_user_api_key",
        {"p_user_id": user_id, "p_provider": provider},
    ).execute()
    return resp.data if resp.data else None


def delete_api_key(user_id: str, provider: str) -> None:
    """Remove a stored API key for *user_id* / *provider*."""
    client = _supabase_client()
    client.rpc(
        "delete_user_api_key",
        {"p_user_id": user_id, "p_provider": provider},
    ).execute()


def has_api_keys(user_id: str) -> dict[str, bool]:
    """Return ``{"anthropic": bool, "gemini": bool}`` without decrypting."""
    client = _supabase_client()
    resp = client.rpc(
        "has_user_api_keys",
        {"p_user_id": user_id},
    ).execute()
    if isinstance(resp.data, dict):
        return resp.data
    # Fallback if RPC returns unexpected shape.
    return {"anthropic": False, "gemini": False}

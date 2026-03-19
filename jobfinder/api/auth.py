"""Authentication dependency for FastAPI routes.

When ``SUPABASE_URL`` is set, verifies the Supabase JWT using Supabase's
JWKS endpoint (``/auth/v1/.well-known/jwks.json``).  This works for both
ES256/P-256 (newer Supabase projects) and HS256 (older projects) since the
JWKS endpoint advertises the correct key type.

When ``SUPABASE_URL`` is **not** set (local dev), returns ``None`` — the
storage factory falls back to :class:`JsonStorageBackend` and no auth is
required.
"""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# auto_error=False so the dependency doesn't 403 when no header is present
# (we handle the missing-header case ourselves below).
_bearer = HTTPBearer(auto_error=False)

# Module-level JWKS client — shared across requests so public keys are cached.
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        try:
            from jwt import PyJWKClient
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Server misconfigured: pyjwt[crypto] not installed",
            )
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def _decode_jwt(raw_token: str) -> str:
    """Decode a Supabase JWT and return the user UUID (``sub`` claim).

    Uses JWKS-based verification so it works regardless of whether the project
    uses HS256 or ES256/P-256 signing.
    """
    try:
        import jwt

        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(raw_token)
        payload = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: pyjwt not installed",
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token: str | None = Query(None),
) -> tuple[str, str] | None:
    """Return ``(user_id, raw_jwt)`` for the authenticated user, or ``None`` in dev mode.

    Accepts the JWT from either:
      - ``Authorization: Bearer <token>`` header (standard REST calls)
      - ``?token=<jwt>`` query param (SSE via EventSource, which can't send headers)

    Dev mode: ``SUPABASE_URL`` is not set -> no auth required.
    Prod mode: ``SUPABASE_URL`` is set -> JWT must be valid.
    """
    if not os.environ.get("SUPABASE_URL"):
        return None  # dev bypass -- local JSON storage, no auth

    # Prefer header, fall back to query param (SSE)
    raw_token = (credentials.credentials if credentials else None) or token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return (_decode_jwt(raw_token), raw_token)

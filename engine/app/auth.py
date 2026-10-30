"""Two ways in:
1. X-API-Key header (server-to-server, scripts).
2. Short-lived HMAC token minted by the Vercel app (?token= or Authorization: Bearer), so browsers can upload
   large files straight to the engine through the Cloudflare tunnel without ever seeing a long-lived key.
Token format: base64url(json{"sub":..., "exp":unix}) + "." + base64url(hmac_sha256(secret, payload))
"""
import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request

from .config import settings


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_token(sub: str, ttl: int = 3600) -> str:
    payload = _b64(json.dumps({"sub": sub, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify_token(token: str) -> dict | None:
    if not settings.token_secret or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    good = _b64(hmac.new(settings.token_secret.encode(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, good):
        return None
    data = json.loads(_unb64(payload))
    if data.get("exp", 0) < time.time():
        return None
    return data


def require_auth(request: Request) -> str:
    if not settings.api_keys and not settings.token_secret:
        return "anonymous"  # local development
    key = request.headers.get("x-api-key")
    if key and key in settings.api_keys:
        return "api-key"
    token = request.query_params.get("token") or ""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:]
    data = verify_token(token) if token else None
    if data:
        return data.get("sub", "user")
    raise HTTPException(401, "Unauthorized")

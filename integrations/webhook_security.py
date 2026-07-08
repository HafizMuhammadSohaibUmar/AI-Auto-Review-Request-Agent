"""Shared webhook signature helpers."""
import hashlib
import hmac

from fastapi import HTTPException, Request


def hmac_sha256_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def require_hmac_signature(*, body: bytes, signature: str, secret: str, provider: str) -> None:
    if not secret:
        raise HTTPException(status_code=500, detail=f"{provider} webhook secret is not configured")
    expected = hmac_sha256_signature(secret, body)
    normalized = signature.removeprefix("sha256=").strip()
    if not hmac.compare_digest(normalized, expected):
        raise HTTPException(status_code=403, detail=f"Invalid {provider} signature")


def require_api_key(request: Request, *, expected: str, header_name: str = "X-LeadPilot-Key") -> None:
    if not expected:
        raise HTTPException(status_code=500, detail="Manual trigger API key is not configured")
    if request.headers.get(header_name, "") != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")

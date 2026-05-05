"""
Rate-limiting configuration — slowapi.

Phase 1 PR #5 — task 1.5.

CLAUDE.md §3 baseline: 5 login attempts per minute per IP. The default
per-route policy is empty so we only apply limits where explicitly decorated.

The 429 handler emits an RFC 7807 problem+json body with a `Retry-After`
header. Unit tests call the handler directly to assert the contract.

H-4 (security-reviewer blocker):
  - The key function must honour `X-Forwarded-For` so reverse proxies in
    front of FastAPI (Traefik, nginx, GCP LB) report the real client IP
    instead of the proxy's loopback. Without this every caller shares the
    same bucket and the limiter becomes a global rate cap.
  - Storage is Redis (shared across uvicorn workers / Celery beats), not
    slowapi's default in-memory dict, so the 5/min budget is enforced
    correctly under multi-worker deployments.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.config import redis_url
from core.errors import PROBLEM_CONTENT_TYPE

# Module-level constant — this is policy, not configuration. Keep it in code.
LOGIN_RATE_LIMIT = "5/minute"


def _client_ip_for_limit(request: Request) -> str:
    """
    H-4: prefer the leftmost X-Forwarded-For entry (reverse proxies set this
    to the real client IP), fall back to the ASGI client tuple via slowapi's
    `get_remote_address`. Mirrors `core.middleware._extract_client_ip` so
    audit + rate-limit see the same IP for any given request.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        first = fwd.split(",", 1)[0].strip()
        if first:
            return first
    return get_remote_address(request)


# Limiter keyed by client IP. `default_limits=[]` → endpoints opt in via
# @limiter.limit(...). storage_uri uses Redis so the 5/min budget is shared
# across uvicorn workers (the function call is a runtime call, not a cached
# module constant — CLAUDE.md rule #11 is about getenv, not bootstrap config).
limiter = Limiter(
    key_func=_client_ip_for_limit,
    default_limits=[],
    storage_uri=redis_url(),
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Convert slowapi's RateLimitExceeded into RFC 7807 + Retry-After.

    Retry-After is a fixed 60s for the login limiter; if we add more granular
    policies later we can derive it from `exc.limit.error_message`.
    """
    detail = getattr(getattr(exc, "limit", None), "error_message", None) or "Rate limit exceeded"
    body = {
        "type": "about:blank",
        "title": "Too Many Requests",
        "status": 429,
        "detail": str(detail),
        "instance": getattr(getattr(request, "url", None), "path", None) or "/",
    }
    response = JSONResponse(
        body,
        status_code=429,
        media_type=PROBLEM_CONTENT_TYPE,
    )
    response.headers["Retry-After"] = "60"
    return response

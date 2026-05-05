"""
Runtime configuration accessors.

CLAUDE.md core rule #11: do not cache environment variables in module-level
constants. Every accessor below calls os.getenv() at the moment it is invoked
so the values stay correct when the process re-reads its environment (e.g.
docker-compose --env-file changes between sessions).
"""

from __future__ import annotations

import os

DEFAULT_DATABASE_URL = "postgresql+asyncpg://trustedoss:trustedoss@postgres:5432/trustedoss"
DEFAULT_REDIS_URL = "redis://redis:6379/0"


def database_url() -> str:
    """Return the SQLAlchemy async DSN (asyncpg driver)."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def database_url_sync() -> str:
    """
    Sync DSN derived from DATABASE_URL.

    Alembic runs migrations through the synchronous engine (psycopg2) while the
    application uses asyncpg. We strip the +asyncpg suffix here so callers do
    not have to think about driver dialects.
    """
    raw = database_url()
    return raw.replace("postgresql+asyncpg://", "postgresql://")


def redis_url() -> str:
    return os.getenv("REDIS_URL", DEFAULT_REDIS_URL)


def secret_key() -> str:
    return os.getenv("SECRET_KEY", "change-me-in-dev-only-not-for-production")


def access_token_expire_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def refresh_token_expire_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def log_level() -> str:
    return os.getenv("LOG_LEVEL", "INFO").upper()


def cors_allowed_origins() -> list[str]:
    """
    Comma-separated origin list. Production must set this explicitly;
    dev defaults to the Vite dev server.
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def app_env() -> str:
    """`dev`, `staging`, `prod` — informational, drives a few CORS/log defaults."""
    return os.getenv("APP_ENV", "dev").lower()

"""
Database engine and session factory wiring.

The engine is created during the FastAPI lifespan and stored on app.state so
environment variables are read once per process startup (CLAUDE.md core rule
#11 — no module-level caching). Request handlers acquire sessions via the
get_db dependency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import database_url


def build_engine() -> AsyncEngine:
    """Create a fresh async engine using the current DATABASE_URL value."""
    return create_async_engine(database_url(), pool_pre_ping=True, future=True)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def _ensure_state(app: Any) -> async_sessionmaker[AsyncSession]:
    """
    Return the app's session factory, building it lazily if the lifespan has
    not run.

    The FastAPI lifespan is the canonical place to construct the engine, but
    httpx's `ASGITransport` does not trigger lifespan events by default. To
    keep the integration tests simple we fall back to building on first
    access — and we install the audit listener at the same time so audit
    logs work even outside the normal startup path. This is idempotent.
    """
    state = app.state
    factory = getattr(state, "session_factory", None)
    if factory is None:
        # Local import to avoid circular dependency between db <-> audit.
        from .audit import install_audit_listeners

        engine = build_engine()
        state.engine = engine
        factory = build_session_factory(engine)
        state.session_factory = factory
        install_audit_listeners(factory)
    return factory


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = _ensure_state(request.app)
    async with session_factory() as session:
        yield session

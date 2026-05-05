"""
Database engine and session factory wiring.

The engine is created during the FastAPI lifespan and stored on app.state so
environment variables are read once per process startup (CLAUDE.md core rule
#11 — no module-level caching). Request handlers acquire sessions via the
get_db dependency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

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


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session

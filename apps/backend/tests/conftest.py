"""
Backend test bootstrap.

Adds the backend root to sys.path so tests can import top-level packages
(`main`, `core`, `tasks`) when pytest is invoked from anywhere.

Also installs autouse fixtures that:
  - reset slowapi's in-memory rate-limit storage so policy state never
    leaks across tests, and
  - dispose the FastAPI app's async engine after every test so asyncpg's
    connection pool does not get reused under a different event loop.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear slowapi's in-memory storage so rate-limit state never leaks."""
    try:
        from core.ratelimit import limiter
    except Exception:  # pragma: no cover - slowapi optional in some envs
        return
    limiter.reset()


@pytest.fixture(autouse=True)
async def _isolate_engine_per_test() -> AsyncIterator[None]:
    """
    Dispose the FastAPI app's async engine after every test.

    pytest-asyncio creates a fresh event loop per test by default. asyncpg
    connections bind to whatever loop opened them, so reusing the engine
    across tests crashes with "got Future <...> attached to a different
    loop". We dispose after each test; the next test triggers
    core.db._ensure_state to rebuild it under the new loop.
    """
    yield
    try:
        from main import app
    except Exception:  # pragma: no cover
        return
    engine = getattr(app.state, "engine", None)
    if engine is None:
        return
    await engine.dispose()
    if "engine" in app.state.__dict__:
        del app.state.__dict__["engine"]
    if "session_factory" in app.state.__dict__:
        del app.state.__dict__["session_factory"]

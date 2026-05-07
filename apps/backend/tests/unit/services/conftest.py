"""
Shared fixtures for ``tests/unit/services/*`` — Phase 4 PR #14.

Re-exports the fakeredis + DTClient fixtures originally written for the
integrations test tree (``tests/unit/integrations/conftest.py``). PR #14's
admin DT service drives the same primitives (CircuitBreaker against
fakeredis, DTClient with httpx.MockTransport), so duplicating the
fixtures here would be wasteful — we import them.

We do NOT make the integrations conftest's fixtures package-scoped global
because pytest's conftest discovery is path-based: a fixture defined under
``tests/unit/integrations/conftest.py`` is only visible inside that
directory tree. This thin re-export bridges the two trees.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest


@pytest.fixture
def fakeredis_client() -> Iterator[Any]:
    """Yield a fresh fakeredis client; identical to the integrations fixture."""
    fakeredis = pytest.importorskip("fakeredis")
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    try:
        yield client
    finally:
        client.flushall()
        client.close()


@pytest.fixture
def make_breaker(fakeredis_client: Any) -> Callable[..., Any]:
    """CircuitBreaker factory bound to the fake Redis."""
    from integrations.dt.breaker import CircuitBreaker

    def _factory(
        *,
        failure_threshold: int | None = None,
        cooldown_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
    ) -> CircuitBreaker:
        kwargs: dict[str, Any] = {"redis_client": fakeredis_client}
        if failure_threshold is not None:
            kwargs["failure_threshold"] = failure_threshold
        if cooldown_seconds is not None:
            kwargs["cooldown_seconds"] = cooldown_seconds
        if clock is not None:
            kwargs["clock"] = clock
        return CircuitBreaker(**kwargs)

    return _factory


@pytest.fixture
def make_dt_client() -> Callable[[Callable[[httpx.Request], httpx.Response]], Any]:
    """DTClient factory backed by ``httpx.MockTransport``."""
    from integrations.dt.client import DTClient

    def _factory(handler: Callable[[httpx.Request], httpx.Response]) -> DTClient:
        transport = httpx.MockTransport(handler)
        http = httpx.Client(
            transport=transport,
            base_url="http://test-dt.invalid",
            headers={"X-API-Key": "test-key", "Accept": "application/json"},
            timeout=1.0,
        )
        return DTClient(http=http)

    return _factory

"""
Tests for ``tasks.dt_orphan_cleanup`` — Phase 4 PR #14.

The task body is sync; we drive its DT-deletion logic by patching the
breaker / DT client / sync session factory. Three branches matter:

  - Happy path: every UUID gets ``DELETE /api/v1/project/{uuid}`` and an
    audit row.
  - Idempotent path: DT 4xx (already gone) is recorded under ``already_gone``.
  - Bad UUID input: malformed strings are routed to ``failed``.

We do NOT exercise the Celery autoretry path — that would need a real
broker; we trust Celery's own retry mechanics.
"""

from __future__ import annotations

from typing import Any

import pytest

from integrations.dt import DTClientError


class _FakeBreaker:
    """Lets the test pass-through the inner ``call`` without breaker logic."""

    def __init__(self, *, raise_on_call: Exception | None = None) -> None:
        self.raise_on_call = raise_on_call
        self.calls: list[Any] = []

    def call(self, fn):  # type: ignore[no-untyped-def]
        if self.raise_on_call is not None:
            raise self.raise_on_call
        self.calls.append(fn)
        return fn()

    def snapshot(self) -> Any:
        from integrations.dt.breaker import BreakerSnapshot

        return BreakerSnapshot(state="closed", fail_count=0, opened_at=None)


class _FakeDTClient:
    """Track every delete_project call; raise DTClientError on a marked uuid."""

    def __init__(self, *, missing_uuids: set[str] | None = None) -> None:
        self.deleted: list[str] = []
        self.missing_uuids = missing_uuids or set()

    def delete_project(self, *, project_uuid: str) -> None:
        if project_uuid in self.missing_uuids:
            raise DTClientError(f"DT 404 on {project_uuid}")
        self.deleted.append(project_uuid)

    def list_projects(self, **_kw: Any) -> list[Any]:
        return []  # not used in these tests

    def close(self) -> None:
        pass


class _FakeRedis:
    """Minimal stand-in — tracks delete calls for the lock release branch."""

    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def delete(self, key: str) -> None:
        self.deleted_keys.append(key)


class _FakeSyncSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def execute(self, _stmt: Any) -> Any:
        return self  # not used in cleanup task delete path

    def scalars(self) -> Any:
        return self


def _scope_factory(session: _FakeSyncSession):  # type: ignore[no-untyped-def]
    """Match the contextmanager protocol of sync_session_scope."""
    from contextlib import contextmanager

    @contextmanager
    def _scope():  # type: ignore[no-untyped-def]
        try:
            yield session
        finally:
            session.close()

    return _scope


def test_orphan_cleanup_deletes_each_uuid_and_emits_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tasks import dt_orphan_cleanup as task_module

    fake_breaker = _FakeBreaker()
    fake_client = _FakeDTClient()
    fake_session = _FakeSyncSession()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(task_module, "get_breaker", lambda: fake_breaker)
    monkeypatch.setattr(task_module, "build_client", lambda: fake_client)
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(fake_session))
    monkeypatch.setattr(
        task_module.redis.Redis,
        "from_url",
        classmethod(lambda cls, *_a, **_kw: fake_redis),
    )

    uuids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]

    # Call the underlying function via .run so we don't go through Celery's
    # binding machinery (no broker required).
    summary = task_module.dt_orphan_cleanup_task.run(uuids)

    assert sorted(summary["deleted"]) == sorted(uuids)
    assert summary["already_gone"] == []
    assert summary["failed"] == []
    assert sorted(fake_client.deleted) == sorted(uuids)
    # One audit row per deleted UUID.
    audit_rows = [obj for obj in fake_session.added if hasattr(obj, "target_table")]
    assert len(audit_rows) == 2
    assert all(r.target_table == "dt_projects" for r in audit_rows)
    assert all(r.action == "delete" for r in audit_rows)
    # Lock release.
    assert "dt:admin:orphan_cleanup_lock" in fake_redis.deleted_keys


def test_orphan_cleanup_404_is_treated_as_already_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tasks import dt_orphan_cleanup as task_module

    missing = "00000000-0000-0000-0000-000000000099"
    present = "00000000-0000-0000-0000-000000000001"

    fake_breaker = _FakeBreaker()
    fake_client = _FakeDTClient(missing_uuids={missing})
    fake_session = _FakeSyncSession()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(task_module, "get_breaker", lambda: fake_breaker)
    monkeypatch.setattr(task_module, "build_client", lambda: fake_client)
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(fake_session))
    monkeypatch.setattr(
        task_module.redis.Redis,
        "from_url",
        classmethod(lambda cls, *_a, **_kw: fake_redis),
    )

    summary = task_module.dt_orphan_cleanup_task.run([present, missing])

    assert summary["deleted"] == [present]
    assert summary["already_gone"] == [missing]
    assert summary["failed"] == []
    # Two audit rows: one ``delete`` for the present, one ``delete_skipped_missing``
    # for the missing.
    audit_actions = sorted(
        obj.action
        for obj in fake_session.added
        if hasattr(obj, "action")
    )
    assert audit_actions == ["delete", "delete_skipped_missing"]


def test_orphan_cleanup_empty_uuid_list_scans_dt_and_deletes_orphans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When called with ``[]``, the task scans the DT catalog and deletes
    every orphan it finds. We patch the breaker / client / session so
    the test exercises the catalog-walk branch without a real DT.
    """
    from tasks import dt_orphan_cleanup as task_module

    fake_breaker = _FakeBreaker()
    fake_redis = _FakeRedis()

    # Build a DT client whose list_projects returns one page with two
    # orphan-shaped rows then an empty page (terminator).
    class _ListingClient(_FakeDTClient):
        def __init__(self, pages: list[list[Any]]) -> None:
            super().__init__()
            self.pages = pages
            self.idx = 0

        def list_projects(self, *, page_size: int = 100, page_number: int = 1) -> list[Any]:  # noqa: ARG002
            i = self.idx
            self.idx += 1
            return self.pages[i] if i < len(self.pages) else []

    # DT project UUIDs are themselves UUIDs in DT's storage; use realistic
    # values so the task's delete loop survives ``uuid.UUID(str(raw_uuid))``
    # validation. (Phase 2 PR #8 adopted DT's "version=scan_uuid" convention,
    # but the project UUID is independent and is also a UUID.)
    project_a = {
        "uuid": "11111111-1111-1111-1111-111111111111",
        "version": "00000000-0000-0000-0000-000000000099",
    }
    project_b = {
        "uuid": "22222222-2222-2222-2222-222222222222",
        "version": "00000000-0000-0000-0000-000000000098",
    }
    fake_client = _ListingClient(pages=[[project_a, project_b], []])

    fake_session = _FakeSyncSession()

    # Force the scan-id query to return an empty set so every project is
    # classified as an orphan. The session.scalars().all() chain is the
    # SQLAlchemy idiom the task expects.
    class _StubScalars:
        def all(self) -> list[Any]:
            return []

    class _StubResult:
        def scalars(self) -> _StubScalars:
            return _StubScalars()

    def _execute(_stmt: Any) -> _StubResult:
        return _StubResult()

    fake_session.execute = _execute  # type: ignore[assignment]

    monkeypatch.setattr(task_module, "get_breaker", lambda: fake_breaker)
    monkeypatch.setattr(task_module, "build_client", lambda: fake_client)
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(fake_session))
    monkeypatch.setattr(
        task_module.redis.Redis,
        "from_url",
        classmethod(lambda cls, *_a, **_kw: fake_redis),
    )

    summary = task_module.dt_orphan_cleanup_task.run([])

    assert sorted(summary["deleted"]) == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]
    assert summary["scanned"] == 2
    assert "dt:admin:orphan_cleanup_lock" in fake_redis.deleted_keys


def test_orphan_cleanup_invalid_uuid_routed_to_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tasks import dt_orphan_cleanup as task_module

    fake_breaker = _FakeBreaker()
    fake_client = _FakeDTClient()
    fake_session = _FakeSyncSession()
    fake_redis = _FakeRedis()

    monkeypatch.setattr(task_module, "get_breaker", lambda: fake_breaker)
    monkeypatch.setattr(task_module, "build_client", lambda: fake_client)
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(fake_session))
    monkeypatch.setattr(
        task_module.redis.Redis,
        "from_url",
        classmethod(lambda cls, *_a, **_kw: fake_redis),
    )

    # Mix valid + invalid; the schema usually catches malformed strings, but
    # the empty-list branch reads raw DT data so the task itself must defend.
    summary = task_module.dt_orphan_cleanup_task.run(
        [
            "00000000-0000-0000-0000-000000000001",  # valid
            "not-a-uuid",
            "javascript:alert(1)",
        ]
    )
    assert sorted(summary["deleted"]) == ["00000000-0000-0000-0000-000000000001"]
    assert len(summary["failed"]) == 2

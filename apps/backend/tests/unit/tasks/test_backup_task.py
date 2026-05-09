"""
Unit tests for ``tasks.backup`` — Phase 6 chore PR #19.

We drive the task body via ``run_backup_task.run`` / ``restore_backup_task.run``
to bypass Celery's bind-self injection without needing a broker. Subprocess
calls are patched so the tests are hermetic; audit emission is captured via a
fake sync session.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeSession:
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


class _SessionAccumulator:
    """Collects every session opened via the patched scope."""

    def __init__(self) -> None:
        self.sessions: list[_FakeSession] = []

    @property
    def all_added(self) -> list[Any]:
        return [obj for session in self.sessions for obj in session.added]


def _scope_factory(accumulator: _SessionAccumulator) -> Any:
    """Return a ``sync_session_scope``-compatible context manager."""

    @contextmanager
    def _scope() -> Any:
        session = _FakeSession()
        accumulator.sessions.append(session)
        try:
            yield session
        finally:
            session.close()

    return _scope


def _seed_manifest(root: Path, name: str, *, alembic_head: str = "abc123") -> None:
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    (target / "postgres.sql.gz").write_bytes(b"\x1f\x8bfake")
    (target / "manifest.json").write_text(
        json.dumps({"alembic_head": alembic_head, "timestamp": "2026-05-09"})
    )


# ---------------------------------------------------------------------------
# run_backup_task
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_backups(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("BACKUPS_ROOT", str(tmp_path))
    return tmp_path


def test_run_backup_emits_completed_audit_on_success(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    fake_completed = subprocess.CompletedProcess(
        args=["bash", "scripts/backup.sh"], returncode=0, stdout="ok", stderr=""
    )

    captured_calls: list[dict[str, Any]] = []

    def _fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_calls.append(kwargs)
        # Simulate the script writing manifest + artifacts to BACKUP_DIR.
        backup_dir = Path(kwargs["env"]["BACKUP_DIR"])
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "postgres.sql.gz").write_bytes(b"\x1f\x8bfake")
        (backup_dir / "manifest.json").write_text(
            json.dumps({"alembic_head": "rev42"})
        )
        return fake_completed

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = task_module.run_backup_task.run(kind="manual", actor_user_id=None)

    assert result["name"].startswith("manual-")
    assert result["db_revision"] == "rev42"
    assert result["size_bytes"] > 0
    assert result["pruned"] == []

    actions = sorted(getattr(obj, "action", "") for obj in accumulator.all_added)
    assert "backup.completed" in actions
    # No failure rows on the success path.
    assert "backup.failed" not in actions

    completed_row = next(
        obj for obj in accumulator.all_added if getattr(obj, "action", "") == "backup.completed"
    )
    assert completed_row.target_table == "backups"
    assert completed_row.diff["kind"] == "manual"
    assert completed_row.diff["db_revision"] == "rev42"

    # Subprocess invoked with the correct env override.
    assert captured_calls[0]["env"]["BACKUP_DIR"]


def test_run_backup_raises_and_emits_failed_audit_on_subprocess_error(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    def _fail(_argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(returncode=2, cmd=_argv, stderr="pg_dump exploded")

    monkeypatch.setattr(subprocess, "run", _fail)

    with pytest.raises(task_module.BackupTaskError):
        task_module.run_backup_task.run(kind="auto", actor_user_id=None)

    actions = [getattr(obj, "action", "") for obj in accumulator.all_added]
    assert actions == ["backup.failed"]
    failed = accumulator.all_added[0]
    assert failed.diff["returncode"] == 2
    assert "pg_dump exploded" in failed.diff["stderr_tail"]


def test_run_backup_applies_retention_after_success(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    """An old auto backup is pruned during the post-success retention pass."""
    from tasks import backup as task_module

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    # Pre-seed an old auto backup that the retention pass should remove.
    old_name = "auto-20260101T000000Z"
    old_dir = temp_backups / old_name
    old_dir.mkdir()
    (old_dir / "postgres.sql.gz").write_bytes(b"old")
    (old_dir / "manifest.json").write_text(json.dumps({"alembic_head": "old"}))
    eight_days_ago = (datetime.now(tz=UTC) - timedelta(days=8)).timestamp()
    import os

    os.utime(old_dir, (eight_days_ago, eight_days_ago))

    # Pre-seed a manual that must NOT be pruned even though it is also old.
    manual_old_name = "manual-20260101T000000Z"
    manual_old = temp_backups / manual_old_name
    manual_old.mkdir()
    (manual_old / "postgres.sql.gz").write_bytes(b"old")
    (manual_old / "manifest.json").write_text(json.dumps({"alembic_head": "old"}))
    os.utime(manual_old, (eight_days_ago, eight_days_ago))

    def _fake_run(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        backup_dir = Path(kwargs["env"]["BACKUP_DIR"])
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "postgres.sql.gz").write_bytes(b"\x1f\x8bfake")
        (backup_dir / "manifest.json").write_text(json.dumps({"alembic_head": "rev42"}))
        return subprocess.CompletedProcess(args=_argv, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = task_module.run_backup_task.run(kind="auto", actor_user_id=None)

    assert old_name in result["pruned"]
    assert manual_old_name not in result["pruned"]
    assert not old_dir.exists()
    assert manual_old.is_dir()

    # One backup.pruned audit row per deleted entry.
    pruned_rows = [
        obj for obj in accumulator.all_added if getattr(obj, "action", "") == "backup.pruned"
    ]
    assert [row.target_id for row in pruned_rows] == [old_name]


def test_run_backup_records_actor_uuid_when_supplied(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    actor = uuid.uuid4()

    def _fake_run(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        backup_dir = Path(kwargs["env"]["BACKUP_DIR"])
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "postgres.sql.gz").write_bytes(b"x")
        (backup_dir / "manifest.json").write_text(json.dumps({"alembic_head": "r"}))
        return subprocess.CompletedProcess(args=_argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    task_module.run_backup_task.run(kind="manual", actor_user_id=str(actor))

    completed = next(
        obj for obj in accumulator.all_added if getattr(obj, "action", "") == "backup.completed"
    )
    assert completed.actor_user_id == actor


# ---------------------------------------------------------------------------
# restore_backup_task
# ---------------------------------------------------------------------------


def test_restore_backup_emits_restored_audit_on_success(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    name = "manual-20260509T120000Z"
    _seed_manifest(temp_backups, name, alembic_head="rev99")

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    captured_envs: list[dict[str, str]] = []

    def _fake_run(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_envs.append(kwargs["env"])
        return subprocess.CompletedProcess(args=_argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    actor = uuid.uuid4()
    result = task_module.restore_backup_task.run(name=name, actor_user_id=str(actor))

    assert result["revision_before"] == "rev99"
    assert result["revision_after"] == "rev99"
    assert result["mismatch"] is False

    actions = [getattr(obj, "action", "") for obj in accumulator.all_added]
    assert actions == ["backup.restored"]

    # The restore script was invoked with the non-interactive confirm env.
    assert captured_envs[0]["BACKUP_RESTORE_CONFIRM"] == "yes"


def test_restore_backup_raises_when_artifact_missing(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    name = "manual-20260509T120000Z"
    target = temp_backups / name
    target.mkdir()
    # Only the manifest is present — postgres.sql.gz missing.
    (target / "manifest.json").write_text(json.dumps({"alembic_head": "rev1"}))

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    actor = uuid.uuid4()
    with pytest.raises(task_module.RestoreTaskError):
        task_module.restore_backup_task.run(name=name, actor_user_id=str(actor))

    actions = [getattr(obj, "action", "") for obj in accumulator.all_added]
    assert actions == ["backup.restore_failed"]
    failed = accumulator.all_added[0]
    assert failed.diff["error"] == "incomplete_artifacts"
    assert failed.diff["missing"] == "postgres.sql.gz"


def test_restore_backup_raises_on_invalid_name(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    """Path-traversal name → RestoreTaskError + audit row."""
    from tasks import backup as task_module

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    actor = uuid.uuid4()
    with pytest.raises(task_module.RestoreTaskError):
        task_module.restore_backup_task.run(
            name="../etc/passwd", actor_user_id=str(actor)
        )

    actions = [getattr(obj, "action", "") for obj in accumulator.all_added]
    assert actions == ["backup.restore_failed"]
    assert accumulator.all_added[0].diff["error"] == "not_found"


def test_restore_backup_logs_warning_on_revision_mismatch(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    """If the manifest revision changes between probes, mismatch=True is recorded."""
    from tasks import backup as task_module

    name = "manual-20260509T120000Z"
    _seed_manifest(temp_backups, name, alembic_head="rev_before")

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    def _fake_run(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        # Pretend the script rewrote the manifest mid-run.
        backup_path = temp_backups / name
        (backup_path / "manifest.json").write_text(
            json.dumps({"alembic_head": "rev_after"})
        )
        return subprocess.CompletedProcess(args=_argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    actor = uuid.uuid4()
    result = task_module.restore_backup_task.run(name=name, actor_user_id=str(actor))

    assert result["mismatch"] is True
    restored = accumulator.all_added[0]
    assert restored.action == "backup.restored"
    assert restored.diff["mismatch"] is True
    assert restored.diff["revision_before"] == "rev_before"
    assert restored.diff["revision_after"] == "rev_after"


def test_restore_backup_subprocess_error_emits_failed_audit(
    monkeypatch: pytest.MonkeyPatch, temp_backups: Path
) -> None:
    from tasks import backup as task_module

    name = "manual-20260509T120000Z"
    _seed_manifest(temp_backups, name)

    accumulator = _SessionAccumulator()
    monkeypatch.setattr(task_module, "sync_session_scope", _scope_factory(accumulator))

    def _fail(_argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(
            returncode=3, cmd=_argv, stderr="restore exploded"
        )

    monkeypatch.setattr(subprocess, "run", _fail)

    actor = uuid.uuid4()
    with pytest.raises(task_module.RestoreTaskError):
        task_module.restore_backup_task.run(name=name, actor_user_id=str(actor))

    actions = [getattr(obj, "action", "") for obj in accumulator.all_added]
    assert actions == ["backup.restore_failed"]
    assert accumulator.all_added[0].diff["returncode"] == 3

"""
Integration test: `alembic upgrade head` succeeds against the configured database.

Skipped automatically when DATABASE_URL is not set (e.g. unit-only local runs).
In docker-compose dev and CI the env var is provided, so this exercises a real
Postgres + the bundled migrations end-to-end.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.integration
def test_alembic_upgrade_head_succeeds():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — skip alembic integration test")

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"alembic upgrade head failed (exit {result.returncode})\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.integration
def test_alembic_current_reports_head_revision():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — skip alembic integration test")

    upgrade = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    current = subprocess.run(
        ["alembic", "current"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert current.returncode == 0, current.stderr
    # `alembic current` prints the head revision; today that is `0002` (auth
    # schema). When PR #5 adds further migrations, bump this assertion.
    assert "0002" in current.stdout, current.stdout

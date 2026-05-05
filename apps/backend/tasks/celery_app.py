"""
Celery application bootstrap.

Phase 0 PR #2 only stands up the worker process so docker-compose can verify
the broker/worker wiring. Real tasks (scan_source, scan_container, dt_resync,
backups, …) land in their respective Phases.

CLAUDE.md core rule #11: environment variables are read inside the factory at
process startup, not cached as module-level constants.
"""

from __future__ import annotations

from celery import Celery

from core.config import redis_url
from core.logging import configure_logging


def create_celery_app() -> Celery:
    broker = redis_url()
    app = Celery(
        "trustedoss",
        broker=broker,
        backend=broker,
        include=[],  # task modules registered as Phases land
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue="trustedoss.default",
        timezone="UTC",
        enable_utc=True,
    )
    configure_logging()
    return app


celery_app = create_celery_app()

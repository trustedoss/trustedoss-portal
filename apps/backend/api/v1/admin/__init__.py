"""
Admin API sub-router aggregator — Phase 4 PR #13.

Mounts under ``/v1/admin`` and gates every nested route through
``require_super_admin_or_404`` (existence-hide: non-super-admin = 404,
anonymous = 401).

Sub-routers (PR #13):
  - ``users``  — ``/v1/admin/users/*``
  - ``teams``  — ``/v1/admin/teams/*``

Future PRs (#14 / #15) will add: dt, scans, disk, audit, health, approvals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.security import require_super_admin_or_404

from . import teams, users

# Apply the super-admin gate at the parent-router level so individual route
# signatures stay clean — each route still gets the resolved CurrentUser
# via its own ``Depends(require_super_admin_or_404())`` injection where it
# needs the actor.
router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_super_admin_or_404())],
)

router.include_router(users.router)
router.include_router(teams.router)


__all__ = ["router"]

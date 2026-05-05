"""
Auth request/response schemas — Phase 1 PR #5.

Pydantic v2. We deliberately split RegisterRequest from the ORM model so
incoming JSON cannot smuggle is_superuser/is_active flags. UserPublic is the
only shape ever returned to the wire — it never carries hashed_password.

Quality standard §3 (CLAUDE.md): the password field rejects values shorter
than 12 characters at the schema layer. The 422 response is automatically
RFC 7807 because of the validation handler installed in core.errors.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Inbound payload for POST /auth/register."""

    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=256,
        description="At least 12 characters (NIST 800-63B baseline).",
    )
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    """Inbound payload for POST /auth/login."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    """Shape returned for every user-bearing response. Never includes secrets."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """Response body for /auth/login and /auth/refresh."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int

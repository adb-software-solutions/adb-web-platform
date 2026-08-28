from __future__ import annotations

from datetime import datetime

from ninja import Schema
from pydantic import Field


class CredentialLifecycleUpdateIn(Schema):
    rotation_interval_days: int | None = Field(default=None, ge=1, le=3650)
    clear_rotation_interval: bool = False
    mark_rotated: bool = False


class CredentialHealthOut(Schema):
    credential_id: int
    name: str
    status: str
    client_id: int | None
    client_name: str | None
    expires_at: datetime | None
    expires_in_days: int | None
    last_rotated_at: datetime | None
    rotation_interval_days: int | None
    rotation_due_at: datetime | None
    rotation_due_in_days: int | None
    health_status: str
    health_severity: str
    href: str


class CredentialHealthListOut(Schema):
    items: list[CredentialHealthOut]
    healthy_count: int
    warning_count: int
    critical_count: int

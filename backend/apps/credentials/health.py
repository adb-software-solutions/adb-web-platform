from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from apps.credentials.models import StoredCredential

EXPIRY_WARNING_DAYS = 30
EXPIRY_CRITICAL_DAYS = 7
ROTATION_WARNING_DAYS = 14


@dataclass(frozen=True)
class CredentialHealth:
    status: str
    severity: str
    expires_in_days: int | None
    rotation_due_at: datetime | None
    rotation_due_in_days: int | None


def _whole_days(delta: timedelta) -> int:
    return delta.days


def credential_rotation_due_at(credential: StoredCredential) -> datetime | None:
    if not credential.rotation_interval_days:
        return None
    baseline = credential.last_rotated_at or credential.created_at
    if baseline is None:
        return None
    return baseline + timedelta(days=credential.rotation_interval_days)


def evaluate_credential_health(
    credential: StoredCredential,
    *,
    now: datetime | None = None,
) -> CredentialHealth:
    """Return metadata-only lifecycle health without accessing credential secrets."""
    current = now or timezone.now()
    expires_in_days: int | None = None
    if credential.expires_at is not None:
        expires_in_days = _whole_days(credential.expires_at - current)

    rotation_due_at = credential_rotation_due_at(credential)
    rotation_due_in_days: int | None = None
    if rotation_due_at is not None:
        rotation_due_in_days = _whole_days(rotation_due_at - current)

    if credential.status != StoredCredential.Status.ACTIVE:
        return CredentialHealth(
            status="inactive",
            severity="info",
            expires_in_days=expires_in_days,
            rotation_due_at=rotation_due_at,
            rotation_due_in_days=rotation_due_in_days,
        )
    if expires_in_days is not None and expires_in_days < 0:
        status, severity = "expired", "critical"
    elif rotation_due_in_days is not None and rotation_due_in_days < 0:
        status, severity = "rotation_overdue", "critical"
    elif expires_in_days is not None and expires_in_days <= EXPIRY_CRITICAL_DAYS:
        status, severity = "expiring_soon", "critical"
    elif rotation_due_in_days is not None and rotation_due_in_days <= 0:
        status, severity = "rotation_due", "warning"
    elif expires_in_days is not None and expires_in_days <= EXPIRY_WARNING_DAYS:
        status, severity = "expiring", "warning"
    elif rotation_due_in_days is not None and rotation_due_in_days <= ROTATION_WARNING_DAYS:
        status, severity = "rotation_due_soon", "warning"
    else:
        status, severity = "healthy", "info"

    return CredentialHealth(
        status=status,
        severity=severity,
        expires_in_days=expires_in_days,
        rotation_due_at=rotation_due_at,
        rotation_due_in_days=rotation_due_in_days,
    )

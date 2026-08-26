from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import MonitorCheck, MonitorIncident, MonitorResult


@dataclass(frozen=True)
class CheckObservation:
    successful: bool
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    message: str = ""
    status_code: int | None = None
    observed_value: str = ""
    execution_error: bool = False


@transaction.atomic
def record_observation(check_id: int, observation: CheckObservation) -> MonitorResult:
    """Persist a safe result and advance threshold-aware Check/Incident state."""
    check = MonitorCheck.objects.select_for_update().get(id=check_id)
    outcome = (
        MonitorResult.Outcome.SUCCESS
        if observation.successful
        else (
            MonitorResult.Outcome.ERROR
            if observation.execution_error
            else MonitorResult.Outcome.FAILURE
        )
    )
    result = MonitorResult(
        monitor_check=check,
        outcome=outcome,
        started_at=observation.started_at,
        finished_at=observation.finished_at,
        duration_ms=observation.duration_ms,
        status_code=observation.status_code,
        observed_value=observation.observed_value[:500],
        message=observation.message[:500],
    )
    result.full_clean()
    result.save()

    check.last_checked_at = observation.finished_at
    check.last_duration_ms = observation.duration_ms
    check.last_message = observation.message[:500]
    check.next_run_at = observation.finished_at + timedelta(seconds=check.interval_seconds)

    active_incident = (
        MonitorIncident.objects.select_for_update()
        .filter(
            monitor_check=check,
            status__in=[MonitorIncident.Status.OPEN, MonitorIncident.Status.ACKNOWLEDGED],
        )
        .first()
    )

    if observation.successful:
        check.consecutive_failures = 0
        check.consecutive_successes += 1
        if active_incident and check.consecutive_successes >= check.recovery_threshold:
            active_incident.status = MonitorIncident.Status.RESOLVED
            active_incident.resolved_at = observation.finished_at
            active_incident.save(update_fields=["status", "resolved_at", "updated_at"])
            check.status = MonitorCheck.Status.HEALTHY
        elif active_incident:
            check.status = MonitorCheck.Status.DEGRADED
        else:
            check.status = MonitorCheck.Status.HEALTHY
    else:
        check.consecutive_successes = 0
        check.consecutive_failures += 1
        if active_incident:
            active_incident.failure_count += 1
            active_incident.summary = observation.message[:500] or "Monitoring check failed."
            active_incident.save(update_fields=["failure_count", "summary", "updated_at"])
        if check.consecutive_failures >= check.failure_threshold:
            check.status = MonitorCheck.Status.FAILING
            if active_incident is None:
                MonitorIncident.objects.create(
                    monitor_check=check,
                    severity=check.severity,
                    opened_at=observation.finished_at,
                    failure_count=check.consecutive_failures,
                    summary=observation.message[:500] or "Monitoring check failed.",
                )
        else:
            check.status = MonitorCheck.Status.DEGRADED

    check.save(
        update_fields=[
            "status",
            "consecutive_failures",
            "consecutive_successes",
            "last_checked_at",
            "next_run_at",
            "last_duration_ms",
            "last_message",
            "updated_at",
        ]
    )
    return result


@transaction.atomic
def acknowledge_incident(incident: MonitorIncident) -> MonitorIncident:
    incident = MonitorIncident.objects.select_for_update().get(id=incident.id)
    if incident.status == MonitorIncident.Status.OPEN:
        incident.status = MonitorIncident.Status.ACKNOWLEDGED
        incident.acknowledged_at = timezone.now()
        incident.save(update_fields=["status", "acknowledged_at", "updated_at"])
    return incident

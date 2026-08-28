from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.utils import timezone

from apps.ticketing.models import Ticket

SLA_WARNING_RATIO = 0.25
MIN_WARNING_MINUTES = 15


@dataclass(frozen=True)
class TicketSLAHealth:
    first_response_status: str
    resolution_status: str
    overall_status: str
    severity: str
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    next_due_at: datetime | None


def _completed_status(completed_at: datetime | None, due_at: datetime | None) -> str:
    if due_at is None:
        return "not_configured"
    if completed_at is None:
        return "pending"
    return "met" if completed_at <= due_at else "breached"


def _active_status(
    *,
    completed_at: datetime | None,
    due_at: datetime | None,
    target_minutes: int | None,
    now: datetime,
) -> str:
    status = _completed_status(completed_at, due_at)
    if status != "pending" or due_at is None:
        return status
    if now > due_at:
        return "breached"
    warning_minutes = max(
        MIN_WARNING_MINUTES,
        int((target_minutes or MIN_WARNING_MINUTES) * SLA_WARNING_RATIO),
    )
    if due_at - now <= timedelta(minutes=warning_minutes):
        return "warning"
    return "healthy"


def evaluate_ticket_sla(
    ticket: Ticket,
    *,
    now: datetime | None = None,
) -> TicketSLAHealth:
    """Evaluate queue-defined SLA state without mutating ticket workflow."""
    current = now or timezone.now()
    first_response_status = _active_status(
        completed_at=ticket.first_response_at,
        due_at=ticket.first_response_due_at,
        target_minutes=ticket.queue.first_response_sla_minutes,
        now=current,
    )
    resolution_completed_at = ticket.resolved_at or ticket.closed_at
    resolution_status = _active_status(
        completed_at=resolution_completed_at,
        due_at=ticket.resolution_due_at,
        target_minutes=ticket.queue.resolution_sla_minutes,
        now=current,
    )

    active = ticket.status not in {
        Ticket.Status.RESOLVED,
        Ticket.Status.CLOSED,
        Ticket.Status.SPAM,
    }
    waiting_customer = active and ticket.status == Ticket.Status.WAITING_CUSTOMER
    active_statuses = [
        status
        for status in (first_response_status, resolution_status)
        if status not in {"not_configured", "met"}
    ]

    if waiting_customer:
        overall_status, severity = "waiting_customer", "info"
    elif active and "breached" in active_statuses:
        overall_status, severity = "breached", "critical"
    elif active and "warning" in active_statuses:
        overall_status, severity = "warning", "warning"
    elif active and active_statuses:
        overall_status, severity = "healthy", "info"
    elif not active and "breached" in {first_response_status, resolution_status}:
        overall_status, severity = "completed_breached", "warning"
    elif not active:
        overall_status, severity = "completed", "info"
    else:
        overall_status, severity = "not_configured", "info"

    pending_due = [
        due
        for due, completed in (
            (ticket.first_response_due_at, ticket.first_response_at),
            (ticket.resolution_due_at, resolution_completed_at),
        )
        if due is not None and completed is None
    ]
    return TicketSLAHealth(
        first_response_status=first_response_status,
        resolution_status=resolution_status,
        overall_status=overall_status,
        severity=severity,
        first_response_due_at=ticket.first_response_due_at,
        resolution_due_at=ticket.resolution_due_at,
        next_due_at=min(pending_due) if pending_due else None,
    )


def reset_ticket_sla_deadlines(
    ticket: Ticket,
    *,
    baseline: datetime | None = None,
) -> Ticket:
    """Apply the current queue's SLA policy when a Ticket enters a new queue."""
    start = baseline or timezone.now()
    ticket.first_response_due_at = (
        start + timedelta(minutes=ticket.queue.first_response_sla_minutes)
        if ticket.first_response_at is None and ticket.queue.first_response_sla_minutes
        else None
    )
    ticket.resolution_due_at = (
        start + timedelta(minutes=ticket.queue.resolution_sla_minutes)
        if ticket.status not in {Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.SPAM}
        and ticket.queue.resolution_sla_minutes
        else None
    )
    ticket.save(update_fields=["first_response_due_at", "resolution_due_at", "updated_at"])
    return ticket

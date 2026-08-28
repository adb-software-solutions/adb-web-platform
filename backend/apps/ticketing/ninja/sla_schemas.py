from __future__ import annotations

from datetime import datetime

from ninja import Schema
from pydantic import Field


class TicketQueueSLAUpdateIn(Schema):
    first_response_sla_minutes: int | None = Field(default=None, ge=1, le=525600)
    resolution_sla_minutes: int | None = Field(default=None, ge=1, le=525600)


class TicketQueueSLAOut(Schema):
    queue_id: int
    queue_name: str
    first_response_sla_minutes: int | None
    resolution_sla_minutes: int | None


class TicketSLAOut(Schema):
    ticket_id: int
    reference: str
    subject: str
    status: str
    priority: str
    queue_id: int
    queue_name: str
    client_id: int | None
    client_name: str | None
    assigned_to_name: str | None
    first_response_due_at: datetime | None
    first_response_at: datetime | None
    first_response_status: str
    resolution_due_at: datetime | None
    resolved_at: datetime | None
    resolution_status: str
    next_due_at: datetime | None
    overall_status: str
    severity: str
    href: str


class TicketSLAListOut(Schema):
    items: list[TicketSLAOut]
    healthy_count: int
    warning_count: int
    breached_count: int
    waiting_customer_count: int

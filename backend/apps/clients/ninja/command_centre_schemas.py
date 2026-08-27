from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from ninja import Schema


class ClientCommandCentreCapabilitiesOut(Schema):
    contacts: bool
    projects: bool
    tasks: bool
    tickets: bool
    time: bool
    infrastructure: bool
    credentials: bool
    knowledge_base: bool
    monitoring: bool
    activity: bool


class ClientCommandCentreStatsOut(Schema):
    active_contacts: int = 0
    current_projects: int = 0
    open_tasks: int = 0
    overdue_tasks: int = 0
    actionable_tickets: int = 0
    waiting_customer_tickets: int = 0
    period_hours: Decimal = Decimal("0")
    period_billable_hours: Decimal = Decimal("0")
    current_resources: int = 0
    active_credentials: int = 0
    knowledge_documents: int = 0
    active_monitor_incidents: int = 0


class ClientCommandCentreProjectOut(Schema):
    id: int
    name: str
    status: str
    start_date: date
    end_date: date | None


class ClientCommandCentreTaskOut(Schema):
    id: int
    title: str
    priority: int
    due_date: date | None
    status_name: str | None
    assigned_to_name: str | None
    project_id: int | None
    project_name: str | None
    is_overdue: bool


class ClientCommandCentreTicketOut(Schema):
    id: int
    reference: str
    subject: str
    status: str
    priority: str
    assigned_to_name: str | None
    last_message_at: datetime | None
    updated_at: datetime


class ClientCommandCentreActivityOut(Schema):
    kind: str
    label: str
    description: str
    occurred_at: datetime
    href: str


class ClientCommandCentreOut(Schema):
    client_id: int
    period_days: int
    period_start: date
    period_end: date
    capabilities: ClientCommandCentreCapabilitiesOut
    stats: ClientCommandCentreStatsOut
    projects: list[ClientCommandCentreProjectOut]
    tasks: list[ClientCommandCentreTaskOut]
    tickets: list[ClientCommandCentreTicketOut]
    activity: list[ClientCommandCentreActivityOut]

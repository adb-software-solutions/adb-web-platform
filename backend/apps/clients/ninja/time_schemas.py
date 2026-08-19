import datetime
import decimal
import typing
from uuid import UUID

from ninja import Schema

TimeOwnershipType = typing.Literal["client", "internal"]


class TimeEntryIn(Schema):
    date: datetime.date
    duration_hours: decimal.Decimal
    description: str = ""
    billable: bool = True
    ownership_type: TimeOwnershipType = "internal"
    client_id: int | None = None
    project_id: int | None = None
    task_id: int | None = None
    ticket_id: int | None = None


class TimerStartIn(Schema):
    description: str = ""
    billable: bool = True
    ownership_type: TimeOwnershipType = "internal"
    client_id: int | None = None
    project_id: int | None = None
    task_id: int | None = None
    ticket_id: int | None = None


class TimerStopIn(Schema):
    description: str | None = None


class TimeEntryOut(Schema):
    id: int
    date: datetime.date
    duration_hours: decimal.Decimal
    description: str
    billable: bool
    entry_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    task_id: int | None
    task_title: str | None
    ticket_id: int | None
    ticket_reference: str | None
    ticket_subject: str | None
    user_id: UUID | None
    user_name: str | None
    created_at: datetime.datetime


class TimeEntryPageOut(Schema):
    items: list[TimeEntryOut]
    total: int
    page: int
    page_size: int
    tracked_hours: decimal.Decimal
    billable_hours: decimal.Decimal


class RunningTimerOut(Schema):
    id: int
    started_at: datetime.datetime
    elapsed_seconds: int
    description: str
    billable: bool
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    task_id: int | None
    task_title: str | None
    ticket_id: int | None
    ticket_reference: str | None
    ticket_subject: str | None


class TimeClientOptionOut(Schema):
    id: int
    name: str


class TimeProjectOptionOut(Schema):
    id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class TimeTaskOptionOut(Schema):
    id: int
    title: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None


class TimeTicketOptionOut(Schema):
    id: int
    reference: str
    subject: str
    client_id: int | None
    client_name: str | None


class TimeTrackingOptionsOut(Schema):
    clients: list[TimeClientOptionOut]
    projects: list[TimeProjectOptionOut]
    tasks: list[TimeTaskOptionOut]
    tickets: list[TimeTicketOptionOut]
    can_add_time: bool

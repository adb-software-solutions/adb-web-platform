from datetime import date, datetime
from typing import Literal

from ninja import Schema
from pydantic import Field

CalendarItemKind = Literal["task", "project", "event"]
CalendarEventType = Literal["event", "meeting", "milestone", "reminder"]
CalendarEventStatus = Literal["scheduled", "completed", "cancelled"]


class CalendarItemOut(Schema):
    kind: CalendarItemKind
    id: int
    title: str
    start_date: date
    end_date: date
    status: str
    completed: bool
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool = True
    event_type: str = ""
    location: str = ""
    meeting_url: str = ""


class CalendarOut(Schema):
    date_from: date
    date_to: date
    items: list[CalendarItemOut]
    task_count: int
    project_count: int
    event_count: int


class CalendarEventCreateIn(Schema):
    ownership_type: Literal["internal", "client"] = "internal"
    client_id: int | None = None
    project_id: int | None = None
    title: str
    description: str = ""
    event_type: CalendarEventType = "event"
    status: CalendarEventStatus = "scheduled"
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    location: str = ""
    meeting_url: str = ""
    attendee_emails: list[str] = Field(default_factory=list)


class CalendarEventUpdateIn(Schema):
    title: str | None = None
    description: str | None = None
    event_type: CalendarEventType | None = None
    status: CalendarEventStatus | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool | None = None
    location: str | None = None
    meeting_url: str | None = None
    attendee_emails: list[str] | None = None
    project_id: int | None = None
    clear_project: bool = False


class CalendarEventDetailOut(Schema):
    id: int
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    title: str
    description: str
    event_type: str
    status: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool
    location: str
    meeting_url: str
    attendee_emails: list[str]
    created_at: datetime
    updated_at: datetime

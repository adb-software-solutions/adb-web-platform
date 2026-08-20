from datetime import date
from typing import Literal

from ninja import Schema

CalendarItemKind = Literal["task", "project"]


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


class CalendarOut(Schema):
    date_from: date
    date_to: date
    items: list[CalendarItemOut]
    task_count: int
    project_count: int

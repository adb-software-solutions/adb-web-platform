from datetime import date, datetime
from typing import Literal
from uuid import UUID

from ninja import Schema

TaskOwnershipType = Literal["client", "internal"]
TaskRecurrenceFrequency = Literal["none", "daily", "weekly", "monthly"]


class TaskIn(Schema):
    title: str
    description: str = ""
    project_id: int | None = None
    ownership_type: TaskOwnershipType = "internal"
    client_id: int | None = None
    task_list_id: int | None = None
    status_id: int | None = None
    priority: int = 2
    due_date: date | None = None
    assigned_to_id: UUID | None = None
    recurrence_frequency: TaskRecurrenceFrequency = "none"


class TaskListIn(Schema):
    name: str
    description: str = ""
    project_id: int | None = None
    ownership_type: TaskOwnershipType = "internal"
    client_id: int | None = None


class TaskSummaryOut(Schema):
    id: int
    title: str
    status: str
    status_id: int | None
    priority: int
    due_date: date | None
    completed_at: datetime | None
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    task_list_id: int | None
    task_list_name: str | None
    assigned_to_id: UUID | None
    assigned_to_name: str | None
    recurrence_frequency: str


class TaskPageOut(Schema):
    items: list[TaskSummaryOut]
    total: int
    page: int
    page_size: int


class TaskDetailOut(TaskSummaryOut):
    description: str
    previous_occurrence_id: int | None
    next_occurrence_id: int | None
    created_by_name: str | None
    created_at: datetime
    updated_at: datetime
    can_change: bool
    can_complete: bool
    can_reopen: bool


class TaskListDetailOut(Schema):
    id: int
    name: str
    description: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    task_count: int
    open_task_count: int
    can_change: bool


class StatusOptionOut(Schema):
    id: int
    name: str
    color: str


class StaffOptionOut(Schema):
    id: UUID
    name: str
    email: str


class ClientOptionOut(Schema):
    id: int
    name: str


class ProjectOptionOut(Schema):
    id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class TaskListOptionOut(Schema):
    id: int
    name: str
    ownership_type: str
    client_id: int | None
    project_id: int | None


class TaskOptionsOut(Schema):
    statuses: list[StatusOptionOut]
    staff: list[StaffOptionOut]
    clients: list[ClientOptionOut]
    projects: list[ProjectOptionOut]
    task_lists: list[TaskListOptionOut]
    can_add_task: bool
    can_add_task_list: bool

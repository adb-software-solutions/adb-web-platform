from datetime import date
from decimal import Decimal

from ninja import Schema


class TaskWorkspaceTaskOut(Schema):
    id: int
    title: str
    status: str
    priority: int
    start_date: date | None
    due_date: date | None
    completed: bool
    assigned_to_name: str | None
    section_id: int | None
    parent_task_id: int | None
    sort_order: Decimal
    subtask_count: int
    blocked_by_count: int


class TaskWorkspaceSectionOut(Schema):
    id: int
    name: str
    sort_order: Decimal
    tasks: list[TaskWorkspaceTaskOut]


class TaskListWorkspaceOut(Schema):
    id: int
    name: str
    description: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    sections: list[TaskWorkspaceSectionOut]
    unsectioned_tasks: list[TaskWorkspaceTaskOut]
    total_tasks: int
    open_tasks: int
    can_change: bool


class ProjectTaskWorkspaceOut(Schema):
    project_id: int
    project_name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    task_lists: list[TaskListWorkspaceOut]
    unlisted_tasks: list[TaskWorkspaceTaskOut]


class TaskRelationsOut(Schema):
    task_id: int
    subtasks: list[TaskWorkspaceTaskOut]
    blocked_by: list[TaskWorkspaceTaskOut]
    blocking: list[TaskWorkspaceTaskOut]
    can_change: bool


class TaskSectionIn(Schema):
    name: str


class QuickTaskIn(Schema):
    title: str
    section_id: int | None = None
    parent_task_id: int | None = None


class QuickSubtaskIn(Schema):
    title: str


class TaskMoveIn(Schema):
    task_list_id: int | None = None
    section_id: int | None = None
    before_task_id: int | None = None
    after_task_id: int | None = None


class TaskDependencyIn(Schema):
    blocking_task_id: int

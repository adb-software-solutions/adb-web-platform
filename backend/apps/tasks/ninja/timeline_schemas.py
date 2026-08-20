from datetime import date

from ninja import Schema


class ProjectTimelineTaskOut(Schema):
    id: int
    title: str
    start_date: date | None
    due_date: date | None
    completed: bool
    priority: int
    assigned_to_name: str | None
    parent_task_id: int | None
    blocked_by_ids: list[int]


class ProjectTimelineOut(Schema):
    project_id: int
    project_name: str
    tasks: list[ProjectTimelineTaskOut]

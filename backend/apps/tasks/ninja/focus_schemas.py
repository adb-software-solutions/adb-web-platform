from typing import Literal

from ninja import Schema

from .schemas import TaskSummaryOut

TaskFocusView = Literal["my", "today", "upcoming", "overdue", "completed", "all"]


class TaskFocusCountsOut(Schema):
    my: int
    today: int
    upcoming: int
    overdue: int
    completed: int


class TaskFocusPageOut(Schema):
    focus: TaskFocusView
    items: list[TaskSummaryOut]
    total: int
    page: int
    page_size: int
    counts: TaskFocusCountsOut

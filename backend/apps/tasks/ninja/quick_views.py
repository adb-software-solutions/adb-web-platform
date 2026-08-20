from __future__ import annotations

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from apps.tasks.services import next_occurrence_datetime
from authentication.ninja.schemas import ProblemDetail

from .admin_views import (
    StaffProblem,
    _build_task_detail,
    _permission_problem,
    _problem,
    _resolve_assignee,
    _scoped_tasks,
    _validation_problem,
)
from .quick_schemas import TaskQuickUpdateIn
from .schemas import TaskDetailOut

quick_router = Router(tags=["admin-task-quick-update"])


@quick_router.patch(
    "/tasks/{task_id}/quick-update",
    response={
        200: TaskDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def quick_update_task(
    request: HttpRequest,
    task_id: int,
    payload: TaskQuickUpdateIn,
) -> TaskDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem

    task = _scoped_tasks(request).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)
    if task.completed_at is not None:
        return _problem(
            "Completed tasks must be reopened before they can be edited.",
            "task_completed",
        )

    fields = payload.model_fields_set
    if "title" in fields:
        if payload.title is None or not payload.title.strip():
            return _problem("Task title is required.", "validation_error")
        task.title = payload.title.strip()
    if "description" in fields:
        task.description = (payload.description or "").strip()
    if "priority" in fields:
        if payload.priority not in {1, 2, 3, 4}:
            return _problem("Task priority must be between 1 and 4.", "validation_error")
        task.priority = payload.priority
    if "start_date" in fields:
        task.start_date = payload.start_date
    if "due_date" in fields:
        task.due_date = payload.due_date
        task.next_occurrence_at = next_occurrence_datetime(
            task.due_date,
            task.recurrence_rule,
        )
    if "assigned_to_id" in fields:
        assignee = _resolve_assignee(payload.assigned_to_id)
        if isinstance(assignee, tuple):
            return assignee
        task.assigned_to = assignee

    try:
        task.full_clean()
    except ValidationError as error:
        return _validation_problem(error, "Invalid task details.")
    task.save()
    return _build_task_detail(request, task)

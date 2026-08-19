from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db.models import Count, Max, Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task, TaskDependency
from apps.tasks.services import default_open_status
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .workspace_schemas import (
    QuickSubtaskIn,
    TaskDependencyIn,
    TaskRelationsOut,
    TaskWorkspaceTaskOut,
)

relations_router = Router(tags=["admin-task-relations"])
StaffProblem = tuple[int, dict[str, Any]]


def _problem(message: str, code: str, status: int = 400) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _permission_problem(request: HttpRequest, permission: str) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem("User not authenticated", "unauthenticated", 401)
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(
            "You do not have permission to access this resource.",
            "forbidden",
            403,
        )
    if not request.user.has_perm(permission):
        return _problem(
            "You do not have permission to perform this action.",
            "forbidden",
            403,
        )
    return None


def _visible_tasks(user: User) -> QuerySet[Task]:
    tasks = Task.objects.select_related(
        "status",
        "assigned_to",
        "client",
        "project",
        "task_list",
        "section",
    )
    if user.is_superuser:
        return tasks
    clients = scope_clients_for_user(user)
    return tasks.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


def _decorated_tasks(user: User) -> QuerySet[Task]:
    return _visible_tasks(user).annotate(
        subtask_count=Count("subtasks", distinct=True),
        blocked_by_count=Count("dependency_links", distinct=True),
    )


def _user_name(user: User | None) -> str | None:
    if user is None:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _task_out(
    task: Task,
    *,
    subtask_count: int | None = None,
    blocked_by_count: int | None = None,
) -> TaskWorkspaceTaskOut:
    return TaskWorkspaceTaskOut(
        id=task.id,
        title=task.title,
        status=task.status.name if task.status else "Unassigned",
        priority=task.priority,
        start_date=task.start_date,
        due_date=task.due_date,
        completed=task.completed_at is not None,
        assigned_to_name=_user_name(task.assigned_to),
        section_id=task.section_id,
        parent_task_id=task.parent_task_id,
        sort_order=task.sort_order,
        subtask_count=(
            subtask_count if subtask_count is not None else getattr(task, "subtask_count", 0)
        ),
        blocked_by_count=(
            blocked_by_count
            if blocked_by_count is not None
            else getattr(task, "blocked_by_count", 0)
        ),
    )


def _next_subtask_order(task: Task) -> Decimal:
    highest = task.subtasks.aggregate(value=Max("sort_order"))["value"]
    return (highest or Decimal(0)) + Decimal(1000)


@relations_router.get(
    "/task-relations/tasks/{task_id}",
    response={
        200: TaskRelationsOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def task_relations(
    request: HttpRequest,
    task_id: int,
) -> TaskRelationsOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).filter(id=task_id).first()
    if task is None:
        return _problem(
            "Task not found or outside your access scope.",
            "not_found",
            404,
        )

    subtasks = list(_decorated_tasks(user).filter(parent_task=task).order_by("sort_order", "id"))
    blocked_by_ids = TaskDependency.objects.filter(blocked_task=task).values_list(
        "blocking_task_id",
        flat=True,
    )
    blocking_ids = TaskDependency.objects.filter(blocking_task=task).values_list(
        "blocked_task_id",
        flat=True,
    )
    blocked_by = list(_decorated_tasks(user).filter(id__in=blocked_by_ids).order_by("title"))
    blocking = list(_decorated_tasks(user).filter(id__in=blocking_ids).order_by("title"))
    return TaskRelationsOut(
        task_id=task.id,
        subtasks=[_task_out(item) for item in subtasks],
        blocked_by=[_task_out(item) for item in blocked_by],
        blocking=[_task_out(item) for item in blocking],
        can_change=user.has_perm("tasks.change_task"),
        can_add_subtask=user.has_perm("tasks.add_task"),
    )


@relations_router.post(
    "/task-relations/tasks/{task_id}/subtasks",
    response={
        201: TaskWorkspaceTaskOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_subtask(
    request: HttpRequest,
    task_id: int,
    payload: QuickSubtaskIn,
) -> tuple[int, TaskWorkspaceTaskOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.add_task")
    if problem:
        return problem
    user = cast(User, request.user)
    parent = _visible_tasks(user).filter(id=task_id).first()
    if parent is None:
        return _problem(
            "Parent task not found or outside your access scope.",
            "not_found",
            404,
        )
    title = payload.title.strip()
    if not title:
        return _problem("Subtask title is required.", "validation_error")

    task = Task(
        ownership_type=parent.ownership_type,
        client=parent.client,
        project=parent.project,
        task_list=parent.task_list,
        section=parent.section,
        parent_task=parent,
        title=title,
        status=default_open_status(),
        assigned_to=parent.assigned_to,
        created_by=user,
        sort_order=_next_subtask_order(parent),
    )
    try:
        task.full_clean()
    except ValidationError as error:
        return _problem("; ".join(error.messages), "validation_error")
    task.save()
    return 201, _task_out(task, subtask_count=0, blocked_by_count=0)


@relations_router.post(
    "/task-relations/tasks/{task_id}/dependencies",
    response={
        204: None,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def add_dependency(
    request: HttpRequest,
    task_id: int,
    payload: TaskDependencyIn,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).filter(id=task_id).first()
    blocking = _visible_tasks(user).filter(id=payload.blocking_task_id).first()
    if task is None or blocking is None:
        return _problem(
            "Task dependency target not found or outside your access scope.",
            "not_found",
            404,
        )

    dependency = TaskDependency(blocked_task=task, blocking_task=blocking)
    try:
        dependency.full_clean()
    except ValidationError as error:
        return _problem("; ".join(error.messages), "validation_error")
    TaskDependency.objects.get_or_create(blocked_task=task, blocking_task=blocking)
    return 204, None


@relations_router.delete(
    "/task-relations/tasks/{task_id}/dependencies/{blocking_task_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def remove_dependency(
    request: HttpRequest,
    task_id: int,
    blocking_task_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).filter(id=task_id).first()
    blocking = _visible_tasks(user).filter(id=blocking_task_id).first()
    if task is None or blocking is None:
        return _problem(
            "Task dependency target not found or outside your access scope.",
            "not_found",
            404,
        )
    deleted, _ = TaskDependency.objects.filter(
        blocked_task=task,
        blocking_task=blocking,
    ).delete()
    if not deleted:
        return _problem("Task dependency not found.", "not_found", 404)
    return 204, None

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Project
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task, TaskDependency, TaskList, TaskSection
from apps.tasks.services import default_open_status
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .workspace_schemas import (
    ProjectTaskWorkspaceOut,
    QuickTaskIn,
    TaskDependencyIn,
    TaskListWorkspaceOut,
    TaskMoveIn,
    TaskSectionIn,
    TaskWorkspaceSectionOut,
    TaskWorkspaceTaskOut,
)

workspace_router = Router(tags=["admin-task-workspaces"])
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


def _visible_task_lists(user: User) -> QuerySet[TaskList]:
    task_lists = TaskList.objects.select_related("client", "project")
    if user.is_superuser:
        return task_lists
    clients = scope_clients_for_user(user)
    return task_lists.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


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


def _visible_projects(user: User) -> QuerySet[Project]:
    projects = Project.objects.select_related("client")
    if user.is_superuser:
        return projects
    clients = scope_clients_for_user(user)
    return projects.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


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


def _tasks_for_workspace(user: User) -> QuerySet[Task]:
    return _visible_tasks(user).annotate(
        subtask_count=Count("subtasks", distinct=True),
        blocked_by_count=Count("dependency_links", distinct=True),
    )


def _list_out(user: User, task_list: TaskList) -> TaskListWorkspaceOut:
    tasks = list(
        _tasks_for_workspace(user)
        .filter(task_list=task_list, parent_task__isnull=True)
        .order_by("sort_order", "id")
    )
    by_section: dict[int, list[TaskWorkspaceTaskOut]] = {}
    unsectioned: list[TaskWorkspaceTaskOut] = []
    for task in tasks:
        output = _task_out(task)
        if task.section_id is None:
            unsectioned.append(output)
        else:
            by_section.setdefault(task.section_id, []).append(output)

    sections = [
        TaskWorkspaceSectionOut(
            id=section.id,
            name=section.name,
            sort_order=section.sort_order,
            tasks=by_section.get(section.id, []),
        )
        for section in task_list.sections.order_by("sort_order", "id")
    ]
    all_tasks = _visible_tasks(user).filter(task_list=task_list)
    return TaskListWorkspaceOut(
        id=task_list.id,
        name=task_list.name,
        description=task_list.description,
        ownership_type=task_list.ownership_type,
        client_id=task_list.client_id,
        client_name=str(task_list.client) if task_list.client else None,
        project_id=task_list.project_id,
        project_name=task_list.project.name if task_list.project else None,
        sections=sections,
        unsectioned_tasks=unsectioned,
        total_tasks=all_tasks.count(),
        open_tasks=all_tasks.filter(completed_at__isnull=True).count(),
        can_change=user.has_perm("tasks.change_tasklist"),
        can_add_task=user.has_perm("tasks.add_task"),
        can_change_task=user.has_perm("tasks.change_task"),
    )


def _next_sort_order(queryset: QuerySet[Task] | QuerySet[TaskSection]) -> Decimal:
    highest = queryset.aggregate(value=Max("sort_order"))["value"]
    return (highest or Decimal(0)) + Decimal(1000)


def _midpoint(before: Decimal | None, after: Decimal | None) -> Decimal:
    if before is None and after is None:
        return Decimal(1000)
    if before is None:
        assert after is not None
        return after - Decimal(1000)
    if after is None:
        return before + Decimal(1000)
    return (before + after) / Decimal(2)


@workspace_router.get(
    "/task-workspaces/lists/{task_list_id}",
    response={
        200: TaskListWorkspaceOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def task_list_workspace(
    request: HttpRequest,
    task_list_id: int,
) -> TaskListWorkspaceOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_tasklist")
    if problem:
        return problem
    user = cast(User, request.user)
    task_list = _visible_task_lists(user).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )
    return _list_out(user, task_list)


@workspace_router.get(
    "/task-workspaces/projects/{project_id}",
    response={
        200: ProjectTaskWorkspaceOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def project_task_workspace(
    request: HttpRequest,
    project_id: int,
) -> ProjectTaskWorkspaceOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem
    user = cast(User, request.user)
    project = _visible_projects(user).filter(id=project_id).first()
    if project is None:
        return _problem(
            "Project not found or outside your access scope.",
            "not_found",
            404,
        )
    task_lists = [
        _list_out(user, task_list)
        for task_list in _visible_task_lists(user)
        .filter(project=project)
        .order_by("sort_order", "id")
    ]
    unlisted_tasks = [
        _task_out(task)
        for task in _tasks_for_workspace(user)
        .filter(project=project, task_list__isnull=True, parent_task__isnull=True)
        .order_by("sort_order", "id")
    ]
    return ProjectTaskWorkspaceOut(
        project_id=project.id,
        project_name=project.name,
        ownership_type=project.ownership_type,
        client_id=project.client_id,
        client_name=str(project.client) if project.client else None,
        task_lists=task_lists,
        unlisted_tasks=unlisted_tasks,
        can_add_task=user.has_perm("tasks.add_task"),
        can_add_task_list=user.has_perm("tasks.add_tasklist"),
        can_change_task=user.has_perm("tasks.change_task"),
        can_view_task_lists=user.has_perm("tasks.view_tasklist"),
    )


@workspace_router.post(
    "/task-workspaces/lists/{task_list_id}/sections",
    response={
        201: TaskWorkspaceSectionOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_task_section(
    request: HttpRequest,
    task_list_id: int,
    payload: TaskSectionIn,
) -> tuple[int, TaskWorkspaceSectionOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.change_tasklist")
    if problem:
        return problem
    user = cast(User, request.user)
    task_list = _visible_task_lists(user).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )
    name = payload.name.strip()
    if not name:
        return _problem("Section name is required.", "validation_error")
    section = TaskSection.objects.create(
        task_list=task_list,
        name=name,
        sort_order=_next_sort_order(task_list.sections.all()),
    )
    return 201, TaskWorkspaceSectionOut(
        id=section.id,
        name=section.name,
        sort_order=section.sort_order,
        tasks=[],
    )


@workspace_router.post(
    "/task-workspaces/lists/{task_list_id}/quick-task",
    response={
        201: TaskWorkspaceTaskOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_quick_task(
    request: HttpRequest,
    task_list_id: int,
    payload: QuickTaskIn,
) -> tuple[int, TaskWorkspaceTaskOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.add_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task_list = _visible_task_lists(user).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )
    title = payload.title.strip()
    if not title:
        return _problem("Task title is required.", "validation_error")

    section = None
    if payload.section_id is not None:
        section = task_list.sections.filter(id=payload.section_id).first()
        if section is None:
            return _problem(
                "Section does not belong to this task list.",
                "context_mismatch",
            )

    parent = None
    if payload.parent_task_id is not None:
        parent = _visible_tasks(user).filter(id=payload.parent_task_id).first()
        if parent is None or parent.task_list_id != task_list.id:
            return _problem(
                "Parent task is not available in this task list.",
                "context_mismatch",
            )

    siblings = _visible_tasks(user).filter(
        task_list=task_list,
        section=section,
        parent_task=parent,
    )
    task = Task(
        ownership_type=task_list.ownership_type,
        client=task_list.client,
        project=task_list.project,
        task_list=task_list,
        section=section,
        parent_task=parent,
        title=title,
        status=default_open_status(),
        created_by=user,
        sort_order=_next_sort_order(siblings),
    )
    try:
        task.full_clean()
    except ValidationError as error:
        return _problem("; ".join(error.messages), "validation_error")
    task.save()
    return 201, _task_out(task, subtask_count=0, blocked_by_count=0)


@workspace_router.post(
    "/task-workspaces/tasks/{task_id}/move",
    response={
        200: TaskWorkspaceTaskOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
@transaction.atomic
def move_task(
    request: HttpRequest,
    task_id: int,
    payload: TaskMoveIn,
) -> TaskWorkspaceTaskOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).select_for_update().filter(id=task_id).first()
    if task is None:
        return _problem(
            "Task not found or outside your access scope.",
            "not_found",
            404,
        )

    task_list = None
    if payload.task_list_id is not None:
        task_list = _visible_task_lists(user).filter(id=payload.task_list_id).first()
        if task_list is None:
            return _problem(
                "Task list not found or outside your access scope.",
                "not_found",
                404,
            )
        if task_list.ownership_type != task.ownership_type or task_list.client_id != task.client_id:
            return _problem(
                "Task cannot move across ownership boundaries.",
                "context_mismatch",
            )
        if task_list.project_id and task_list.project_id != task.project_id:
            return _problem(
                "Task list belongs to a different project.",
                "context_mismatch",
            )

    section = None
    if payload.section_id is not None:
        if task_list is None:
            task_list = task.task_list
        if task_list is None:
            return _problem(
                "A section move requires a task list.",
                "context_mismatch",
            )
        section = task_list.sections.filter(id=payload.section_id).first()
        if section is None:
            return _problem(
                "Section does not belong to the selected task list.",
                "context_mismatch",
            )

    before = None
    after = None
    if payload.before_task_id is not None:
        before = _visible_tasks(user).filter(id=payload.before_task_id).first()
    if payload.after_task_id is not None:
        after = _visible_tasks(user).filter(id=payload.after_task_id).first()
    if before is not None and before.id == task.id:
        before = None
    if after is not None and after.id == task.id:
        after = None

    target_list = task_list
    for neighbour in (before, after):
        if neighbour is None:
            continue
        if neighbour.task_list_id != (target_list.id if target_list else None):
            return _problem(
                "Move neighbours must be in the destination task list.",
                "context_mismatch",
            )
        if neighbour.section_id != (section.id if section else None):
            return _problem(
                "Move neighbours must be in the destination section.",
                "context_mismatch",
            )

    task.task_list = target_list
    task.section = section
    if target_list and target_list.project_id:
        task.project = target_list.project
    task.sort_order = _midpoint(
        before.sort_order if before else None,
        after.sort_order if after else None,
    )
    try:
        task.full_clean()
    except ValidationError as error:
        return _problem("; ".join(error.messages), "validation_error")
    task.save(
        update_fields=[
            "task_list",
            "section",
            "project",
            "sort_order",
            "updated_at",
        ]
    )
    return _task_out(
        task,
        subtask_count=task.subtasks.count(),
        blocked_by_count=task.dependency_links.count(),
    )


@workspace_router.post(
    "/task-workspaces/tasks/{task_id}/dependencies",
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

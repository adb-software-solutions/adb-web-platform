from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client, Project
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task, TaskList, TaskStatus
from apps.tasks.services import (
    build_recurrence_rule,
    complete_task,
    default_open_status,
    next_occurrence_datetime,
    recurrence_frequency,
    reopen_task,
)
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .schemas import (
    ClientOptionOut,
    ProjectOptionOut,
    StaffOptionOut,
    StatusOptionOut,
    TaskDetailOut,
    TaskIn,
    TaskListDetailOut,
    TaskListIn,
    TaskListOptionOut,
    TaskOptionsOut,
    TaskPageOut,
    TaskSummaryOut,
)

tasks_admin_router = Router(tags=["admin-tasks"])

StaffProblem = tuple[int, dict[str, Any]]


@dataclass(frozen=True)
class WorkContext:
    ownership_type: str
    client: Client | None
    project: Project | None


def _problem(message: str, code: str, status: int = 400) -> StaffProblem:
    return status, {
        "message": message,
        "success": False,
        "code": code,
    }


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


def _validation_problem(error: ValidationError, message: str) -> StaffProblem:
    details = getattr(error, "message_dict", None)
    return 400, {
        "message": message,
        "success": False,
        "code": "validation_error",
        **({"details": details} if details else {}),
    }


def _scoped_clients(request: HttpRequest) -> QuerySet[Client]:
    return scope_clients_for_user(request.user)


def _scoped_projects(request: HttpRequest) -> QuerySet[Project]:
    projects = Project.objects.select_related("client")
    if request.user.is_superuser:
        return projects
    return projects.filter(
        Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=_scoped_clients(request))
    )


def _scoped_tasks(request: HttpRequest) -> QuerySet[Task]:
    tasks = Task.objects.select_related(
        "client",
        "project",
        "status",
        "task_list",
        "assigned_to",
        "created_by",
        "previous_occurrence",
    )
    if request.user.is_superuser:
        return tasks
    return tasks.filter(
        Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=_scoped_clients(request))
    )


def _scoped_task_lists(request: HttpRequest) -> QuerySet[TaskList]:
    task_lists = TaskList.objects.select_related("client", "project")
    if request.user.is_superuser:
        return task_lists
    return task_lists.filter(
        Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=_scoped_clients(request))
    )


def _user_name(user: User | None) -> str | None:
    if user is None:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _build_task_summary(task: Task) -> TaskSummaryOut:
    return TaskSummaryOut(
        id=task.id,
        title=task.title,
        status=task.status.name if task.status else "Unassigned",
        status_id=task.status_id,
        priority=task.priority,
        due_date=task.due_date,
        completed_at=task.completed_at,
        ownership_type=task.ownership_type,
        client_id=task.client_id,
        client_name=str(task.client) if task.client else None,
        project_id=task.project_id,
        project_name=task.project.name if task.project else None,
        task_list_id=task.task_list_id,
        task_list_name=task.task_list.name if task.task_list else None,
        assigned_to_id=task.assigned_to_id,
        assigned_to_name=_user_name(task.assigned_to),
        recurrence_frequency=recurrence_frequency(task.recurrence_rule),
    )


def _build_task_detail(request: HttpRequest, task: Task) -> TaskDetailOut:
    next_occurrence = getattr(task, "next_occurrence", None)
    return TaskDetailOut(
        **_build_task_summary(task).dict(),
        description=task.description,
        previous_occurrence_id=task.previous_occurrence_id,
        next_occurrence_id=next_occurrence.id if next_occurrence else None,
        created_by_name=_user_name(task.created_by),
        created_at=task.created_at,
        updated_at=task.updated_at,
        can_change=request.user.has_perm("tasks.change_task"),
        can_complete=(
            task.completed_at is None and request.user.has_perm("tasks.change_task")
        ),
        can_reopen=(
            task.completed_at is not None
            and next_occurrence is None
            and request.user.has_perm("tasks.change_task")
        ),
    )


def _build_task_list_detail(request: HttpRequest, task_list: TaskList) -> TaskListDetailOut:
    tasks = task_list.tasks.all()
    return TaskListDetailOut(
        id=task_list.id,
        name=task_list.name,
        description=task_list.description,
        ownership_type=task_list.ownership_type,
        client_id=task_list.client_id,
        client_name=str(task_list.client) if task_list.client else None,
        project_id=task_list.project_id,
        project_name=task_list.project.name if task_list.project else None,
        task_count=tasks.count(),
        open_task_count=tasks.filter(completed_at__isnull=True).count(),
        can_change=request.user.has_perm("tasks.change_tasklist"),
    )


def _resolve_context(
    request: HttpRequest,
    *,
    project_id: int | None,
    ownership_type: str,
    client_id: int | None,
) -> WorkContext | StaffProblem:
    if project_id is not None:
        project = _scoped_projects(request).filter(id=project_id).first()
        if project is None:
            return _problem(
                "Project not found or outside your access scope.",
                "not_found",
                404,
            )
        return WorkContext(project.ownership_type, project.client, project)

    if ownership_type == OwnershipType.INTERNAL:
        if client_id is not None:
            return _problem("Internal work cannot reference a client.", "invalid_ownership")
        return WorkContext(OwnershipType.INTERNAL, None, None)

    if ownership_type != OwnershipType.CLIENT:
        return _problem("Invalid ownership type.", "invalid_ownership")

    if client_id is None:
        return _problem("Client-owned work requires a client.", "invalid_ownership")
    client = _scoped_clients(request).filter(id=client_id).first()
    if client is None:
        return _problem(
            "Client not found or outside your access scope.",
            "not_found",
            404,
        )
    return WorkContext(OwnershipType.CLIENT, client, None)


def _resolve_task_list(
    request: HttpRequest,
    task_list_id: int | None,
) -> TaskList | None | StaffProblem:
    if task_list_id is None:
        return None
    task_list = _scoped_task_lists(request).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )
    return task_list


def _resolve_status(status_id: int | None) -> TaskStatus | None | StaffProblem:
    if status_id is None:
        return default_open_status()
    status = TaskStatus.objects.filter(id=status_id).first()
    if status is None:
        return _problem("Task status not found.", "not_found", 404)
    return status


def _resolve_assignee(assignee_id: UUID | None) -> User | None | StaffProblem:
    if assignee_id is None:
        return None
    assignee = User.objects.filter(
        id=assignee_id,
        is_staff=True,
        is_active=True,
    ).first()
    if assignee is None:
        return _problem("Assigned staff member not found.", "not_found", 404)
    return assignee


def _apply_task_payload(
    request: HttpRequest,
    task: Task,
    payload: TaskIn,
) -> StaffProblem | None:
    title = payload.title.strip()
    if not title:
        return _problem("Task title is required.", "validation_error")
    if payload.priority not in {1, 2, 3, 4}:
        return _problem("Task priority must be between 1 and 4.", "validation_error")

    context = _resolve_context(
        request,
        project_id=payload.project_id,
        ownership_type=payload.ownership_type,
        client_id=payload.client_id,
    )
    if isinstance(context, tuple):
        return context
    ownership_type = context.ownership_type
    client = context.client
    project = context.project

    task_list_result = _resolve_task_list(request, payload.task_list_id)
    if isinstance(task_list_result, tuple):
        return task_list_result
    task_list = task_list_result

    status_result = _resolve_status(payload.status_id)
    if isinstance(status_result, tuple):
        return status_result
    status = status_result

    assignee_result = _resolve_assignee(payload.assigned_to_id)
    if isinstance(assignee_result, tuple):
        return assignee_result
    assignee = assignee_result

    recurrence_rule = build_recurrence_rule(payload.recurrence_frequency)
    if recurrence_rule and payload.due_date is None:
        return _problem(
            "Recurring tasks require a due date.",
            "recurrence_requires_due_date",
        )

    task.title = title
    task.description = payload.description.strip()
    task.ownership_type = ownership_type
    task.client = client
    task.project = project
    task.task_list = task_list
    task.status = status
    task.priority = payload.priority
    task.due_date = payload.due_date
    task.assigned_to = assignee
    task.recurrence_rule = recurrence_rule
    task.next_occurrence_at = next_occurrence_datetime(
        payload.due_date,
        recurrence_rule,
    )
    return None


def _apply_task_list_payload(
    request: HttpRequest,
    task_list: TaskList,
    payload: TaskListIn,
) -> StaffProblem | None:
    name = payload.name.strip()
    if not name:
        return _problem("Task list name is required.", "validation_error")

    context = _resolve_context(
        request,
        project_id=payload.project_id,
        ownership_type=payload.ownership_type,
        client_id=payload.client_id,
    )
    if isinstance(context, tuple):
        return context
    ownership_type = context.ownership_type
    client = context.client
    project = context.project

    task_list.name = name
    task_list.description = payload.description.strip()
    task_list.ownership_type = ownership_type
    task_list.client = client
    task_list.project = project
    return None


@tasks_admin_router.get(
    "/tasks",
    response={200: TaskPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_tasks(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    ownership_type: str | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    task_list_id: int | None = None,
    assigned_to_id: UUID | None = None,
    completed: bool | None = None,
) -> TaskPageOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    tasks = _scoped_tasks(request)

    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if ownership_type in {OwnershipType.INTERNAL, OwnershipType.CLIENT}:
        tasks = tasks.filter(ownership_type=ownership_type)
    if client_id is not None:
        tasks = tasks.filter(client_id=client_id)
    if project_id is not None:
        tasks = tasks.filter(project_id=project_id)
    if task_list_id is not None:
        tasks = tasks.filter(task_list_id=task_list_id)
    if assigned_to_id is not None:
        tasks = tasks.filter(assigned_to_id=assigned_to_id)
    if completed is not None:
        tasks = tasks.filter(completed_at__isnull=not completed)

    tasks = tasks.order_by("completed_at", "due_date", "-priority", "-created_at")
    total = tasks.count()
    start = (page - 1) * page_size
    items = [_build_task_summary(task) for task in tasks[start : start + page_size]]
    return TaskPageOut(items=items, total=total, page=page, page_size=page_size)


@tasks_admin_router.post(
    "/tasks",
    response={
        201: TaskDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_task(
    request: HttpRequest,
    payload: TaskIn,
) -> tuple[int, TaskDetailOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.add_task")
    if problem:
        return problem

    task = Task(created_by=cast(User, request.user))
    payload_problem = _apply_task_payload(request, task, payload)
    if payload_problem:
        return payload_problem
    try:
        task.full_clean()
    except ValidationError as error:
        return _validation_problem(error, "Invalid task details.")
    task.save()
    return 201, _build_task_detail(request, task)


@tasks_admin_router.get(
    "/tasks/{task_id}",
    response={200: TaskDetailOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def get_task(request: HttpRequest, task_id: int) -> TaskDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem
    task = _scoped_tasks(request).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)
    return _build_task_detail(request, task)


@tasks_admin_router.put(
    "/tasks/{task_id}",
    response={
        200: TaskDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_task(
    request: HttpRequest,
    task_id: int,
    payload: TaskIn,
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

    payload_problem = _apply_task_payload(request, task, payload)
    if payload_problem:
        return payload_problem
    try:
        task.full_clean()
    except ValidationError as error:
        return _validation_problem(error, "Invalid task details.")
    task.save()
    return _build_task_detail(request, task)


@tasks_admin_router.post(
    "/tasks/{task_id}/complete",
    response={
        200: TaskDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def complete_task_view(request: HttpRequest, task_id: int) -> TaskDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    task = _scoped_tasks(request).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)
    completed, _ = complete_task(task)
    return _build_task_detail(request, completed)


@tasks_admin_router.post(
    "/tasks/{task_id}/reopen",
    response={
        200: TaskDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def reopen_task_view(request: HttpRequest, task_id: int) -> TaskDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    task = _scoped_tasks(request).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)
    try:
        reopened = reopen_task(task)
    except ValidationError as error:
        return _validation_problem(error, "Task cannot be reopened.")
    return _build_task_detail(request, reopened)


@tasks_admin_router.get(
    "/task-lists",
    response={200: list[TaskListDetailOut], 401: ProblemDetail, 403: ProblemDetail},
)
def list_task_lists(request: HttpRequest) -> list[TaskListDetailOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.view_tasklist")
    if problem:
        return problem
    return [
        _build_task_list_detail(request, task_list)
        for task_list in _scoped_task_lists(request).order_by("name")
    ]


@tasks_admin_router.post(
    "/task-lists",
    response={
        201: TaskListDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_task_list(
    request: HttpRequest,
    payload: TaskListIn,
) -> tuple[int, TaskListDetailOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.add_tasklist")
    if problem:
        return problem

    task_list = TaskList()
    payload_problem = _apply_task_list_payload(request, task_list, payload)
    if payload_problem:
        return payload_problem
    try:
        task_list.full_clean()
    except ValidationError as error:
        return _validation_problem(error, "Invalid task list details.")
    task_list.save()
    return 201, _build_task_list_detail(request, task_list)


@tasks_admin_router.get(
    "/task-lists/{task_list_id}",
    response={
        200: TaskListDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_task_list(
    request: HttpRequest,
    task_list_id: int,
) -> TaskListDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_tasklist")
    if problem:
        return problem
    task_list = _scoped_task_lists(request).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )
    return _build_task_list_detail(request, task_list)


@tasks_admin_router.put(
    "/task-lists/{task_list_id}",
    response={
        200: TaskListDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_task_list(
    request: HttpRequest,
    task_list_id: int,
    payload: TaskListIn,
) -> TaskListDetailOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_tasklist")
    if problem:
        return problem
    task_list = _scoped_task_lists(request).filter(id=task_list_id).first()
    if task_list is None:
        return _problem(
            "Task list not found or outside your access scope.",
            "not_found",
            404,
        )

    payload_problem = _apply_task_list_payload(request, task_list, payload)
    if payload_problem:
        return payload_problem
    try:
        task_list.full_clean()
    except ValidationError as error:
        return _validation_problem(error, "Invalid task list details.")
    task_list.save()
    return _build_task_list_detail(request, task_list)


@tasks_admin_router.get(
    "/task-options",
    response={200: TaskOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def task_options(request: HttpRequest) -> TaskOptionsOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem

    clients = _scoped_clients(request).order_by("company", "name")
    projects = _scoped_projects(request).order_by("name")
    task_lists = _scoped_task_lists(request).order_by("name")
    staff = User.objects.filter(is_staff=True, is_active=True).order_by(
        "first_name",
        "last_name",
        "email",
    )

    return TaskOptionsOut(
        statuses=[
            StatusOptionOut(id=status.id, name=status.name, color=status.color)
            for status in TaskStatus.objects.order_by("order")
        ],
        staff=[
            StaffOptionOut(
                id=user.id,
                name=_user_name(user) or user.email,
                email=user.email,
            )
            for user in staff
        ],
        clients=[ClientOptionOut(id=client.id, name=str(client)) for client in clients],
        projects=[
            ProjectOptionOut(
                id=project.id,
                name=project.name,
                ownership_type=project.ownership_type,
                client_id=project.client_id,
                client_name=str(project.client) if project.client else None,
            )
            for project in projects
        ],
        task_lists=[
            TaskListOptionOut(
                id=task_list.id,
                name=task_list.name,
                ownership_type=task_list.ownership_type,
                client_id=task_list.client_id,
                project_id=task_list.project_id,
            )
            for task_list in task_lists
        ],
        can_add_task=request.user.has_perm("tasks.add_task"),
        can_add_task_list=request.user.has_perm("tasks.add_tasklist"),
    )

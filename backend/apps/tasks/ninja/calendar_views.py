from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db.models import Q
from django.http import HttpRequest
from ninja import Router

from authentication.ninja.schemas import ProblemDetail

from .admin_views import _scoped_projects, _scoped_tasks
from .calendar_schemas import CalendarItemOut, CalendarOut

calendar_router = Router(tags=["admin-calendar"])
StaffProblem = tuple[int, dict[str, Any]]
MAX_CALENDAR_DAYS = 62


def _problem(message: str, code: str, status: int = 400) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem("User not authenticated", "unauthenticated", 401)
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(
            "You do not have permission to access this resource.",
            "forbidden",
            403,
        )
    if not (
        request.user.has_perm("tasks.view_task")
        or request.user.has_perm("clients.view_project")
    ):
        return _problem(
            "You do not have permission to view work calendar items.",
            "forbidden",
            403,
        )
    return None


def _task_calendar_items(request: HttpRequest, date_from: date, date_to: date) -> list[CalendarItemOut]:
    if not request.user.has_perm("tasks.view_task"):
        return []

    tasks = (
        _scoped_tasks(request)
        .filter(
            Q(start_date__range=(date_from, date_to))
            | Q(due_date__range=(date_from, date_to))
            | Q(start_date__lte=date_from, due_date__gte=date_to)
        )
        .order_by("start_date", "due_date", "title")
    )
    items: list[CalendarItemOut] = []
    for task in tasks:
        item_start = task.start_date or task.due_date
        item_end = task.due_date or task.start_date
        if item_start is None or item_end is None:
            continue
        items.append(
            CalendarItemOut(
                kind="task",
                id=task.id,
                title=task.title,
                start_date=item_start,
                end_date=item_end,
                status=task.status.name if task.status else "Unassigned",
                completed=task.completed_at is not None,
                client_id=task.client_id,
                client_name=str(task.client) if task.client else None,
                project_id=task.project_id,
                project_name=task.project.name if task.project else None,
            )
        )
    return items


def _project_calendar_items(
    request: HttpRequest,
    date_from: date,
    date_to: date,
) -> list[CalendarItemOut]:
    if not request.user.has_perm("clients.view_project"):
        return []

    projects = (
        _scoped_projects(request)
        .filter(
            Q(start_date__range=(date_from, date_to))
            | Q(end_date__range=(date_from, date_to))
            | Q(start_date__lte=date_from, end_date__gte=date_to)
        )
        .order_by("start_date", "name")
    )
    return [
        CalendarItemOut(
            kind="project",
            id=project.id,
            title=project.name,
            start_date=project.start_date,
            end_date=project.end_date or project.start_date,
            status=project.status,
            completed=project.status == "completed",
            client_id=project.client_id,
            client_name=str(project.client) if project.client else None,
            project_id=project.id,
            project_name=project.name,
        )
        for project in projects
    ]


@calendar_router.get(
    "/calendar",
    response={
        200: CalendarOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def work_calendar(
    request: HttpRequest,
    date_from: date,
    date_to: date,
) -> CalendarOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    if date_from > date_to:
        return _problem("date_from cannot be after date_to.", "invalid_period")
    if date_to - date_from > timedelta(days=MAX_CALENDAR_DAYS):
        return _problem(
            f"Calendar ranges cannot exceed {MAX_CALENDAR_DAYS + 1} days.",
            "invalid_period",
        )

    task_items = _task_calendar_items(request, date_from, date_to)
    project_items = _project_calendar_items(request, date_from, date_to)
    items = sorted(
        [*project_items, *task_items],
        key=lambda item: (item.start_date, item.kind != "project", item.title.lower()),
    )
    return CalendarOut(
        date_from=date_from,
        date_to=date_to,
        items=items,
        task_count=len(task_items),
        project_count=len(project_items),
    )

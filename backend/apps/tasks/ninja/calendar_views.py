from __future__ import annotations

from datetime import date, timedelta
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client, Project
from apps.core.models import AuditEvent
from apps.core.ownership import OwnershipType
from apps.tasks.models import CalendarEvent
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .admin_views import _scoped_projects, _scoped_tasks
from .calendar_schemas import (
    CalendarEventCreateIn,
    CalendarEventDetailOut,
    CalendarEventUpdateIn,
    CalendarItemOut,
    CalendarOut,
)

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
        or request.user.has_perm("tasks.view_calendarevent")
    ):
        return _problem(
            "You do not have permission to view work calendar items.",
            "forbidden",
            403,
        )
    return None


def _scoped_events(request: HttpRequest) -> QuerySet[CalendarEvent]:
    events = CalendarEvent.objects.select_related("client", "project")
    if request.user.is_superuser:
        return events
    return events.filter(
        Q(ownership_type=OwnershipType.INTERNAL)
        | Q(client__in=scope_clients_for_user(request.user))
    ).distinct()


def _event_out(event: CalendarEvent) -> CalendarEventDetailOut:
    return CalendarEventDetailOut(
        id=event.id,
        ownership_type=event.ownership_type,
        client_id=event.client_id,
        client_name=str(event.client) if event.client else None,
        project_id=event.project_id,
        project_name=event.project.name if event.project else None,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        status=event.status,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        all_day=event.all_day,
        location=event.location,
        meeting_url=event.meeting_url,
        attendee_emails=list(event.attendee_emails),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _task_calendar_items(
    request: HttpRequest, date_from: date, date_to: date
) -> list[CalendarItemOut]:
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


def _event_calendar_items(
    request: HttpRequest,
    date_from: date,
    date_to: date,
) -> list[CalendarItemOut]:
    if not request.user.has_perm("tasks.view_calendarevent"):
        return []
    events = _scoped_events(request).filter(
        starts_at__date__lte=date_to,
        ends_at__date__gte=date_from,
    )
    return [
        CalendarItemOut(
            kind="event",
            id=event.id,
            title=event.title,
            start_date=event.starts_at.date(),
            end_date=event.ends_at.date(),
            status=event.status,
            completed=event.status == CalendarEvent.Status.COMPLETED,
            client_id=event.client_id,
            client_name=str(event.client) if event.client else None,
            project_id=event.project_id,
            project_name=event.project.name if event.project else None,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            all_day=event.all_day,
            event_type=event.event_type,
            location=event.location,
            meeting_url=event.meeting_url,
        )
        for event in events.order_by("starts_at", "title", "id")
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
    event_items = _event_calendar_items(request, date_from, date_to)
    items = sorted(
        [*project_items, *event_items, *task_items],
        key=lambda item: (
            item.start_date,
            item.starts_at.isoformat() if item.starts_at else "",
            item.kind != "event",
            item.title.lower(),
        ),
    )
    return CalendarOut(
        date_from=date_from,
        date_to=date_to,
        items=items,
        task_count=len(task_items),
        project_count=len(project_items),
        event_count=len(event_items),
    )


def _resolve_event_scope(
    request: HttpRequest,
    ownership_type: str,
    client_id: int | None,
    project_id: int | None,
) -> tuple[Client | None, Project | None, StaffProblem | None]:
    client: Client | None = None
    if ownership_type == OwnershipType.CLIENT:
        if client_id is None:
            return None, None, _problem(
                "Client events require a Client.",
                "client_required",
            )
        client = scope_clients_for_user(request.user).filter(id=client_id).first()
        if client is None:
            return None, None, _problem("Client not found.", "not_found", 404)
    elif client_id is not None:
        return None, None, _problem(
            "Internal events cannot select a Client.",
            "invalid_ownership",
        )

    project: Project | None = None
    if project_id is not None:
        project = _scoped_projects(request).filter(id=project_id).first()
        if project is None:
            return None, None, _problem("Project not found.", "not_found", 404)
        if project.ownership_type != ownership_type or project.client_id != client_id:
            return None, None, _problem(
                "Project ownership must match the Event context.",
                "invalid_project",
            )
    return client, project, None


@calendar_router.post(
    "/calendar/events",
    response={
        201: CalendarEventDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_calendar_event(
    request: HttpRequest,
    payload: CalendarEventCreateIn,
) -> tuple[int, CalendarEventDetailOut | dict[str, object]]:
    if not request.user.is_authenticated:
        return 401, {
            "message": "User not authenticated",
            "success": False,
            "code": "unauthenticated",
        }
    if not request.user.has_perm("tasks.add_calendarevent"):
        return 403, {
            "message": "You do not have permission to create calendar events.",
            "success": False,
            "code": "forbidden",
        }
    client, project, scope_problem = _resolve_event_scope(
        request,
        payload.ownership_type,
        payload.client_id,
        payload.project_id,
    )
    if scope_problem:
        return scope_problem
    event = CalendarEvent(
        ownership_type=payload.ownership_type,
        client=client,
        project=project,
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        status=payload.status,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
        location=payload.location,
        meeting_url=payload.meeting_url,
        attendee_emails=payload.attendee_emails,
        created_by=cast(User, request.user),
        updated_by=cast(User, request.user),
    )
    try:
        event.full_clean()
    except ValidationError as error:
        return 400, {
            "message": " ".join(error.messages),
            "success": False,
            "code": "invalid_event",
        }
    event.save()
    AuditEvent.record(action="calendar.event_created", actor=request.user, target=event)
    return 201, _event_out(event)


@calendar_router.get(
    "/calendar/events/{event_id}",
    response={
        200: CalendarEventDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_calendar_event(
    request: HttpRequest,
    event_id: int,
) -> CalendarEventDetailOut | StaffProblem:
    if not request.user.is_authenticated:
        return _problem("User not authenticated", "unauthenticated", 401)
    if not request.user.has_perm("tasks.view_calendarevent"):
        return _problem(
            "You do not have permission to view calendar events.",
            "forbidden",
            403,
        )
    event = _scoped_events(request).filter(id=event_id).first()
    if event is None:
        return _problem("Calendar event not found.", "not_found", 404)
    return _event_out(event)


@calendar_router.put(
    "/calendar/events/{event_id}",
    response={
        200: CalendarEventDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_calendar_event(
    request: HttpRequest,
    event_id: int,
    payload: CalendarEventUpdateIn,
) -> CalendarEventDetailOut | StaffProblem:
    if not request.user.is_authenticated:
        return _problem("User not authenticated", "unauthenticated", 401)
    if not request.user.has_perm("tasks.change_calendarevent"):
        return _problem(
            "You do not have permission to change calendar events.",
            "forbidden",
            403,
        )
    event = _scoped_events(request).filter(id=event_id).first()
    if event is None:
        return _problem("Calendar event not found.", "not_found", 404)

    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.event_type is not None:
        event.event_type = payload.event_type
    if payload.status is not None:
        event.status = payload.status
    if payload.starts_at is not None:
        event.starts_at = payload.starts_at
    if payload.ends_at is not None:
        event.ends_at = payload.ends_at
    if payload.all_day is not None:
        event.all_day = payload.all_day
    if payload.location is not None:
        event.location = payload.location
    if payload.meeting_url is not None:
        event.meeting_url = payload.meeting_url
    if payload.attendee_emails is not None:
        event.attendee_emails = payload.attendee_emails
    if payload.clear_project:
        event.project = None
    elif payload.project_id is not None:
        project = _scoped_projects(request).filter(id=payload.project_id).first()
        if project is None:
            return _problem("Project not found.", "not_found", 404)
        event.project = project
    event.updated_by = cast(User, request.user)
    try:
        event.full_clean()
    except ValidationError as error:
        return _problem(" ".join(error.messages), "invalid_event")
    event.save()
    AuditEvent.record(action="calendar.event_updated", actor=request.user, target=event)
    return _event_out(event)


@calendar_router.delete(
    "/calendar/events/{event_id}",
    response={204: None, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def delete_calendar_event(
    request: HttpRequest,
    event_id: int,
) -> tuple[int, None] | StaffProblem:
    if not request.user.is_authenticated:
        return _problem("User not authenticated", "unauthenticated", 401)
    if not request.user.has_perm("tasks.delete_calendarevent"):
        return _problem(
            "You do not have permission to delete calendar events.",
            "forbidden",
            403,
        )
    event = _scoped_events(request).filter(id=event_id).first()
    if event is None:
        return _problem("Calendar event not found.", "not_found", 404)
    event_client_id = event.client_id
    event_label = str(event)
    event_pk = event.pk
    event.delete()
    AuditEvent.record(
        action="calendar.event_deleted",
        actor=request.user,
        target_label=event_label,
        client_id=event_client_id,
        metadata={"event_id": event_pk},
    )
    return 204, None

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import RunningTimer, TimeEntry
from apps.clients.services.time_tracking import (
    TimeTrackingError,
    apply_time_context,
    cancel_timer,
    resolve_time_context,
    start_timer,
    stop_timer,
    visible_projects,
    visible_tasks,
    visible_tickets,
    visible_time_entries,
)
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .time_schemas import (
    RunningTimerOut,
    TimeClientOptionOut,
    TimeEntryIn,
    TimeEntryOut,
    TimeEntryPageOut,
    TimeProjectOptionOut,
    TimerStartIn,
    TimerStopIn,
    TimeTaskOptionOut,
    TimeTicketOptionOut,
    TimeTrackingOptionsOut,
)

time_tracking_router = Router(tags=["admin-time-tracking"])

StaffProblem = tuple[int, dict[str, Any]]


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


def _context_permission_problem(
    request: HttpRequest,
    *,
    client_id: int | None,
    project_id: int | None,
    task_id: int | None,
    ticket_id: int | None,
) -> StaffProblem | None:
    if ticket_id is not None and not request.user.has_perm("ticketing.view_ticket"):
        return _problem(
            "You do not have permission to track time against tickets.",
            "forbidden",
            403,
        )
    if task_id is not None and not request.user.has_perm("tasks.view_task"):
        return _problem(
            "You do not have permission to track time against tasks.",
            "forbidden",
            403,
        )
    if project_id is not None and not request.user.has_perm("clients.view_project"):
        return _problem(
            "You do not have permission to track time against projects.",
            "forbidden",
            403,
        )
    if (
        client_id is not None
        and project_id is None
        and task_id is None
        and ticket_id is None
        and not request.user.has_perm("clients.view_client")
    ):
        return _problem(
            "You do not have permission to track time against clients.",
            "forbidden",
            403,
        )
    return None


def _tracking_error_problem(error: TimeTrackingError) -> StaffProblem:
    if error.code == "not_found":
        return _problem(str(error), error.code, 404)
    if error.code == "timer_already_running":
        return _problem(str(error), error.code, 409)
    return _problem(str(error), error.code)


def _user_name(user: User | None) -> str | None:
    if user is None:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _entry_out(entry: TimeEntry) -> TimeEntryOut:
    return TimeEntryOut(
        id=entry.id,
        date=entry.date,
        duration_hours=entry.duration_hours,
        description=entry.description,
        billable=entry.billable,
        entry_type=entry.entry_type,
        ownership_type=entry.ownership_type,
        client_id=entry.client_id,
        client_name=str(entry.client) if entry.client else None,
        project_id=entry.project_id,
        project_name=entry.project.name if entry.project else None,
        task_id=entry.task_id,
        task_title=entry.task.title if entry.task else None,
        ticket_id=entry.ticket_id,
        ticket_reference=entry.ticket.reference if entry.ticket else None,
        ticket_subject=entry.ticket.subject if entry.ticket else None,
        user_id=entry.user_id,
        user_name=_user_name(entry.user),
        created_at=entry.created_at,
    )


def _timer_out(timer: RunningTimer) -> RunningTimerOut:
    elapsed_seconds = max(0, int((timezone.now() - timer.started_at).total_seconds()))
    return RunningTimerOut(
        id=timer.id,
        started_at=timer.started_at,
        elapsed_seconds=elapsed_seconds,
        description=timer.description,
        billable=timer.billable,
        ownership_type=timer.ownership_type,
        client_id=timer.client_id,
        client_name=str(timer.client) if timer.client else None,
        project_id=timer.project_id,
        project_name=timer.project.name if timer.project else None,
        task_id=timer.task_id,
        task_title=timer.task.title if timer.task else None,
        ticket_id=timer.ticket_id,
        ticket_reference=timer.ticket.reference if timer.ticket else None,
        ticket_subject=timer.ticket.subject if timer.ticket else None,
    )


@time_tracking_router.get(
    "/time-records",
    response={200: TimeEntryPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_time_records(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 50,
    ownership_type: str | None = None,
    client_id: int | None = None,
    project_id: int | None = None,
    task_id: int | None = None,
    ticket_id: int | None = None,
) -> TimeEntryPageOut | StaffProblem:
    problem = _permission_problem(request, "clients.view_timeentry")
    if problem:
        return problem

    entries = visible_time_entries(cast(User, request.user))
    if ownership_type in {"internal", "client"}:
        entries = entries.filter(ownership_type=ownership_type)
    if client_id is not None:
        entries = entries.filter(client_id=client_id)
    if project_id is not None:
        entries = entries.filter(project_id=project_id)
    if task_id is not None:
        entries = entries.filter(task_id=task_id)
    if ticket_id is not None:
        entries = entries.filter(ticket_id=ticket_id)

    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    total = entries.count()
    totals = entries.aggregate(
        tracked=Sum("duration_hours"),
        billable=Sum("duration_hours", filter=Q(billable=True)),
    )
    start = (page - 1) * page_size
    rows = entries.order_by("-date", "-created_at")[start : start + page_size]
    return TimeEntryPageOut(
        items=[_entry_out(entry) for entry in rows],
        total=total,
        page=page,
        page_size=page_size,
        tracked_hours=totals["tracked"] or Decimal(0),
        billable_hours=totals["billable"] or Decimal(0),
    )


@time_tracking_router.post(
    "/time-entries",
    response={
        201: TimeEntryOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_time_entry(
    request: HttpRequest,
    payload: TimeEntryIn,
) -> tuple[int, TimeEntryOut] | StaffProblem:
    problem = _permission_problem(request, "clients.add_timeentry")
    if problem:
        return problem
    context_problem = _context_permission_problem(
        request,
        client_id=payload.client_id,
        project_id=payload.project_id,
        task_id=payload.task_id,
        ticket_id=payload.ticket_id,
    )
    if context_problem:
        return context_problem
    if payload.duration_hours <= 0:
        return _problem("Tracked time must be greater than zero.", "validation_error")

    user = cast(User, request.user)
    try:
        context = resolve_time_context(
            user,
            ownership_type=payload.ownership_type,
            client_id=payload.client_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            ticket_id=payload.ticket_id,
        )
    except TimeTrackingError as error:
        return _tracking_error_problem(error)

    entry = TimeEntry(
        user=user,
        date=payload.date,
        duration_hours=payload.duration_hours,
        description=payload.description.strip(),
        billable=payload.billable,
        entry_type=TimeEntry.EntryType.MANUAL,
    )
    apply_time_context(entry, context)
    try:
        entry.full_clean()
    except ValidationError as error:
        return _problem("; ".join(error.messages), "validation_error")
    entry.save()
    return 201, _entry_out(entry)


@time_tracking_router.get(
    "/time-entry-options",
    response={200: TimeTrackingOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def time_entry_options(request: HttpRequest) -> TimeTrackingOptionsOut | StaffProblem:
    problem = _permission_problem(request, "clients.view_timeentry")
    if problem:
        return problem

    user = cast(User, request.user)
    clients = (
        scope_clients_for_user(user).order_by("company", "name")
        if request.user.has_perm("clients.view_client")
        else []
    )
    projects = (
        visible_projects(user).order_by("name")
        if request.user.has_perm("clients.view_project")
        else []
    )
    tasks = (
        visible_tasks(user).filter(completed_at__isnull=True).order_by("due_date", "title")
        if request.user.has_perm("tasks.view_task")
        else []
    )
    tickets = (
        visible_tickets(user).order_by("-last_message_at", "-created_at")[:100]
        if request.user.has_perm("ticketing.view_ticket")
        else []
    )

    return TimeTrackingOptionsOut(
        clients=[TimeClientOptionOut(id=client.id, name=str(client)) for client in clients],
        projects=[
            TimeProjectOptionOut(
                id=project.id,
                name=project.name,
                ownership_type=project.ownership_type,
                client_id=project.client_id,
                client_name=str(project.client) if project.client else None,
            )
            for project in projects
        ],
        tasks=[
            TimeTaskOptionOut(
                id=task.id,
                title=task.title,
                ownership_type=task.ownership_type,
                client_id=task.client_id,
                client_name=str(task.client) if task.client else None,
                project_id=task.project_id,
                project_name=task.project.name if task.project else None,
            )
            for task in tasks
        ],
        tickets=[
            TimeTicketOptionOut(
                id=ticket.id,
                reference=ticket.reference,
                subject=ticket.subject,
                client_id=ticket.client_id,
                client_name=str(ticket.client) if ticket.client else None,
            )
            for ticket in tickets
        ],
        can_add_time=request.user.has_perm("clients.add_timeentry"),
    )


@time_tracking_router.get(
    "/time-timer",
    response={200: RunningTimerOut | None, 401: ProblemDetail, 403: ProblemDetail},
)
def current_timer(request: HttpRequest) -> RunningTimerOut | StaffProblem | None:
    problem = _permission_problem(request, "clients.view_timeentry")
    if problem:
        return problem
    timer = (
        RunningTimer.objects.select_related("client", "project", "task", "ticket")
        .filter(user=cast(User, request.user))
        .first()
    )
    return _timer_out(timer) if timer else None


@time_tracking_router.post(
    "/time-timer/start",
    response={
        201: RunningTimerOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        409: ProblemDetail,
    },
)
def start_time_timer(
    request: HttpRequest,
    payload: TimerStartIn,
) -> tuple[int, RunningTimerOut] | StaffProblem:
    problem = _permission_problem(request, "clients.add_timeentry")
    if problem:
        return problem
    context_problem = _context_permission_problem(
        request,
        client_id=payload.client_id,
        project_id=payload.project_id,
        task_id=payload.task_id,
        ticket_id=payload.ticket_id,
    )
    if context_problem:
        return context_problem

    user = cast(User, request.user)
    try:
        context = resolve_time_context(
            user,
            ownership_type=payload.ownership_type,
            client_id=payload.client_id,
            project_id=payload.project_id,
            task_id=payload.task_id,
            ticket_id=payload.ticket_id,
        )
        timer = start_timer(
            user,
            context,
            description=payload.description,
            billable=payload.billable,
        )
    except TimeTrackingError as error:
        return _tracking_error_problem(error)
    return 201, _timer_out(timer)


@time_tracking_router.post(
    "/time-timer/stop",
    response={
        200: TimeEntryOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def stop_time_timer(
    request: HttpRequest,
    payload: TimerStopIn,
) -> TimeEntryOut | StaffProblem:
    problem = _permission_problem(request, "clients.add_timeentry")
    if problem:
        return problem
    try:
        entry = stop_timer(cast(User, request.user), description=payload.description)
    except TimeTrackingError as error:
        return _tracking_error_problem(error)
    return _entry_out(entry)


@time_tracking_router.post(
    "/time-timer/cancel",
    response={204: None, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail},
)
def cancel_time_timer(request: HttpRequest) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "clients.add_timeentry")
    if problem:
        return problem
    try:
        cancel_timer(cast(User, request.user))
    except TimeTrackingError as error:
        return _tracking_error_problem(error)
    return 204, None

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

from django.db.models import Count, Q, QuerySet, Sum
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.clients.models import TimeEntry
from apps.clients.services.time_tracking import visible_time_entries
from apps.core.ownership import OwnershipType
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .time_report_schemas import (
    TimeReportClientOut,
    TimeReportDayOut,
    TimeReportEntriesOut,
    TimeReportEntryOut,
    TimeReportSummaryOut,
)

time_report_router = Router(tags=["admin-time-reporting"])
StaffProblem = tuple[int, dict[str, Any]]
ZERO_HOURS = Decimal(0)


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
    if not request.user.has_perm("clients.view_timeentry"):
        return _problem(
            "You do not have permission to view time reporting.",
            "forbidden",
            403,
        )
    return None


def _period_dates(period: str, today: date) -> tuple[date, date]:
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    if period == "this_month":
        return today.replace(day=1), today
    if period == "last_month":
        previous_month_end = today.replace(day=1) - timedelta(days=1)
        return previous_month_end.replace(day=1), previous_month_end
    if period == "this_year":
        return today.replace(month=1, day=1), today
    raise ValueError("Unsupported reporting period.")


def _resolve_period(
    period: str,
    *,
    date_from: date | None,
    date_to: date | None,
) -> tuple[str, date, date]:
    if date_from is not None or date_to is not None:
        if date_from is None or date_to is None:
            raise ValueError("Custom reporting requires both date_from and date_to.")
        if date_from > date_to:
            raise ValueError("date_from cannot be after date_to.")
        return "custom", date_from, date_to

    report_from, report_to = _period_dates(period, timezone.localdate())
    return period, report_from, report_to


def _scoped_entries(
    user: User,
    *,
    report_from: date,
    report_to: date,
    client_id: int | None,
    project_id: int | None,
    ownership_type: str | None,
) -> QuerySet[TimeEntry]:
    entries = visible_time_entries(user).filter(
        date__gte=report_from,
        date__lte=report_to,
    )
    if client_id is not None:
        entries = entries.filter(client_id=client_id)
    if project_id is not None:
        entries = entries.filter(project_id=project_id)
    if ownership_type in {OwnershipType.INTERNAL, OwnershipType.CLIENT}:
        entries = entries.filter(ownership_type=ownership_type)
    return entries


def _tracked_billable(entries: QuerySet[TimeEntry]) -> tuple[Decimal, Decimal]:
    totals = entries.aggregate(
        tracked_hours=Sum("duration_hours", default=ZERO_HOURS),
        billable_hours=Sum(
            "duration_hours",
            filter=Q(billable=True),
            default=ZERO_HOURS,
        ),
    )
    return totals["tracked_hours"], totals["billable_hours"]


def _user_name(user: User | None) -> str | None:
    if user is None:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _entry_out(entry: TimeEntry) -> TimeReportEntryOut:
    return TimeReportEntryOut(
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
        user_name=_user_name(entry.user),
    )


def _validate_ownership_filter(ownership_type: str | None) -> StaffProblem | None:
    if ownership_type is None or ownership_type in {
        OwnershipType.INTERNAL,
        OwnershipType.CLIENT,
    }:
        return None
    return _problem("Unsupported ownership filter.", "invalid_scope")


@time_report_router.get(
    "/time-reports/summary",
    response={
        200: TimeReportSummaryOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def time_report_summary(
    request: HttpRequest,
    period: str = "30d",
    client_id: int | None = None,
    project_id: int | None = None,
    ownership_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TimeReportSummaryOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    ownership_problem = _validate_ownership_filter(ownership_type)
    if ownership_problem:
        return ownership_problem

    try:
        period_name, report_from, report_to = _resolve_period(
            period,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as error:
        return _problem(str(error), "invalid_period")

    entries = _scoped_entries(
        cast(User, request.user),
        report_from=report_from,
        report_to=report_to,
        client_id=client_id,
        project_id=project_id,
        ownership_type=ownership_type,
    )

    totals = entries.aggregate(
        tracked_hours=Sum("duration_hours", default=ZERO_HOURS),
        billable_hours=Sum(
            "duration_hours",
            filter=Q(billable=True),
            default=ZERO_HOURS,
        ),
        client_hours=Sum(
            "duration_hours",
            filter=Q(client__isnull=False),
            default=ZERO_HOURS,
        ),
        internal_hours=Sum(
            "duration_hours",
            filter=Q(client__isnull=True),
            default=ZERO_HOURS,
        ),
    )
    tracked = totals["tracked_hours"]
    billable = totals["billable_hours"]
    client_hours = totals["client_hours"]
    internal_hours = totals["internal_hours"]

    client_rows = (
        entries.filter(client__isnull=False)
        .values("client_id", "client__company", "client__name")
        .annotate(
            tracked_hours=Sum("duration_hours", default=ZERO_HOURS),
            billable_hours=Sum(
                "duration_hours",
                filter=Q(billable=True),
                default=ZERO_HOURS,
            ),
            entry_count=Count("id"),
            project_count=Count(
                "project_id",
                distinct=True,
                filter=Q(project__isnull=False),
            ),
        )
        .order_by("-tracked_hours", "client__company", "client__name")
    )
    clients = [
        TimeReportClientOut(
            client_id=row["client_id"],
            client_name=row["client__company"] or row["client__name"],
            tracked_hours=row["tracked_hours"],
            billable_hours=row["billable_hours"],
            non_billable_hours=row["tracked_hours"] - row["billable_hours"],
            entry_count=row["entry_count"],
            project_count=row["project_count"],
        )
        for row in client_rows
    ]

    daily_rows = (
        entries.values("date")
        .annotate(
            tracked_hours=Sum("duration_hours", default=ZERO_HOURS),
            billable_hours=Sum(
                "duration_hours",
                filter=Q(billable=True),
                default=ZERO_HOURS,
            ),
        )
        .order_by("date")
    )
    daily = [
        TimeReportDayOut(
            date=row["date"],
            tracked_hours=row["tracked_hours"],
            billable_hours=row["billable_hours"],
        )
        for row in daily_rows
    ]

    return TimeReportSummaryOut(
        period=period_name,
        date_from=report_from,
        date_to=report_to,
        tracked_hours=tracked,
        billable_hours=billable,
        non_billable_hours=tracked - billable,
        client_hours=client_hours,
        internal_hours=internal_hours,
        entry_count=entries.count(),
        clients=clients,
        daily=daily,
    )


@time_report_router.get(
    "/time-reports/entries",
    response={
        200: TimeReportEntriesOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def time_report_entries(
    request: HttpRequest,
    period: str = "this_month",
    client_id: int | None = None,
    project_id: int | None = None,
    ownership_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TimeReportEntriesOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    ownership_problem = _validate_ownership_filter(ownership_type)
    if ownership_problem:
        return ownership_problem

    try:
        period_name, report_from, report_to = _resolve_period(
            period,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as error:
        return _problem(str(error), "invalid_period")

    entries = _scoped_entries(
        cast(User, request.user),
        report_from=report_from,
        report_to=report_to,
        client_id=client_id,
        project_id=project_id,
        ownership_type=ownership_type,
    )
    tracked, billable = _tracked_billable(entries)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    total = entries.count()
    start = (page - 1) * page_size
    rows = entries.order_by("-date", "-created_at")[start : start + page_size]

    return TimeReportEntriesOut(
        period=period_name,
        date_from=report_from,
        date_to=report_to,
        tracked_hours=tracked,
        billable_hours=billable,
        non_billable_hours=tracked - billable,
        total=total,
        page=page,
        page_size=page_size,
        items=[_entry_out(entry) for entry in rows],
    )

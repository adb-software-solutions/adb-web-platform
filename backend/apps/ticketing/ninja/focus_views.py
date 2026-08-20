from __future__ import annotations

import math
from typing import cast

from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, QuerySet, Value, When
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from ninja import Router

from apps.access_control.models import StaffAccessProfile
from apps.access_control.policies import scope_ticket_queues_for_user
from apps.ticketing.models import Ticket, TicketQueue
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .admin_views import _staff_problem, _user_label, _visible_tickets
from .focus_schemas import (
    TicketFocusCountsOut,
    TicketFocusPageOut,
    TicketFocusQueueOut,
    TicketFocusView,
    TicketQueuePreferencesIn,
    TicketQueuePreferencesOut,
    TicketSort,
)
from .schemas import TicketListItemOut

ticket_focus_router = Router(tags=["admin-ticket-focus"])
StaffProblem = tuple[int, dict[str, object]]
ACTIONABLE_STATUSES = (
    Ticket.Status.NEW,
    Ticket.Status.OPEN,
    Ticket.Status.WAITING_INTERNAL,
    Ticket.Status.WAITING_CUSTOMER,
)


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
    problem = _staff_problem(request)
    if problem:
        return cast(StaffProblem, problem)
    if not request.user.has_perm("ticketing.view_ticket"):
        return 403, {
            "message": "You do not have permission to view tickets.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _visible_enabled_queues(request: HttpRequest) -> QuerySet[TicketQueue]:
    return scope_ticket_queues_for_user(
        request.user,
        TicketQueue.objects.select_related("brand").filter(enabled=True),
    ).order_by("ordering", "name")


def _profile(user: User) -> StaffAccessProfile:
    profile, _ = StaffAccessProfile.objects.get_or_create(user=user)
    return profile


def _stored_default_queue_ids(request: HttpRequest, queues: QuerySet[TicketQueue]) -> list[int]:
    profile = _profile(cast(User, request.user))
    visible_ids = list(queues.values_list("id", flat=True))
    if not visible_ids:
        return []
    stored_ids = list(
        profile.default_ticket_queues.filter(id__in=visible_ids, enabled=True)
        .order_by("ordering", "name")
        .values_list("id", flat=True)
    )
    return stored_ids or visible_ids


def _ticket_item(ticket: Ticket) -> TicketListItemOut:
    return TicketListItemOut(
        id=ticket.id,
        reference=ticket.reference,
        subject=ticket.subject,
        brand_id=ticket.brand_id,
        brand_name=ticket.brand.name,
        queue_id=ticket.queue_id,
        queue_name=ticket.queue.name,
        client_id=ticket.client_id,
        client_name=str(ticket.client) if ticket.client else None,
        primary_contact_id=ticket.primary_contact_id,
        primary_contact_name=ticket.primary_contact.name if ticket.primary_contact else None,
        vendor_id=ticket.vendor_id,
        vendor_name=ticket.vendor.name if ticket.vendor else None,
        status=ticket.status,
        priority=ticket.priority,
        classification=ticket.classification,
        source=ticket.source,
        assigned_to_id=ticket.assigned_to_id,
        assigned_to_name=_user_label(ticket.assigned_to),
        message_count=ticket.message_count,
        last_message_at=ticket.last_message_at,
        created_at=ticket.created_at,
    )


def _apply_sort(tickets: QuerySet[Ticket], sort: TicketSort) -> QuerySet[Ticket]:
    tickets = tickets.annotate(activity_at=Coalesce("last_message_at", "created_at"))
    if sort == "updated_desc":
        return tickets.order_by("-activity_at", "-created_at")
    if sort == "updated_asc":
        return tickets.order_by("activity_at", "created_at")
    if sort == "priority_desc":
        return tickets.annotate(
            priority_rank=Case(
                When(priority=Ticket.Priority.URGENT, then=Value(0)),
                When(priority=Ticket.Priority.HIGH, then=Value(1)),
                When(priority=Ticket.Priority.NORMAL, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by("priority_rank", "-activity_at")
    if sort == "priority_asc":
        return tickets.annotate(
            priority_rank=Case(
                When(priority=Ticket.Priority.LOW, then=Value(0)),
                When(priority=Ticket.Priority.NORMAL, then=Value(1)),
                When(priority=Ticket.Priority.HIGH, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by("priority_rank", "-activity_at")
    if sort == "created_desc":
        return tickets.order_by("-created_at")
    if sort == "created_asc":
        return tickets.order_by("created_at")
    if sort == "subject_asc":
        return tickets.order_by("subject", "-activity_at")
    if sort == "subject_desc":
        return tickets.order_by("-subject", "-activity_at")

    return tickets.annotate(
        status_rank=Case(
            When(status=Ticket.Status.NEW, then=Value(0)),
            When(status=Ticket.Status.OPEN, then=Value(1)),
            When(status=Ticket.Status.WAITING_INTERNAL, then=Value(2)),
            When(status=Ticket.Status.WAITING_CUSTOMER, then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        ),
        priority_rank=Case(
            When(priority=Ticket.Priority.URGENT, then=Value(0)),
            When(priority=Ticket.Priority.HIGH, then=Value(1)),
            When(priority=Ticket.Priority.NORMAL, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
    ).order_by("status_rank", "priority_rank", "-activity_at", "-created_at")


def _focus_counts(tickets: QuerySet[Ticket], user: User) -> TicketFocusCountsOut:
    active = tickets.filter(status__in=ACTIONABLE_STATUSES)
    return TicketFocusCountsOut(
        mine=active.filter(assigned_to=user).count(),
        unassigned=active.filter(assigned_to__isnull=True).count(),
        active=active.count(),
        waiting_customer=active.filter(status=Ticket.Status.WAITING_CUSTOMER).count(),
    )


@ticket_focus_router.get(
    "/ticket-focus",
    response={200: TicketFocusPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def ticket_focus(
    request: HttpRequest,
    view: TicketFocusView = "my",
    page: int = 1,
    page_size: int = 25,
    queue_id: int | None = None,
    search: str | None = None,
    priority: str | None = None,
    sort: TicketSort = "operational",
) -> TicketFocusPageOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    user = cast(User, request.user)
    queues = _visible_enabled_queues(request)
    visible_queue_ids = list(queues.values_list("id", flat=True))
    default_queue_ids = _stored_default_queue_ids(request, queues)
    selected_queue_ids = default_queue_ids
    if queue_id is not None and queue_id in visible_queue_ids:
        selected_queue_ids = [queue_id]

    tickets = (
        _visible_tickets(request)
        .filter(queue_id__in=selected_queue_ids)
        .annotate(message_count=Count("messages", distinct=True))
    )
    counts = _focus_counts(tickets, user)
    active = tickets.filter(status__in=ACTIONABLE_STATUSES)

    if view == "my":
        tickets = active.filter(assigned_to=user)
    elif view == "unassigned":
        tickets = active.filter(assigned_to__isnull=True)
    elif view == "active":
        tickets = active
    elif view == "waiting_customer":
        tickets = active.filter(status=Ticket.Status.WAITING_CUSTOMER)
    elif view == "resolved":
        tickets = tickets.filter(status=Ticket.Status.RESOLVED)
    elif view == "closed":
        tickets = tickets.filter(status=Ticket.Status.CLOSED)

    if priority in {choice for choice, _label in Ticket.Priority.choices}:
        tickets = tickets.filter(priority=priority)
    if search:
        term = search.strip()
        if term:
            tickets = tickets.filter(
                Q(reference__icontains=term)
                | Q(subject__icontains=term)
                | Q(client__name__icontains=term)
                | Q(client__company__icontains=term)
                | Q(primary_contact__name__icontains=term)
                | Q(primary_contact__email__icontains=term)
                | Q(vendor__name__icontains=term)
            )

    queue_counts = dict(
        _visible_tickets(request)
        .filter(queue_id__in=visible_queue_ids, status__in=ACTIONABLE_STATUSES)
        .values("queue_id")
        .annotate(total=Count("id"))
        .values_list("queue_id", "total")
    )
    default_set = set(default_queue_ids)
    queue_rows = [
        TicketFocusQueueOut(
            id=queue.id,
            name=queue.name,
            brand_name=queue.brand.name if queue.brand else None,
            active_count=queue_counts.get(queue.id, 0),
            is_default=queue.id in default_set,
        )
        for queue in queues
    ]

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = tickets.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    page_items = _apply_sort(tickets, sort)[start : start + page_size]

    return TicketFocusPageOut(
        view=view,
        items=[_ticket_item(ticket) for ticket in page_items],
        counts=counts,
        queues=queue_rows,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@ticket_focus_router.put(
    "/ticket-focus/queue-preferences",
    response={
        200: TicketQueuePreferencesOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def update_ticket_queue_preferences(
    request: HttpRequest,
    payload: TicketQueuePreferencesIn,
) -> TicketQueuePreferencesOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    queues = _visible_enabled_queues(request)
    visible_ids = list(queues.values_list("id", flat=True))
    requested_ids = list(dict.fromkeys(payload.queue_ids))
    invalid_ids = set(requested_ids) - set(visible_ids)
    if invalid_ids:
        return 400, {
            "message": "One or more selected ticket queues are unavailable.",
            "success": False,
            "code": "queue_unavailable",
        }

    profile = _profile(cast(User, request.user))
    with transaction.atomic():
        if not requested_ids or set(requested_ids) == set(visible_ids):
            profile.default_ticket_queues.clear()
            effective_ids = visible_ids
            uses_all = True
        else:
            profile.default_ticket_queues.set(requested_ids)
            effective_ids = requested_ids
            uses_all = False

    return TicketQueuePreferencesOut(
        queue_ids=effective_ids,
        uses_all_accessible_queues=uses_all,
    )

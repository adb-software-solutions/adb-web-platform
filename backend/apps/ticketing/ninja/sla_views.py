from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_ticket_queues_for_user
from apps.core.models import AuditEvent
from apps.ticketing.models import Ticket, TicketQueue
from apps.ticketing.services.sla import evaluate_ticket_sla, reset_ticket_sla_deadlines
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .admin_views import _visible_tickets
from .sla_schemas import (
    TicketQueueSLAOut,
    TicketQueueSLAUpdateIn,
    TicketSLAListOut,
    TicketSLAOut,
)

sla_router = Router(tags=["admin-ticket-sla"])
StaffProblem = tuple[int, dict[str, Any]]


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _staff_problem(request: HttpRequest) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(403, "Staff access required.", "forbidden")
    return None


def _user_label(user: User | None) -> str | None:
    if user is None:
        return None
    return user.get_full_name().strip() or user.email


def _sla_out(ticket: Ticket) -> TicketSLAOut:
    health = evaluate_ticket_sla(ticket)
    return TicketSLAOut(
        ticket_id=ticket.id,
        reference=ticket.reference,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        queue_id=ticket.queue_id,
        queue_name=ticket.queue.name,
        client_id=ticket.client_id,
        client_name=str(ticket.client) if ticket.client else None,
        assigned_to_name=_user_label(ticket.assigned_to),
        first_response_due_at=ticket.first_response_due_at,
        first_response_at=ticket.first_response_at,
        first_response_status=health.first_response_status,
        resolution_due_at=ticket.resolution_due_at,
        resolved_at=ticket.resolved_at,
        resolution_status=health.resolution_status,
        next_due_at=health.next_due_at,
        overall_status=health.overall_status,
        severity=health.severity,
        href=f"/admin/tickets/{ticket.id}",
    )


@sla_router.get(
    "/ticket-queues/{queue_id}/sla",
    response={
        200: TicketQueueSLAOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_queue_sla(request: HttpRequest, queue_id: int) -> TicketQueueSLAOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.view_ticketqueue"):
        return _problem(403, "You do not have permission to view ticket queues.", "forbidden")
    queue = scope_ticket_queues_for_user(request.user).filter(id=queue_id).first()
    if queue is None:
        return _problem(404, "Ticket queue not found.", "not_found")
    return TicketQueueSLAOut(
        queue_id=queue.id,
        queue_name=queue.name,
        first_response_sla_minutes=queue.first_response_sla_minutes,
        resolution_sla_minutes=queue.resolution_sla_minutes,
    )


@sla_router.put(
    "/ticket-queues/{queue_id}/sla",
    response={
        200: TicketQueueSLAOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_queue_sla(
    request: HttpRequest,
    queue_id: int,
    payload: TicketQueueSLAUpdateIn,
) -> TicketQueueSLAOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.configure_ticket_queues"):
        return _problem(403, "You do not have permission to configure ticket queues.", "forbidden")
    queue = scope_ticket_queues_for_user(request.user).filter(id=queue_id).first()
    if queue is None:
        return _problem(404, "Ticket queue not found.", "not_found")

    queue.first_response_sla_minutes = payload.first_response_sla_minutes
    queue.resolution_sla_minutes = payload.resolution_sla_minutes
    try:
        queue.full_clean()
    except ValidationError as error:
        return _problem(400, " ".join(error.messages), "invalid_sla")
    queue.save(
        update_fields=[
            "first_response_sla_minutes",
            "resolution_sla_minutes",
            "updated_at",
        ]
    )
    AuditEvent.record(
        action="ticketing.queue_sla_updated",
        actor=request.user,
        target=queue,
        metadata={
            "first_response_sla_minutes": queue.first_response_sla_minutes,
            "resolution_sla_minutes": queue.resolution_sla_minutes,
        },
    )
    return TicketQueueSLAOut(
        queue_id=queue.id,
        queue_name=queue.name,
        first_response_sla_minutes=queue.first_response_sla_minutes,
        resolution_sla_minutes=queue.resolution_sla_minutes,
    )


@sla_router.get(
    "/tickets/{ticket_id}/sla",
    response={
        200: TicketSLAOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def ticket_sla_detail(request: HttpRequest, ticket_id: int) -> TicketSLAOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.view_ticket"):
        return _problem(403, "You do not have permission to view tickets.", "forbidden")
    ticket = (
        _visible_tickets(request)
        .select_related("queue", "client", "assigned_to")
        .filter(id=ticket_id)
        .first()
    )
    if ticket is None:
        return _problem(404, "Ticket not found.", "not_found")
    return _sla_out(ticket)


@sla_router.get(
    "/ticket-sla",
    response={200: TicketSLAListOut, 401: ProblemDetail, 403: ProblemDetail},
)
def ticket_sla_list(
    request: HttpRequest,
    attention_only: bool = True,
    assigned_to_me: bool = False,
) -> TicketSLAListOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.view_ticket"):
        return _problem(403, "You do not have permission to view tickets.", "forbidden")

    tickets = _visible_tickets(request).select_related("queue", "client", "assigned_to")
    tickets = tickets.exclude(
        status__in=[Ticket.Status.CLOSED, Ticket.Status.SPAM]
    ).order_by("first_response_due_at", "resolution_due_at", "-priority", "id")
    if assigned_to_me:
        tickets = tickets.filter(assigned_to=cast(User, request.user))

    all_items = [_sla_out(ticket) for ticket in tickets[:500]]
    items = (
        [item for item in all_items if item.overall_status in {"warning", "breached"}]
        if attention_only
        else all_items
    )
    return TicketSLAListOut(
        items=items,
        healthy_count=sum(item.overall_status == "healthy" for item in all_items),
        warning_count=sum(item.overall_status == "warning" for item in all_items),
        breached_count=sum(item.overall_status == "breached" for item in all_items),
        waiting_customer_count=sum(
            item.overall_status == "waiting_customer" for item in all_items
        ),
    )


@sla_router.post(
    "/tickets/{ticket_id}/sla/recalculate",
    response={
        200: TicketSLAOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def recalculate_ticket_sla(
    request: HttpRequest,
    ticket_id: int,
) -> TicketSLAOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.change_ticket"):
        return _problem(403, "You do not have permission to change tickets.", "forbidden")
    ticket = (
        _visible_tickets(request)
        .select_related("queue", "client", "assigned_to")
        .filter(id=ticket_id)
        .first()
    )
    if ticket is None:
        return _problem(404, "Ticket not found.", "not_found")
    reset_ticket_sla_deadlines(ticket)
    AuditEvent.record(
        action="ticketing.sla_recalculated",
        actor=request.user,
        target=ticket,
    )
    return _sla_out(ticket)

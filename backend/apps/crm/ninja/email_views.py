from __future__ import annotations

from typing import Any, cast

from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user, scope_ticket_queues_for_user
from apps.crm.models import Lead
from apps.crm.tasks import deliver_lead_email_task
from apps.ticketing.models import Mailbox, Ticket
from apps.ticketing.services.outbound import (
    BACKGROUND_AUTH_METHODS,
    TicketOutboundError,
    prepare_outbound_ticket_email,
)
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .email_schemas import LeadEmailIn, LeadEmailOptionsOut, LeadEmailOut, LeadMailboxOut
from .schemas import LeadTicketOut

lead_email_router = Router(tags=["admin-lead-email"])
StaffProblem = tuple[int, dict[str, Any]]


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
    if not request.user.has_perm("crm.view_lead"):
        return _problem("You do not have permission to view leads.", "forbidden", 403)
    return None


def _lead(lead_id: int) -> Lead | None:
    return Lead.objects.select_related("brand").filter(id=lead_id).first()


def _available_mailboxes(request: HttpRequest, lead: Lead) -> QuerySet[Mailbox]:
    mailboxes = Mailbox.objects.select_related(
        "brand",
        "default_queue",
        "graph_connection__credential",
    ).filter(
        enabled=True,
        graph_connection__enabled=True,
        graph_connection__credential__isnull=False,
        graph_connection__authentication_method__in=BACKGROUND_AUTH_METHODS,
    )
    if lead.brand_id is not None:
        mailboxes = mailboxes.filter(brand_id=lead.brand_id)
    if not request.user.is_superuser:
        queues = scope_ticket_queues_for_user(request.user)
        mailboxes = mailboxes.filter(default_queue__in=queues)
    return mailboxes


def _mailbox_rows(request: HttpRequest, lead: Lead) -> list[LeadMailboxOut]:
    purpose_order: dict[str, int] = {
        Mailbox.Purpose.SALES.value: 0,
        Mailbox.Purpose.GENERAL.value: 1,
        Mailbox.Purpose.SUPPORT.value: 2,
        Mailbox.Purpose.ACCOUNTS.value: 3,
        Mailbox.Purpose.OPERATIONS.value: 4,
    }
    rows = sorted(
        _available_mailboxes(request, lead),
        key=lambda mailbox: (
            purpose_order.get(mailbox.purpose, 99),
            mailbox.email_address.lower(),
        ),
    )
    return [
        LeadMailboxOut(
            id=mailbox.id,
            email_address=mailbox.email_address,
            display_name=mailbox.display_name,
            brand_name=mailbox.brand.name,
            purpose=mailbox.purpose,
        )
        for mailbox in rows
    ]


def _conversation_rows(request: HttpRequest, lead: Lead) -> list[LeadTicketOut]:
    if not request.user.has_perm("ticketing.view_ticket"):
        return []

    tickets = Ticket.objects.select_related("queue").filter(
        Q(messages__sender_address__iexact=lead.email)
        | Q(messages__to_recipients__contains=[lead.email])
        | Q(primary_contact__email__iexact=lead.email)
    )
    if lead.brand_id is not None:
        tickets = tickets.filter(brand_id=lead.brand_id)
    if not request.user.is_superuser:
        clients = scope_clients_for_user(request.user)
        queues = scope_ticket_queues_for_user(request.user)
        tickets = tickets.filter(
            Q(queue__in=queues) & (Q(client__isnull=True) | Q(client__in=clients))
        )

    return [
        LeadTicketOut(
            id=ticket.id,
            reference=ticket.reference,
            subject=ticket.subject,
            status=ticket.status,
            priority=ticket.priority,
            queue_name=ticket.queue.name,
            last_message_at=ticket.last_message_at,
        )
        for ticket in tickets.distinct().order_by("-last_message_at", "-created_at")[:20]
    ]


@lead_email_router.get(
    "/leads/{lead_id}/email-options",
    response={
        200: LeadEmailOptionsOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def lead_email_options(request: HttpRequest, lead_id: int) -> LeadEmailOptionsOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    lead = _lead(lead_id)
    if lead is None:
        return _problem("Lead not found.", "not_found", 404)

    can_email = bool(lead.converted_at is None and request.user.has_perm("ticketing.reply_ticket"))
    return LeadEmailOptionsOut(
        can_email=can_email,
        mailboxes=_mailbox_rows(request, lead) if can_email else [],
    )


@lead_email_router.get(
    "/leads/{lead_id}/conversations",
    response={
        200: list[LeadTicketOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def lead_conversations(request: HttpRequest, lead_id: int) -> list[LeadTicketOut] | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    lead = _lead(lead_id)
    if lead is None:
        return _problem("Lead not found.", "not_found", 404)
    return _conversation_rows(request, lead)


@lead_email_router.post(
    "/leads/{lead_id}/email",
    response={
        202: LeadEmailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def email_lead(
    request: HttpRequest,
    lead_id: int,
    payload: LeadEmailIn,
) -> tuple[int, LeadEmailOut] | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("ticketing.reply_ticket"):
        return _problem("You do not have permission to send lead email.", "forbidden", 403)

    lead = _lead(lead_id)
    if lead is None:
        return _problem("Lead not found.", "not_found", 404)
    if lead.converted_at is not None:
        return _problem(
            "Converted leads should be contacted from their client account.",
            "lead_converted",
        )

    mailbox = _available_mailboxes(request, lead).filter(id=payload.mailbox_id).first()
    if mailbox is None:
        return _problem(
            "The selected mailbox is unavailable for this lead.",
            "mailbox_unavailable",
            404,
        )

    try:
        prepared = prepare_outbound_ticket_email(
            mailbox,
            cast(User, request.user),
            recipient=lead.email,
            subject=payload.subject,
            body_text=payload.body_text,
        )
    except TicketOutboundError as error:
        return _problem(str(error), "email_unavailable")

    deliver_lead_email_task.delay(prepared.message.id)
    return 202, LeadEmailOut(
        ticket_id=prepared.ticket.id,
        ticket_reference=prepared.ticket.reference,
        message_id=prepared.message.id,
        delivery_status=prepared.message.delivery_status,
    )

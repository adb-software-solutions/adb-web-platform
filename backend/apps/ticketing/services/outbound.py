from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.ticketing.models import Mailbox, MicrosoftGraphConnection, Ticket, TicketMessage
from apps.ticketing.services.replies import DELIVERY_STATUS_QUEUED, GRAPH_PROVIDER
from authentication.models import User

BACKGROUND_AUTH_METHODS = (
    MicrosoftGraphConnection.AuthenticationMethod.CERTIFICATE,
    MicrosoftGraphConnection.AuthenticationMethod.CLIENT_SECRET,
)


class TicketOutboundError(RuntimeError):
    """A new outbound ticket conversation cannot be prepared safely."""


@dataclass(frozen=True)
class PreparedOutboundTicket:
    ticket: Ticket
    message: TicketMessage


def mailbox_supports_background_delivery(mailbox: Mailbox) -> bool:
    return bool(
        mailbox.enabled
        and mailbox.graph_connection.enabled
        and mailbox.graph_connection.credential_id
        and mailbox.graph_connection.authentication_method in BACKGROUND_AUTH_METHODS
    )


def prepare_outbound_ticket_email(
    mailbox: Mailbox,
    author: User,
    *,
    recipient: str,
    subject: str,
    body_text: str,
) -> PreparedOutboundTicket:
    """Create an auditable queued conversation before Microsoft Graph delivery."""
    recipient_address = recipient.strip().lower()
    clean_subject = subject.strip()
    body = body_text.strip()

    try:
        validate_email(recipient_address)
    except ValidationError as exc:
        raise TicketOutboundError("A valid recipient email address is required.") from exc
    if not clean_subject:
        raise TicketOutboundError("An email subject is required.")
    if not body:
        raise TicketOutboundError("An email body is required.")
    if not mailbox_supports_background_delivery(mailbox):
        raise TicketOutboundError(
            "The selected mailbox is not available for background Microsoft Graph delivery."
        )

    priority = mailbox.default_queue.default_priority
    if priority not in Ticket.Priority.values:
        priority = Ticket.Priority.NORMAL

    with transaction.atomic():
        ticket = Ticket(
            brand=mailbox.brand,
            queue=mailbox.default_queue,
            mailbox=mailbox,
            subject=clean_subject,
            status=Ticket.Status.NEW,
            priority=priority,
            classification=Ticket.Classification.SALES,
            source=Ticket.Source.MANUAL,
            assigned_to=author,
        )
        # Ticket.save() generates the immutable human-readable reference used by validation.
        ticket.save()
        ticket.full_clean()

        message = TicketMessage(
            ticket=ticket,
            direction=TicketMessage.Direction.OUTBOUND,
            sender_name=mailbox.display_name.strip(),
            sender_address=mailbox.email_address.strip().lower(),
            to_recipients=[recipient_address],
            subject=clean_subject,
            body_text=body,
            body_text_normalised=body,
            provider=GRAPH_PROVIDER,
            provider_message_id=None,
            provider_reply_to_message_id="",
            internet_message_id="",
            sent_or_received_at=timezone.now(),
            delivery_status=DELIVERY_STATUS_QUEUED,
            created_by=author,
        )
        message.full_clean()
        message.save()

    return PreparedOutboundTicket(ticket=ticket, message=message)

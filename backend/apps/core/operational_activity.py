from __future__ import annotations

import math
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from apps.access_control.policies import scope_clients_for_user
from apps.core.models import AuditEvent
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.models import User

from .ninja.operational_schemas import ActivityItemOut, ActivityPageOut


@dataclass(frozen=True)
class ActivityContext:
    client_id: int | None = None
    resource_id: int | None = None


def _actor_name(event: AuditEvent) -> str:
    if event.actor is None:
        return "System"
    return event.actor.get_full_name().strip() or event.actor.email


def scoped_audit_events(user: User) -> QuerySet[AuditEvent]:
    """Return audit rows that can be safely associated with the caller's object scope."""
    events = AuditEvent.objects.select_related("actor")
    if user.is_superuser:
        return events

    clients = scope_clients_for_user(user)
    resources = scope_infrastructure_resources_for_user(user)
    return events.filter(
        Q(actor=user)
        | Q(client_id__in=clients.values("id"))
        | Q(resource_id__in=resources.values("id"))
    ).distinct()


def activity_page(
    *,
    user: User,
    context: ActivityContext,
    page: int = 1,
    page_size: int = 50,
) -> ActivityPageOut:
    events = scoped_audit_events(user)
    if context.client_id is not None:
        events = events.filter(client_id=context.client_id)
    if context.resource_id is not None:
        events = events.filter(resource_id=context.resource_id)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = events.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    metadata_visible = user.has_perm("core.view_sensitive_audit_metadata")

    rows = events.order_by("-created_at", "-id")[start : start + page_size]
    items = [
        ActivityItemOut(
            id=event.id,
            action=event.action,
            actor_name=_actor_name(event),
            target_type=event.target_type,
            target_id=event.target_id,
            target_label=event.target_label,
            client_id=event.client_id,
            resource_id=event.resource_id,
            metadata=event.metadata if metadata_visible else {},
            ip_address=event.ip_address if metadata_visible else None,
            user_agent=event.user_agent if metadata_visible else "",
            occurred_at=event.created_at,
        )
        for event in rows
    ]
    return ActivityPageOut(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        metadata_visible=metadata_visible,
    )

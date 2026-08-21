from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet

from apps.access_control.policies import can_access_client, scope_clients_for_user
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import InfrastructureResource


def can_access_infrastructure_resource(user: Any, resource: InfrastructureResource) -> bool:
    """Check resource scope independently from Django capability permissions."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if resource.ownership_type == OwnershipType.INTERNAL:
        return True
    if resource.client is None:
        return False
    return can_access_client(user, resource.client)


def scope_infrastructure_resources_for_user(
    user: Any,
    queryset: QuerySet[InfrastructureResource] | None = None,
) -> QuerySet[InfrastructureResource]:
    """Restrict resources to Internal plus Client records inside the user's scope."""
    queryset = queryset if queryset is not None else InfrastructureResource.objects.all()

    if not getattr(user, "is_authenticated", False):
        return queryset.none()
    if getattr(user, "is_superuser", False):
        return queryset

    clients = scope_clients_for_user(user)
    return queryset.filter(
        Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients)
    ).distinct()

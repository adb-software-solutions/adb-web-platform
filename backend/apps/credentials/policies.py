from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet

from apps.access_control.policies import can_access_client, scope_clients_for_user
from apps.core.ownership import OwnershipType
from apps.credentials.models import StoredCredential


def can_access_credential(user: Any, credential: StoredCredential) -> bool:
    """Check credential scope independently from Django capability permissions."""
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not getattr(user, "is_staff", False):
        return False
    if credential.ownership_type == OwnershipType.INTERNAL:
        return True
    if credential.client is None:
        return False
    return can_access_client(user, credential.client)


def scope_credentials_for_user(
    user: Any,
    queryset: QuerySet[StoredCredential] | None = None,
) -> QuerySet[StoredCredential]:
    """Restrict credentials to Internal plus Client records inside the user's scope."""
    queryset = queryset if queryset is not None else StoredCredential.objects.all()

    if not getattr(user, "is_authenticated", False):
        return queryset.none()
    if getattr(user, "is_superuser", False):
        return queryset
    if not getattr(user, "is_staff", False):
        return queryset.none()

    clients = scope_clients_for_user(user)
    return queryset.filter(
        Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients)
    ).distinct()

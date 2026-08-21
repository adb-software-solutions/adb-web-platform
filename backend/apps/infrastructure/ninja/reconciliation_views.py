from __future__ import annotations

import math
from typing import Any

from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import can_access_client, scope_clients_for_user
from apps.clients.models import Client
from apps.core.ownership import OwnershipType
from authentication.ninja.schemas import ProblemDetail

from ..legacy_reconciliation import (
    LEGACY_RESOURCE_DEFINITIONS,
    LegacyResourceAlreadyLinkedError,
    LegacyResourceNotFoundError,
    legacy_rows,
    reconcile_legacy_resource,
    reconciliation_counts,
)
from ..resource_models import InfrastructureResource
from .reconciliation_schemas import (
    LegacyReconciliationItemOut,
    LegacyReconciliationOptionsOut,
    LegacyReconciliationPageOut,
    LegacyReconciliationStatus,
    LegacyResourceType,
    ReconcileLegacyResourceIn,
    ReconciledResourceOut,
    ReconciliationClientOptionOut,
)

infrastructure_reconciliation_router = Router(
    tags=["admin-infrastructure-reconciliation"]
)
StaffProblem = tuple[int, dict[str, Any]]


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return 401, {
            "message": "User not authenticated",
            "success": False,
            "code": "unauthenticated",
        }
    if not (request.user.is_staff or request.user.is_superuser):
        return 403, {
            "message": "You do not have permission to reconcile infrastructure.",
            "success": False,
            "code": "forbidden",
        }
    if not request.user.has_perm("infrastructure.reconcile_legacy_infrastructure"):
        return 403, {
            "message": "You do not have permission to reconcile infrastructure.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _row_out(
    definition: Any,
    legacy: Any,
    identity: Any,
) -> LegacyReconciliationItemOut:
    resource = identity.resource if identity is not None else None
    return LegacyReconciliationItemOut(
        legacy_type=definition.key,
        legacy_type_label=definition.label,
        legacy_id=int(legacy.pk),
        name=definition.display_name(legacy),
        resource_id=resource.id if resource else None,
        ownership_type=resource.ownership_type if resource else None,
        client_id=resource.client_id if resource else None,
        client_name=str(resource.client) if resource and resource.client else None,
        lifecycle_status=resource.lifecycle_status if resource else None,
        environment=resource.environment if resource else None,
        criticality=resource.criticality if resource else None,
    )


@infrastructure_reconciliation_router.get(
    "/infrastructure/reconciliation",
    response={
        200: LegacyReconciliationPageOut,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def list_legacy_reconciliation(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    legacy_type: LegacyResourceType | None = None,
    status: LegacyReconciliationStatus = "unlinked",
) -> LegacyReconciliationPageOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    all_rows = legacy_rows(legacy_type=legacy_type, status=status)
    total_legacy, linked = reconciliation_counts()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = len(all_rows)
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size

    return LegacyReconciliationPageOut(
        items=[
            _row_out(definition, legacy, identity)
            for definition, legacy, identity in all_rows[start : start + page_size]
        ],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        total_legacy=total_legacy,
        linked=linked,
        unlinked=total_legacy - linked,
    )


@infrastructure_reconciliation_router.get(
    "/infrastructure/reconciliation/options",
    response={
        200: LegacyReconciliationOptionsOut,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def legacy_reconciliation_options(
    request: HttpRequest,
) -> LegacyReconciliationOptionsOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    clients = scope_clients_for_user(
        request.user,
        Client.objects.order_by("company", "name", "id"),
    )
    return LegacyReconciliationOptionsOut(
        clients=[
            ReconciliationClientOptionOut(
                id=client.id,
                name=str(client),
                status=client.status,
            )
            for client in clients
        ],
        legacy_types=[definition.key for definition in LEGACY_RESOURCE_DEFINITIONS],
        lifecycle_statuses=[
            choice.value for choice in InfrastructureResource.LifecycleStatus
        ],
        environments=[choice.value for choice in InfrastructureResource.Environment],
        criticalities=[choice.value for choice in InfrastructureResource.Criticality],
    )


@infrastructure_reconciliation_router.post(
    "/infrastructure/reconciliation/{legacy_type}/{legacy_id}",
    response={
        200: ReconciledResourceOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        409: ProblemDetail,
        422: ProblemDetail,
    },
)
def reconcile_legacy_record(
    request: HttpRequest,
    legacy_type: LegacyResourceType,
    legacy_id: int,
    payload: ReconcileLegacyResourceIn,
) -> ReconciledResourceOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    client: Client | None = None
    if payload.ownership_type == OwnershipType.CLIENT:
        if payload.client_id is None:
            return 422, {
                "message": "Client-owned infrastructure requires a client.",
                "success": False,
                "code": "client_required",
            }
        client = Client.objects.filter(id=payload.client_id).first()
        if client is None or not can_access_client(request.user, client):
            return 404, {
                "message": "Client not found.",
                "success": False,
                "code": "not_found",
            }
    elif payload.client_id is not None:
        return 422, {
            "message": "Internal infrastructure cannot reference a client.",
            "success": False,
            "code": "invalid_ownership",
        }

    try:
        resource = reconcile_legacy_resource(
            legacy_type=legacy_type,
            legacy_id=legacy_id,
            ownership_type=payload.ownership_type,
            client=client,
            lifecycle_status=payload.lifecycle_status,
            environment=payload.environment,
            criticality=payload.criticality,
            name=payload.name,
            linked_by=request.user,
        )
    except LegacyResourceNotFoundError:
        return 404, {
            "message": "Legacy infrastructure record not found.",
            "success": False,
            "code": "not_found",
        }
    except LegacyResourceAlreadyLinkedError:
        return 409, {
            "message": "Legacy infrastructure record is already reconciled.",
            "success": False,
            "code": "already_reconciled",
        }

    return ReconciledResourceOut(
        resource_id=resource.id,
        name=resource.name,
        resource_type=resource.resource_type,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
    )

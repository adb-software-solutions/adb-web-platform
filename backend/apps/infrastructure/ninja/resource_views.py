from __future__ import annotations

import math

from django.db.models import Q
from django.http import HttpRequest
from ninja import Router

from apps.infrastructure.legacy_resource_snapshot import legacy_resource_snapshot
from apps.infrastructure.models import InfrastructureResource, ResourceRelationship
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .resource_schemas import (
    InfrastructureRelationshipOut,
    InfrastructureResourceDetailOut,
    InfrastructureResourcePageOut,
    InfrastructureResourceSummaryOut,
    InfrastructureTagOut,
    LegacyResourceReferenceOut,
    ResourceEnvironmentFilter,
    ResourceLifecycleFilter,
    ResourceOwnershipFilter,
    ResourceTypeFilter,
    SpecialistFieldOut,
)

infrastructure_resource_router = Router(tags=["admin-infrastructure-resources"])
StaffProblem = tuple[int, dict[str, object]]
CURRENT_LIFECYCLE_STATUSES = (
    InfrastructureResource.LifecycleStatus.PLANNED,
    InfrastructureResource.LifecycleStatus.ACTIVE,
    InfrastructureResource.LifecycleStatus.MAINTENANCE,
    InfrastructureResource.LifecycleStatus.DEPRECATED,
)


def _staff_problem(request: HttpRequest) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return 401, {
            "message": "User not authenticated",
            "success": False,
            "code": "unauthenticated",
        }
    if not (request.user.is_staff or request.user.is_superuser):
        return 403, {
            "message": "You do not have permission to access this resource.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm("infrastructure.view_infrastructureresource"):
        return 403, {
            "message": "You do not have permission to view infrastructure resources.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _resource_summary(resource: InfrastructureResource) -> InfrastructureResourceSummaryOut:
    return InfrastructureResourceSummaryOut(
        id=resource.id,
        name=resource.name,
        resource_type=resource.resource_type,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        tags=[
            InfrastructureTagOut(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                colour=tag.colour,
            )
            for tag in resource.tags.all()
        ],
        updated_at=resource.updated_at,
    )


def _relationship_rows(
    request: HttpRequest,
    resource: InfrastructureResource,
) -> list[InfrastructureRelationshipOut]:
    visible_resources = scope_infrastructure_resources_for_user(request.user)
    relationships = (
        ResourceRelationship.objects.filter(
            Q(source_resource=resource, target_resource__in=visible_resources)
            | Q(target_resource=resource, source_resource__in=visible_resources)
        )
        .select_related("source_resource", "target_resource")
        .order_by("relationship_type", "id")
    )
    rows: list[InfrastructureRelationshipOut] = []
    for relationship in relationships:
        outgoing = relationship.source_resource_id == resource.id
        related = relationship.target_resource if outgoing else relationship.source_resource
        rows.append(
            InfrastructureRelationshipOut(
                id=relationship.id,
                direction="outgoing" if outgoing else "incoming",
                relationship_type=relationship.relationship_type,
                label=relationship.label,
                related_resource_id=related.id,
                related_resource_name=related.name,
                related_resource_type=related.resource_type,
            )
        )
    return rows


@infrastructure_resource_router.get(
    "/infrastructure/resources",
    response={200: InfrastructureResourcePageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_infrastructure_resources(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    ownership: ResourceOwnershipFilter = "all",
    lifecycle: ResourceLifecycleFilter = "current",
    client_id: int | None = None,
    resource_type: ResourceTypeFilter | None = None,
    environment: ResourceEnvironmentFilter | None = None,
    search: str | None = None,
) -> InfrastructureResourcePageOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    resources = scope_infrastructure_resources_for_user(
        request.user,
        InfrastructureResource.objects.select_related("client").prefetch_related("tags"),
    )

    if ownership != "all":
        resources = resources.filter(ownership_type=ownership)
    if lifecycle == "current":
        resources = resources.filter(lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES)
    elif lifecycle != "all":
        resources = resources.filter(lifecycle_status=lifecycle)
    if client_id is not None:
        resources = resources.filter(client_id=client_id)
    if resource_type is not None:
        resources = resources.filter(resource_type=resource_type)
    if environment is not None:
        resources = resources.filter(environment=environment)
    if search:
        term = search.strip()
        if term:
            resources = resources.filter(
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(client__name__icontains=term)
                | Q(client__company__icontains=term)
                | Q(tags__name__icontains=term)
            ).distinct()

    resources = resources.order_by("name", "id")
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = resources.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    page_items = resources[start : start + page_size]

    return InfrastructureResourcePageOut(
        items=[_resource_summary(resource) for resource in page_items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@infrastructure_resource_router.get(
    "/infrastructure/resources/{resource_id}",
    response={
        200: InfrastructureResourceDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_infrastructure_resource(
    request: HttpRequest,
    resource_id: int,
) -> InfrastructureResourceDetailOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    resource = (
        scope_infrastructure_resources_for_user(
            request.user,
            InfrastructureResource.objects.select_related("client").prefetch_related("tags"),
        )
        .filter(id=resource_id)
        .first()
    )
    if resource is None:
        return 404, {
            "message": "Infrastructure resource not found.",
            "success": False,
            "code": "not_found",
        }

    specialist = legacy_resource_snapshot(resource)
    summary = _resource_summary(resource)
    return InfrastructureResourceDetailOut(
        **summary.model_dump(),
        description=resource.description,
        is_portal_visible=resource.is_portal_visible,
        relationships=_relationship_rows(request, resource),
        legacy_reference=(
            LegacyResourceReferenceOut(
                legacy_type=specialist.legacy_type,
                legacy_id=specialist.legacy_id,
                name=specialist.name,
                register_path=specialist.register_path,
                fields=[
                    SpecialistFieldOut(
                        key=field.key,
                        label=field.label,
                        value=field.value,
                        kind=field.kind,
                    )
                    for field in specialist.fields
                ],
            )
            if specialist
            else None
        ),
        created_at=resource.created_at,
    )

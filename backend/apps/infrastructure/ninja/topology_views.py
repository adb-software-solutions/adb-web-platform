from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.http import HttpRequest
from ninja import Router

from apps.infrastructure.models import InfrastructureResource, ResourceRelationship
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .topology_schemas import ResourceTopologyOut, TopologyEdgeOut, TopologyNodeOut

topology_router = Router(tags=["admin-infrastructure-topology"])
StaffProblem = tuple[int, dict[str, Any]]
MAX_TOPOLOGY_NODES = 100
MAX_TOPOLOGY_EDGES = 250
MAX_TOPOLOGY_DEPTH = 2


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _node(resource: InfrastructureResource, root_id: int) -> TopologyNodeOut:
    return TopologyNodeOut(
        id=resource.id,
        name=resource.name,
        resource_type=resource.resource_type,
        resource_type_label=resource.get_resource_type_display(),
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        href=f"/admin/infrastructure/resources/{resource.id}",
        is_root=resource.id == root_id,
    )


@topology_router.get(
    "/infrastructure/resources/{resource_id}/topology",
    response={
        200: ResourceTopologyOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def resource_topology(
    request: HttpRequest,
    resource_id: int,
    depth: int = 1,
) -> ResourceTopologyOut | StaffProblem:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(403, "Staff access required.", "forbidden")
    if not request.user.has_perm("infrastructure.view_infrastructureresource"):
        return _problem(
            403,
            "You do not have permission to view infrastructure resources.",
            "forbidden",
        )
    if depth < 1 or depth > MAX_TOPOLOGY_DEPTH:
        return _problem(
            400,
            f"Topology depth must be between 1 and {MAX_TOPOLOGY_DEPTH}.",
            "invalid_depth",
        )

    visible = scope_infrastructure_resources_for_user(request.user).select_related("client")
    root = visible.filter(id=resource_id).first()
    if root is None:
        return _problem(404, "Infrastructure resource not found.", "not_found")

    visible_ids = visible.values("id")
    node_ids = {root.id}
    frontier = {root.id}
    edge_rows: dict[int, ResourceRelationship] = {}
    truncated = False

    for _ in range(depth):
        if not frontier:
            break
        relationships = (
            ResourceRelationship.objects.select_related(
                "source_resource__client",
                "target_resource__client",
            )
            .filter(
                Q(source_resource_id__in=frontier) | Q(target_resource_id__in=frontier),
                source_resource_id__in=visible_ids,
                target_resource_id__in=visible_ids,
            )
            .order_by("id")
        )
        next_frontier: set[int] = set()
        for relationship in relationships:
            if len(edge_rows) >= MAX_TOPOLOGY_EDGES:
                truncated = True
                break
            edge_rows[relationship.id] = relationship
            for candidate_id in (
                relationship.source_resource_id,
                relationship.target_resource_id,
            ):
                if candidate_id not in node_ids:
                    if len(node_ids) >= MAX_TOPOLOGY_NODES:
                        truncated = True
                        continue
                    node_ids.add(candidate_id)
                    next_frontier.add(candidate_id)
        frontier = next_frontier
        if truncated:
            break

    resources = {
        resource.id: resource
        for resource in visible.filter(id__in=node_ids).order_by("name", "id")
    }
    edges = [
        TopologyEdgeOut(
            id=relationship.id,
            source_id=relationship.source_resource_id,
            target_id=relationship.target_resource_id,
            relationship_type=relationship.relationship_type,
            relationship_label=relationship.get_relationship_type_display(),
            label=relationship.label,
        )
        for relationship in edge_rows.values()
        if relationship.source_resource_id in resources
        and relationship.target_resource_id in resources
    ]
    return ResourceTopologyOut(
        root_id=root.id,
        depth=depth,
        nodes=[_node(resource, root.id) for resource in resources.values()],
        edges=edges,
        truncated=truncated,
    )

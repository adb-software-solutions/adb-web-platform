from __future__ import annotations

from datetime import date, datetime
from typing import TypeAlias

from django.http import HttpRequest
from ninja import Router, Schema

from apps.infrastructure.data_application_edit import data_application_edit_values
from apps.infrastructure.models import InfrastructureResource, Network, ServerProfile, Subnet
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.infrastructure.web_domain_edit import web_domain_edit_values
from authentication.ninja.schemas import ProblemDetail

infrastructure_specialist_edit_router = Router(tags=["admin-infrastructure-specialist-edit"])
StaffProblem = tuple[int, dict[str, object]]
SpecialistEditValue: TypeAlias = str | int | bool | list[str] | None


class InfrastructureSpecialistEditOut(Schema):
    resource_id: int
    resource_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    name: str
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    values: dict[str, SpecialistEditValue]


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(403, "You do not have permission to access this resource.", "forbidden")
    if not request.user.has_perm("infrastructure.view_infrastructureresource"):
        return _problem(
            403,
            "You do not have permission to view infrastructure resources.",
            "forbidden",
        )
    return None


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _resource_out(
    resource: InfrastructureResource,
    values: dict[str, SpecialistEditValue],
) -> InfrastructureSpecialistEditOut:
    return InfrastructureSpecialistEditOut(
        resource_id=resource.id,
        resource_type=resource.resource_type,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        name=resource.name,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        description=resource.description,
        values=values,
    )


def _server_edit(resource: InfrastructureResource) -> InfrastructureSpecialistEditOut | None:
    server = ServerProfile.objects.filter(resource=resource).first()
    if server is None:
        return None
    provider_account = server.provider_account if server.provider_account_id else None
    return _resource_out(
        resource,
        {
            "hostname": server.hostname,
            "fqdn": server.fqdn,
            "purpose": server.purpose,
            "role": server.role,
            "compute_type": server.compute_type,
            "architecture": server.architecture,
            "cpu_model": server.cpu_model,
            "cpu_cores": server.cpu_cores,
            "ram_mb": server.ram_mb,
            "root_disk_gb": server.root_disk_gb,
            "os_family": server.os_family,
            "distribution": server.distribution,
            "os_version": server.os_version,
            "kernel_version": server.kernel_version,
            "provider_account_resource_id": (
                provider_account.resource_id if provider_account else None
            ),
            "provider_resource_id": server.provider_resource_id,
            "region": server.region,
            "zone": server.zone,
            "datacenter": server.datacenter,
            "virtualization_type": server.virtualization_type,
            "hypervisor": server.hypervisor,
            "ssh_port": server.ssh_port,
            "timezone": server.timezone,
            "automatic_updates": server.automatic_updates,
            "patch_window": server.patch_window,
            "last_patched_at": _iso(server.last_patched_at),
            "commissioned_at": _iso(server.commissioned_at),
            "decommissioned_at": _iso(server.decommissioned_at),
        },
    )


def _network_edit(resource: InfrastructureResource) -> InfrastructureSpecialistEditOut | None:
    network = Network.objects.filter(resource=resource).first()
    if network is None:
        return None
    provider_account = network.provider_account if network.provider_account_id else None
    return _resource_out(
        resource,
        {
            "network_type": network.network_type,
            "provider_account_resource_id": (
                provider_account.resource_id if provider_account else None
            ),
            "provider_network_id": network.provider_network_id,
            "cidr": network.cidr,
            "gateway": network.gateway,
            "region": network.region,
            "vlan_id": network.vlan_id,
            "dns_servers": [str(value) for value in network.dns_servers],
        },
    )


def _subnet_edit(resource: InfrastructureResource) -> InfrastructureSpecialistEditOut | None:
    subnet = Subnet.objects.select_related("network").filter(resource=resource).first()
    if subnet is None:
        return None
    return _resource_out(
        resource,
        {
            "network_resource_id": subnet.network.resource_id,
            "cidr": subnet.cidr,
            "gateway": subnet.gateway,
            "vlan_id": subnet.vlan_id,
            "availability_zone": subnet.availability_zone,
            "purpose": subnet.purpose,
        },
    )


@infrastructure_specialist_edit_router.get(
    "/infrastructure/resources/{resource_id}/specialist-edit",
    response={
        200: InfrastructureSpecialistEditOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_infrastructure_specialist_edit_details(
    request: HttpRequest,
    resource_id: int,
) -> InfrastructureSpecialistEditOut | StaffProblem:
    """Return safe exact specialist metadata for the native resource editor."""

    problem = _permission_problem(request)
    if problem:
        return problem

    resource = (
        scope_infrastructure_resources_for_user(
            request.user,
            InfrastructureResource.objects.select_related("client"),
        )
        .filter(id=resource_id)
        .first()
    )
    if resource is None:
        return _problem(404, "Infrastructure resource not found.", "not_found")

    if resource.resource_type == InfrastructureResource.ResourceType.SERVER:
        result = _server_edit(resource)
    elif resource.resource_type == InfrastructureResource.ResourceType.NETWORK:
        result = _network_edit(resource)
    elif resource.resource_type == InfrastructureResource.ResourceType.SUBNET:
        result = _subnet_edit(resource)
    else:
        values = data_application_edit_values(resource)
        if values is None:
            values = web_domain_edit_values(resource)
        result = _resource_out(resource, values) if values is not None else None

    if result is None:
        return _problem(
            404,
            "Native specialist details were not found for this infrastructure resource.",
            "not_found",
        )
    return result

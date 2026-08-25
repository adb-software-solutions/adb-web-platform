from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import (
    IPAddress,
    InfrastructureResource,
    Network,
    NetworkInterface,
    ProviderAccount,
    ServerProfile,
    Subnet,
)
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .specialist_schemas import (
    ClientOptionOut,
    IPAddressCreateIn,
    IPAddressOut,
    IPAddressUpdateIn,
    InfrastructureSpecialistOptionsOut,
    NetworkCreateIn,
    NetworkInterfaceCreateIn,
    NetworkInterfaceOut,
    NetworkInterfaceUpdateIn,
    NetworkOptionOut,
    NetworkOut,
    NetworkUpdateIn,
    ProviderAccountOptionOut,
    ServerCreateIn,
    ServerOut,
    ServerUpdateIn,
    StructuredResourceIn,
    StructuredResourceUpdateIn,
    SubnetCreateIn,
    SubnetOptionOut,
    SubnetOut,
    SubnetUpdateIn,
)

infrastructure_specialist_router = Router(tags=["admin-infrastructure-specialists"])
StaffProblem = tuple[int, dict[str, object]]
CURRENT_LIFECYCLE_STATUSES = (
    InfrastructureResource.LifecycleStatus.PLANNED,
    InfrastructureResource.LifecycleStatus.ACTIVE,
    InfrastructureResource.LifecycleStatus.MAINTENANCE,
    InfrastructureResource.LifecycleStatus.DEPRECATED,
)


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _permission_problem(
    request: HttpRequest,
    *permissions: str,
) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(403, "You do not have permission to access this resource.", "forbidden")
    if not all(request.user.has_perm(permission) for permission in permissions):
        return _problem(403, "You do not have permission to manage this infrastructure.", "forbidden")
    return None


def _validation_problem(error: ValidationError) -> StaffProblem:
    messages: list[str] = []
    if hasattr(error, "message_dict"):
        for field_messages in error.message_dict.values():
            messages.extend(str(message) for message in field_messages)
    else:
        messages.extend(str(message) for message in error.messages)
    return _problem(400, " ".join(messages), "invalid_infrastructure")


def _resolve_client(
    request: HttpRequest,
    ownership_type: str,
    client_id: int | None,
) -> tuple[Client | None, StaffProblem | None]:
    if ownership_type == OwnershipType.INTERNAL:
        if client_id is not None:
            return None, _problem(
                400,
                "Internal infrastructure cannot reference a Client.",
                "invalid_ownership",
            )
        return None, None

    if client_id is None:
        return None, _problem(
            400,
            "Client-owned infrastructure requires a Client.",
            "client_required",
        )
    client = (
        scope_clients_for_user(request.user, Client.objects.all())
        .filter(id=client_id)
        .first()
    )
    if client is None:
        return None, _problem(404, "Client not found.", "not_found")
    return client, None


def _visible_provider_account(
    request: HttpRequest,
    resource_id: int | None,
) -> ProviderAccount | None:
    if resource_id is None:
        return None
    visible = scope_infrastructure_resources_for_user(request.user)
    return (
        ProviderAccount.objects.select_related("resource", "resource__client", "provider")
        .filter(resource__in=visible, resource_id=resource_id)
        .first()
    )


def _visible_network(request: HttpRequest, resource_id: int | None) -> Network | None:
    if resource_id is None:
        return None
    visible = scope_infrastructure_resources_for_user(request.user)
    return (
        Network.objects.select_related("resource", "resource__client")
        .filter(resource__in=visible, resource_id=resource_id)
        .first()
    )


def _visible_subnet(request: HttpRequest, resource_id: int | None) -> Subnet | None:
    if resource_id is None:
        return None
    visible = scope_infrastructure_resources_for_user(request.user)
    return (
        Subnet.objects.select_related("resource", "resource__client", "network__resource")
        .filter(resource__in=visible, resource_id=resource_id)
        .first()
    )


def _new_resource(
    request: HttpRequest,
    payload: StructuredResourceIn,
    resource_type: str,
) -> tuple[InfrastructureResource | None, StaffProblem | None]:
    client, problem = _resolve_client(request, payload.ownership_type, payload.client_id)
    if problem:
        return None, problem
    resource = InfrastructureResource(
        ownership_type=payload.ownership_type,
        client=client,
        name=payload.name.strip(),
        resource_type=resource_type,
        lifecycle_status=payload.lifecycle_status,
        environment=payload.environment,
        criticality=payload.criticality,
        description=payload.description.strip(),
        created_by_id=request.user.pk,
        updated_by_id=request.user.pk,
    )
    try:
        resource.full_clean()
    except ValidationError as error:
        return None, _validation_problem(error)
    resource.save()
    return resource, None


def _update_resource(
    request: HttpRequest,
    resource: InfrastructureResource,
    payload: StructuredResourceUpdateIn,
) -> StaffProblem | None:
    resource.name = payload.name.strip()
    resource.lifecycle_status = payload.lifecycle_status
    resource.environment = payload.environment
    resource.criticality = payload.criticality
    resource.description = payload.description.strip()
    resource.updated_by_id = request.user.pk
    resource.archived_at = (
        timezone.now()
        if payload.lifecycle_status == InfrastructureResource.LifecycleStatus.ARCHIVED
        else None
    )
    try:
        resource.full_clean()
    except ValidationError as error:
        return _validation_problem(error)
    resource.save()
    return None


def _archive_resource(request: HttpRequest, resource: InfrastructureResource) -> None:
    resource.lifecycle_status = InfrastructureResource.LifecycleStatus.ARCHIVED
    resource.archived_at = timezone.now()
    resource.updated_by_id = request.user.pk
    resource.save(
        update_fields=["lifecycle_status", "archived_at", "updated_by", "updated_at"]
    )


def _ip_out(ip_address: IPAddress) -> IPAddressOut:
    return IPAddressOut(
        id=ip_address.id,
        address=ip_address.address,
        scope=ip_address.scope,
        is_primary=ip_address.is_primary,
        ptr_record=ip_address.ptr_record,
        description=ip_address.description,
        interface_id=ip_address.interface_id,
    )


def _interface_out(interface: NetworkInterface) -> NetworkInterfaceOut:
    return NetworkInterfaceOut(
        id=interface.id,
        name=interface.name,
        mac_address=interface.mac_address,
        network_resource_id=interface.network.resource_id if interface.network else None,
        network_name=interface.network.resource.name if interface.network else None,
        subnet_resource_id=interface.subnet.resource_id if interface.subnet else None,
        subnet_name=interface.subnet.resource.name if interface.subnet else None,
        mtu=interface.mtu,
        description=interface.description,
        ip_addresses=[_ip_out(item) for item in interface.ip_addresses.all()],
    )


def _server_queryset(request: HttpRequest) -> Any:
    visible = scope_infrastructure_resources_for_user(request.user)
    return (
        ServerProfile.objects.select_related(
            "resource",
            "resource__client",
            "provider_account__resource",
            "provider_account__provider",
        )
        .prefetch_related(
            "interfaces__network__resource",
            "interfaces__subnet__resource",
            "interfaces__ip_addresses",
            "resource__ip_addresses",
        )
        .filter(resource__in=visible)
    )


def _server_out(server: ServerProfile) -> ServerOut:
    resource = server.resource
    provider_account = server.provider_account
    direct_ips = [item for item in resource.ip_addresses.all() if item.interface_id is None]
    return ServerOut(
        resource_id=resource.id,
        name=resource.name,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        description=resource.description,
        hostname=server.hostname,
        fqdn=server.fqdn,
        purpose=server.purpose,
        role=server.role,
        compute_type=server.compute_type,
        architecture=server.architecture,
        cpu_model=server.cpu_model,
        cpu_cores=server.cpu_cores,
        ram_mb=server.ram_mb,
        root_disk_gb=server.root_disk_gb,
        os_family=server.os_family,
        distribution=server.distribution,
        os_version=server.os_version,
        kernel_version=server.kernel_version,
        provider_account_resource_id=(provider_account.resource_id if provider_account else None),
        provider_account_name=(provider_account.resource.name if provider_account else None),
        provider_name=(provider_account.provider.name if provider_account else None),
        provider_resource_id=server.provider_resource_id,
        region=server.region,
        zone=server.zone,
        datacenter=server.datacenter,
        virtualization_type=server.virtualization_type,
        hypervisor=server.hypervisor,
        ssh_port=server.ssh_port,
        timezone=server.timezone,
        automatic_updates=server.automatic_updates,
        patch_window=server.patch_window,
        last_patched_at=server.last_patched_at,
        commissioned_at=server.commissioned_at,
        decommissioned_at=server.decommissioned_at,
        interfaces=[_interface_out(item) for item in server.interfaces.all()],
        direct_ip_addresses=[_ip_out(item) for item in direct_ips],
        updated_at=resource.updated_at,
    )


def _network_out(network: Network) -> NetworkOut:
    resource = network.resource
    provider_account = network.provider_account
    return NetworkOut(
        resource_id=resource.id,
        name=resource.name,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        description=resource.description,
        network_type=network.network_type,
        provider_account_resource_id=(provider_account.resource_id if provider_account else None),
        provider_account_name=(provider_account.resource.name if provider_account else None),
        provider_name=(provider_account.provider.name if provider_account else None),
        provider_network_id=network.provider_network_id,
        cidr=network.cidr,
        gateway=network.gateway,
        region=network.region,
        vlan_id=network.vlan_id,
        dns_servers=[str(value) for value in network.dns_servers],
        updated_at=resource.updated_at,
    )


def _subnet_out(subnet: Subnet) -> SubnetOut:
    resource = subnet.resource
    return SubnetOut(
        resource_id=resource.id,
        name=resource.name,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        description=resource.description,
        network_resource_id=subnet.network.resource_id,
        network_name=subnet.network.resource.name,
        cidr=subnet.cidr,
        gateway=subnet.gateway,
        vlan_id=subnet.vlan_id,
        availability_zone=subnet.availability_zone,
        purpose=subnet.purpose,
        updated_at=resource.updated_at,
    )


def _populate_server(server: ServerProfile, payload: ServerCreateIn | ServerUpdateIn) -> None:
    for field in (
        "hostname",
        "fqdn",
        "purpose",
        "role",
        "compute_type",
        "architecture",
        "cpu_model",
        "cpu_cores",
        "ram_mb",
        "root_disk_gb",
        "os_family",
        "distribution",
        "os_version",
        "kernel_version",
        "provider_resource_id",
        "region",
        "zone",
        "datacenter",
        "virtualization_type",
        "hypervisor",
        "ssh_port",
        "timezone",
        "automatic_updates",
        "patch_window",
        "last_patched_at",
        "commissioned_at",
        "decommissioned_at",
    ):
        setattr(server, field, getattr(payload, field))


def _populate_network(network: Network, payload: NetworkCreateIn | NetworkUpdateIn) -> None:
    for field in (
        "network_type",
        "provider_network_id",
        "cidr",
        "gateway",
        "region",
        "vlan_id",
        "dns_servers",
    ):
        setattr(network, field, getattr(payload, field))


@infrastructure_specialist_router.get(
    "/infrastructure/specialist-options",
    response={200: InfrastructureSpecialistOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def infrastructure_specialist_options(
    request: HttpRequest,
) -> InfrastructureSpecialistOptionsOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.view_infrastructureresource")
    if problem:
        return problem

    clients = scope_clients_for_user(request.user, Client.objects.filter(status="active"))
    visible = scope_infrastructure_resources_for_user(request.user)
    provider_accounts = ProviderAccount.objects.select_related(
        "resource", "resource__client", "provider"
    ).filter(resource__in=visible, resource__lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES)
    networks = Network.objects.select_related("resource", "resource__client").filter(
        resource__in=visible,
        resource__lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES,
    )
    subnets = Subnet.objects.select_related(
        "resource", "resource__client", "network__resource"
    ).filter(resource__in=visible, resource__lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES)

    return InfrastructureSpecialistOptionsOut(
        clients=[ClientOptionOut(id=item.id, name=str(item)) for item in clients.order_by("company", "name")],
        provider_accounts=[
            ProviderAccountOptionOut(
                resource_id=item.resource_id,
                name=item.resource.name,
                provider_name=item.provider.name,
                ownership_type=item.resource.ownership_type,
                client_id=item.resource.client_id,
                client_name=str(item.resource.client) if item.resource.client else None,
            )
            for item in provider_accounts.order_by("resource__name")
        ],
        networks=[
            NetworkOptionOut(
                resource_id=item.resource_id,
                name=item.resource.name,
                ownership_type=item.resource.ownership_type,
                client_id=item.resource.client_id,
                client_name=str(item.resource.client) if item.resource.client else None,
            )
            for item in networks.order_by("resource__name")
        ],
        subnets=[
            SubnetOptionOut(
                resource_id=item.resource_id,
                name=item.resource.name,
                network_resource_id=item.network.resource_id,
                cidr=item.cidr,
                ownership_type=item.resource.ownership_type,
                client_id=item.resource.client_id,
                client_name=str(item.resource.client) if item.resource.client else None,
            )
            for item in subnets.order_by("network__resource__name", "cidr")
        ],
    )


@infrastructure_specialist_router.post(
    "/infrastructure/servers",
    response={201: ServerOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def create_server(
    request: HttpRequest,
    payload: ServerCreateIn,
) -> tuple[int, ServerOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_serverprofile",
    )
    if problem:
        return problem

    provider_account = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider_account is None:
        return _problem(404, "Provider account not found.", "not_found")

    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request, payload, InfrastructureResource.ResourceType.SERVER
            )
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            assert resource is not None
            server = ServerProfile(resource=resource, provider_account=provider_account)
            _populate_server(server, payload)
            server.full_clean()
            server.save()
    except ValidationError as error:
        return _validation_problem(error)

    created = _server_queryset(request).get(resource_id=resource.id)
    return 201, _server_out(created)


@infrastructure_specialist_router.get(
    "/infrastructure/servers/{resource_id}",
    response={200: ServerOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def get_server(request: HttpRequest, resource_id: int) -> ServerOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_serverprofile",
    )
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    return _server_out(server)


@infrastructure_specialist_router.put(
    "/infrastructure/servers/{resource_id}",
    response={200: ServerOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def update_server(
    request: HttpRequest,
    resource_id: int,
    payload: ServerUpdateIn,
) -> ServerOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_serverprofile",
    )
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    provider_account = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider_account is None:
        return _problem(404, "Provider account not found.", "not_found")

    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, server.resource, payload)
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            server.provider_account = provider_account
            _populate_server(server, payload)
            server.full_clean()
            server.save()
    except ValidationError as error:
        return _validation_problem(error)

    refreshed = _server_queryset(request).get(resource_id=resource_id)
    return _server_out(refreshed)


@infrastructure_specialist_router.post(
    "/infrastructure/servers/{resource_id}/archive",
    response={200: ServerOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def archive_server(request: HttpRequest, resource_id: int) -> ServerOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_serverprofile",
    )
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    _archive_resource(request, server.resource)
    refreshed = _server_queryset(request).get(resource_id=resource_id)
    return _server_out(refreshed)


@infrastructure_specialist_router.post(
    "/infrastructure/networks",
    response={201: NetworkOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def create_network(
    request: HttpRequest,
    payload: NetworkCreateIn,
) -> tuple[int, NetworkOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_network",
    )
    if problem:
        return problem
    provider_account = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider_account is None:
        return _problem(404, "Provider account not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request, payload, InfrastructureResource.ResourceType.NETWORK
            )
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            assert resource is not None
            network = Network(resource=resource, provider_account=provider_account)
            _populate_network(network, payload)
            network.full_clean()
            network.save()
    except ValidationError as error:
        return _validation_problem(error)
    created = Network.objects.select_related(
        "resource", "resource__client", "provider_account__resource", "provider_account__provider"
    ).get(resource_id=resource.id)
    return 201, _network_out(created)


@infrastructure_specialist_router.put(
    "/infrastructure/networks/{resource_id}",
    response={200: NetworkOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def update_network(
    request: HttpRequest,
    resource_id: int,
    payload: NetworkUpdateIn,
) -> NetworkOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_network",
    )
    if problem:
        return problem
    network = _visible_network(request, resource_id)
    if network is None:
        return _problem(404, "Network not found.", "not_found")
    provider_account = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider_account is None:
        return _problem(404, "Provider account not found.", "not_found")
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, network.resource, payload)
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            network.provider_account = provider_account
            _populate_network(network, payload)
            network.full_clean()
            network.save()
    except ValidationError as error:
        return _validation_problem(error)
    network = Network.objects.select_related(
        "resource", "resource__client", "provider_account__resource", "provider_account__provider"
    ).get(resource_id=resource_id)
    return _network_out(network)


@infrastructure_specialist_router.post(
    "/infrastructure/networks/{resource_id}/archive",
    response={200: NetworkOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def archive_network(request: HttpRequest, resource_id: int) -> NetworkOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_network",
    )
    if problem:
        return problem
    network = _visible_network(request, resource_id)
    if network is None:
        return _problem(404, "Network not found.", "not_found")
    _archive_resource(request, network.resource)
    return _network_out(network)


@infrastructure_specialist_router.post(
    "/infrastructure/subnets",
    response={201: SubnetOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def create_subnet(
    request: HttpRequest,
    payload: SubnetCreateIn,
) -> tuple[int, SubnetOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_subnet",
    )
    if problem:
        return problem
    network = _visible_network(request, payload.network_resource_id)
    if network is None:
        return _problem(404, "Network not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request, payload, InfrastructureResource.ResourceType.SUBNET
            )
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            assert resource is not None
            subnet = Subnet(
                resource=resource,
                network=network,
                cidr=payload.cidr,
                gateway=payload.gateway,
                vlan_id=payload.vlan_id,
                availability_zone=payload.availability_zone.strip(),
                purpose=payload.purpose.strip(),
            )
            subnet.full_clean()
            subnet.save()
    except ValidationError as error:
        return _validation_problem(error)
    created = Subnet.objects.select_related(
        "resource", "resource__client", "network__resource"
    ).get(resource_id=resource.id)
    return 201, _subnet_out(created)


@infrastructure_specialist_router.put(
    "/infrastructure/subnets/{resource_id}",
    response={200: SubnetOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def update_subnet(
    request: HttpRequest,
    resource_id: int,
    payload: SubnetUpdateIn,
) -> SubnetOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_subnet",
    )
    if problem:
        return problem
    subnet = _visible_subnet(request, resource_id)
    if subnet is None:
        return _problem(404, "Subnet not found.", "not_found")
    network = _visible_network(request, payload.network_resource_id)
    if network is None:
        return _problem(404, "Network not found.", "not_found")
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, subnet.resource, payload)
            if resource_problem:
                transaction.set_rollback(True)
                return resource_problem
            subnet.network = network
            subnet.cidr = payload.cidr
            subnet.gateway = payload.gateway
            subnet.vlan_id = payload.vlan_id
            subnet.availability_zone = payload.availability_zone.strip()
            subnet.purpose = payload.purpose.strip()
            subnet.full_clean()
            subnet.save()
    except ValidationError as error:
        return _validation_problem(error)
    refreshed = Subnet.objects.select_related(
        "resource", "resource__client", "network__resource"
    ).get(resource_id=resource_id)
    return _subnet_out(refreshed)


@infrastructure_specialist_router.post(
    "/infrastructure/subnets/{resource_id}/archive",
    response={200: SubnetOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def archive_subnet(request: HttpRequest, resource_id: int) -> SubnetOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_subnet",
    )
    if problem:
        return problem
    subnet = _visible_subnet(request, resource_id)
    if subnet is None:
        return _problem(404, "Subnet not found.", "not_found")
    _archive_resource(request, subnet.resource)
    return _subnet_out(subnet)


def _resolve_interface_links(
    request: HttpRequest,
    network_resource_id: int | None,
    subnet_resource_id: int | None,
) -> tuple[Network | None, Subnet | None, StaffProblem | None]:
    network = _visible_network(request, network_resource_id)
    subnet = _visible_subnet(request, subnet_resource_id)
    if network_resource_id is not None and network is None:
        return None, None, _problem(404, "Network not found.", "not_found")
    if subnet_resource_id is not None and subnet is None:
        return None, None, _problem(404, "Subnet not found.", "not_found")
    return network, subnet, None


@infrastructure_specialist_router.post(
    "/infrastructure/servers/{resource_id}/interfaces",
    response={201: NetworkInterfaceOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def create_network_interface(
    request: HttpRequest,
    resource_id: int,
    payload: NetworkInterfaceCreateIn,
) -> tuple[int, NetworkInterfaceOut | dict[str, object]]:
    problem = _permission_problem(request, "infrastructure.add_networkinterface")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    network, subnet, link_problem = _resolve_interface_links(
        request, payload.network_resource_id, payload.subnet_resource_id
    )
    if link_problem:
        return link_problem
    interface = NetworkInterface(
        server=server,
        name=payload.name.strip(),
        mac_address=payload.mac_address.strip(),
        network=network,
        subnet=subnet,
        mtu=payload.mtu,
        description=payload.description.strip(),
    )
    try:
        interface.full_clean()
        interface.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _interface_out(interface)


@infrastructure_specialist_router.put(
    "/infrastructure/servers/{resource_id}/interfaces/{interface_id}",
    response={200: NetworkInterfaceOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def update_network_interface(
    request: HttpRequest,
    resource_id: int,
    interface_id: int,
    payload: NetworkInterfaceUpdateIn,
) -> NetworkInterfaceOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.change_networkinterface")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    interface = NetworkInterface.objects.filter(id=interface_id, server=server).first()
    if interface is None:
        return _problem(404, "Network interface not found.", "not_found")
    network, subnet, link_problem = _resolve_interface_links(
        request, payload.network_resource_id, payload.subnet_resource_id
    )
    if link_problem:
        return link_problem
    interface.name = payload.name.strip()
    interface.mac_address = payload.mac_address.strip()
    interface.network = network
    interface.subnet = subnet
    interface.mtu = payload.mtu
    interface.description = payload.description.strip()
    try:
        interface.full_clean()
        interface.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _interface_out(interface)


@infrastructure_specialist_router.delete(
    "/infrastructure/servers/{resource_id}/interfaces/{interface_id}",
    response={204: None, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def delete_network_interface(
    request: HttpRequest,
    resource_id: int,
    interface_id: int,
) -> tuple[int, dict[str, object] | None]:
    problem = _permission_problem(request, "infrastructure.delete_networkinterface")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    interface = NetworkInterface.objects.filter(id=interface_id, server=server).first()
    if interface is None:
        return _problem(404, "Network interface not found.", "not_found")
    interface.delete()
    return 204, None


@infrastructure_specialist_router.post(
    "/infrastructure/servers/{resource_id}/ip-addresses",
    response={201: IPAddressOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def create_ip_address(
    request: HttpRequest,
    resource_id: int,
    payload: IPAddressCreateIn,
) -> tuple[int, IPAddressOut | dict[str, object]]:
    problem = _permission_problem(request, "infrastructure.add_ipaddress")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    interface = None
    if payload.interface_id is not None:
        interface = NetworkInterface.objects.filter(
            id=payload.interface_id, server=server
        ).first()
        if interface is None:
            return _problem(404, "Network interface not found.", "not_found")
    ip_address = IPAddress(
        resource=server.resource,
        interface=interface,
        address=payload.address,
        scope=payload.scope,
        is_primary=payload.is_primary,
        ptr_record=payload.ptr_record.strip(),
        description=payload.description.strip(),
    )
    try:
        ip_address.full_clean()
        ip_address.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _ip_out(ip_address)


@infrastructure_specialist_router.put(
    "/infrastructure/servers/{resource_id}/ip-addresses/{ip_address_id}",
    response={200: IPAddressOut, 400: ProblemDetail, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def update_ip_address(
    request: HttpRequest,
    resource_id: int,
    ip_address_id: int,
    payload: IPAddressUpdateIn,
) -> IPAddressOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.change_ipaddress")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    ip_address = IPAddress.objects.filter(id=ip_address_id, resource=server.resource).first()
    if ip_address is None:
        return _problem(404, "IP address not found.", "not_found")
    interface = None
    if payload.interface_id is not None:
        interface = NetworkInterface.objects.filter(
            id=payload.interface_id, server=server
        ).first()
        if interface is None:
            return _problem(404, "Network interface not found.", "not_found")
    ip_address.interface = interface
    ip_address.address = payload.address
    ip_address.scope = payload.scope
    ip_address.is_primary = payload.is_primary
    ip_address.ptr_record = payload.ptr_record.strip()
    ip_address.description = payload.description.strip()
    try:
        ip_address.full_clean()
        ip_address.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _ip_out(ip_address)


@infrastructure_specialist_router.delete(
    "/infrastructure/servers/{resource_id}/ip-addresses/{ip_address_id}",
    response={204: None, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def delete_ip_address(
    request: HttpRequest,
    resource_id: int,
    ip_address_id: int,
) -> tuple[int, dict[str, object] | None]:
    problem = _permission_problem(request, "infrastructure.delete_ipaddress")
    if problem:
        return problem
    server = _server_queryset(request).filter(resource_id=resource_id).first()
    if server is None:
        return _problem(404, "Server not found.", "not_found")
    ip_address = IPAddress.objects.filter(id=ip_address_id, resource=server.resource).first()
    if ip_address is None:
        return _problem(404, "IP address not found.", "not_found")
    ip_address.delete()
    return 204, None

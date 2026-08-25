from datetime import date, datetime
from typing import Literal

from ninja import Schema

InfrastructureOwnership = Literal["internal", "client"]
InfrastructureLifecycle = Literal[
    "planned",
    "active",
    "maintenance",
    "deprecated",
    "retired",
    "archived",
]
InfrastructureEnvironment = Literal[
    "production",
    "staging",
    "development",
    "testing",
    "shared",
    "not_applicable",
]
InfrastructureCriticality = Literal["low", "normal", "high", "critical"]


class StructuredResourceIn(Schema):
    ownership_type: InfrastructureOwnership = "internal"
    client_id: int | None = None
    name: str
    lifecycle_status: InfrastructureLifecycle = "active"
    environment: InfrastructureEnvironment = "not_applicable"
    criticality: InfrastructureCriticality = "normal"
    description: str = ""


class StructuredResourceUpdateIn(Schema):
    name: str
    lifecycle_status: InfrastructureLifecycle
    environment: InfrastructureEnvironment
    criticality: InfrastructureCriticality
    description: str = ""


class ProviderAccountOptionOut(Schema):
    resource_id: int
    name: str
    provider_name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class ClientOptionOut(Schema):
    id: int
    name: str


class NetworkOptionOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class SubnetOptionOut(Schema):
    resource_id: int
    name: str
    network_resource_id: int
    cidr: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class InfrastructureSpecialistOptionsOut(Schema):
    clients: list[ClientOptionOut]
    provider_accounts: list[ProviderAccountOptionOut]
    networks: list[NetworkOptionOut]
    subnets: list[SubnetOptionOut]


class ServerCreateIn(StructuredResourceIn):
    hostname: str
    fqdn: str = ""
    purpose: str = ""
    role: str = ""
    compute_type: str = "cloud_vm"
    architecture: str = ""
    cpu_model: str = ""
    cpu_cores: int | None = None
    ram_mb: int | None = None
    root_disk_gb: int | None = None
    os_family: str = "linux"
    distribution: str = ""
    os_version: str = ""
    kernel_version: str = ""
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    region: str = ""
    zone: str = ""
    datacenter: str = ""
    virtualization_type: str = ""
    hypervisor: str = ""
    ssh_port: int | None = None
    timezone: str = ""
    automatic_updates: bool | None = None
    patch_window: str = ""
    last_patched_at: datetime | None = None
    commissioned_at: date | None = None
    decommissioned_at: date | None = None


class ServerUpdateIn(StructuredResourceUpdateIn):
    hostname: str
    fqdn: str = ""
    purpose: str = ""
    role: str = ""
    compute_type: str
    architecture: str = ""
    cpu_model: str = ""
    cpu_cores: int | None = None
    ram_mb: int | None = None
    root_disk_gb: int | None = None
    os_family: str
    distribution: str = ""
    os_version: str = ""
    kernel_version: str = ""
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    region: str = ""
    zone: str = ""
    datacenter: str = ""
    virtualization_type: str = ""
    hypervisor: str = ""
    ssh_port: int | None = None
    timezone: str = ""
    automatic_updates: bool | None = None
    patch_window: str = ""
    last_patched_at: datetime | None = None
    commissioned_at: date | None = None
    decommissioned_at: date | None = None


class IPAddressOut(Schema):
    id: int
    address: str
    scope: str
    is_primary: bool
    ptr_record: str
    description: str
    interface_id: int | None


class NetworkInterfaceOut(Schema):
    id: int
    name: str
    mac_address: str
    network_resource_id: int | None
    network_name: str | None
    subnet_resource_id: int | None
    subnet_name: str | None
    mtu: int | None
    description: str
    ip_addresses: list[IPAddressOut]


class ServerOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    hostname: str
    fqdn: str
    purpose: str
    role: str
    compute_type: str
    architecture: str
    cpu_model: str
    cpu_cores: int | None
    ram_mb: int | None
    root_disk_gb: int | None
    os_family: str
    distribution: str
    os_version: str
    kernel_version: str
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    provider_resource_id: str
    region: str
    zone: str
    datacenter: str
    virtualization_type: str
    hypervisor: str
    ssh_port: int | None
    timezone: str
    automatic_updates: bool | None
    patch_window: str
    last_patched_at: datetime | None
    commissioned_at: date | None
    decommissioned_at: date | None
    interfaces: list[NetworkInterfaceOut]
    direct_ip_addresses: list[IPAddressOut]
    updated_at: datetime


class NetworkCreateIn(StructuredResourceIn):
    network_type: str = "vpc"
    provider_account_resource_id: int | None = None
    provider_network_id: str = ""
    cidr: str = ""
    gateway: str | None = None
    region: str = ""
    vlan_id: int | None = None
    dns_servers: list[str] = []


class NetworkUpdateIn(StructuredResourceUpdateIn):
    network_type: str
    provider_account_resource_id: int | None = None
    provider_network_id: str = ""
    cidr: str = ""
    gateway: str | None = None
    region: str = ""
    vlan_id: int | None = None
    dns_servers: list[str] = []


class NetworkOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    network_type: str
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    provider_network_id: str
    cidr: str
    gateway: str | None
    region: str
    vlan_id: int | None
    dns_servers: list[str]
    updated_at: datetime


class SubnetCreateIn(StructuredResourceIn):
    network_resource_id: int
    cidr: str
    gateway: str | None = None
    vlan_id: int | None = None
    availability_zone: str = ""
    purpose: str = ""


class SubnetUpdateIn(StructuredResourceUpdateIn):
    network_resource_id: int
    cidr: str
    gateway: str | None = None
    vlan_id: int | None = None
    availability_zone: str = ""
    purpose: str = ""


class SubnetOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    network_resource_id: int
    network_name: str
    cidr: str
    gateway: str | None
    vlan_id: int | None
    availability_zone: str
    purpose: str
    updated_at: datetime


class NetworkInterfaceCreateIn(Schema):
    name: str
    mac_address: str = ""
    network_resource_id: int | None = None
    subnet_resource_id: int | None = None
    mtu: int | None = None
    description: str = ""


class NetworkInterfaceUpdateIn(NetworkInterfaceCreateIn):
    pass


class IPAddressCreateIn(Schema):
    address: str
    scope: str = "private"
    is_primary: bool = False
    ptr_record: str = ""
    description: str = ""
    interface_id: int | None = None


class IPAddressUpdateIn(IPAddressCreateIn):
    pass

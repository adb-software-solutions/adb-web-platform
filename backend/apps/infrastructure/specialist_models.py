from __future__ import annotations

import ipaddress

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.ownership import OwnershipType

from .resource_models import InfrastructureResource, ProviderAccount


def _validate_resource_type(
    resource: InfrastructureResource,
    expected_type: str,
    label: str,
) -> None:
    if resource.resource_type != expected_type:
        raise ValidationError(
            {"resource": f"{label} requires an InfrastructureResource of type '{expected_type}'."}
        )


def _validate_resource_boundary(
    source: InfrastructureResource,
    target: InfrastructureResource,
    field_name: str,
) -> None:
    if (
        source.ownership_type == OwnershipType.CLIENT
        and target.ownership_type == OwnershipType.CLIENT
        and source.client_id != target.client_id
    ):
        raise ValidationError(
            {field_name: "Client-owned infrastructure cannot reference another Client's resource."}
        )


class ServerProfile(models.Model):
    """Modern typed compute/server details attached to a structured resource."""

    class ComputeType(models.TextChoices):
        VPS = "vps", "VPS"
        CLOUD_VM = "cloud_vm", "Cloud VM"
        VIRTUAL_MACHINE = "virtual_machine", "Virtual machine"
        DEDICATED = "dedicated", "Dedicated"
        BARE_METAL = "bare_metal", "Bare metal"
        HYPERVISOR = "hypervisor", "Hypervisor"
        CONTAINER_HOST = "container_host", "Container host"
        NAS = "nas", "NAS"
        OTHER = "other", "Other"

    class OSFamily(models.TextChoices):
        LINUX = "linux", "Linux"
        WINDOWS = "windows", "Windows"
        BSD = "bsd", "BSD"
        APPLIANCE = "appliance", "Appliance"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="server_profile",
    )
    hostname = models.CharField(max_length=200, db_index=True)
    fqdn = models.CharField(max_length=253, blank=True)
    purpose = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=100, blank=True)
    compute_type = models.CharField(
        max_length=30,
        choices=ComputeType.choices,
        default=ComputeType.CLOUD_VM,
    )
    architecture = models.CharField(max_length=50, blank=True)
    cpu_model = models.CharField(max_length=200, blank=True)
    cpu_cores = models.PositiveSmallIntegerField(null=True, blank=True)
    ram_mb = models.PositiveIntegerField(null=True, blank=True)
    root_disk_gb = models.PositiveIntegerField(null=True, blank=True)
    os_family = models.CharField(
        max_length=30,
        choices=OSFamily.choices,
        default=OSFamily.LINUX,
    )
    distribution = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=100, blank=True)
    kernel_version = models.CharField(max_length=100, blank=True)
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="servers",
        null=True,
        blank=True,
    )
    provider_resource_id = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=100, blank=True)
    zone = models.CharField(max_length=100, blank=True)
    datacenter = models.CharField(max_length=100, blank=True)
    virtualization_type = models.CharField(max_length=100, blank=True)
    hypervisor = models.CharField(max_length=100, blank=True)
    ssh_port = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )
    timezone = models.CharField(max_length=100, blank=True)
    automatic_updates = models.BooleanField(null=True, blank=True)
    patch_window = models.CharField(max_length=200, blank=True)
    last_patched_at = models.DateTimeField(null=True, blank=True)
    commissioned_at = models.DateField(null=True, blank=True)
    decommissioned_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["hostname", "id"]
        indexes = [
            models.Index(fields=["hostname"], name="infra_server_hostname_idx"),
            models.Index(
                fields=["provider_account", "region"],
                name="infra_server_provider_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.SERVER,
                "Server",
            )
        if self.provider_account_id and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                self.provider_account.resource,
                "provider_account",
            )
        if (
            self.commissioned_at
            and self.decommissioned_at
            and self.decommissioned_at < self.commissioned_at
        ):
            raise ValidationError(
                {"decommissioned_at": "Decommissioned date cannot precede commissioned date."}
            )

    def __str__(self) -> str:
        return self.hostname


class Network(models.Model):
    """Typed network/VPC/LAN/VLAN/VPN details."""

    class NetworkType(models.TextChoices):
        VPC = "vpc", "VPC"
        LAN = "lan", "LAN"
        VLAN = "vlan", "VLAN"
        VPN = "vpn", "VPN"
        OVERLAY = "overlay", "Overlay"
        PUBLIC = "public", "Public"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="network_profile",
    )
    network_type = models.CharField(
        max_length=30,
        choices=NetworkType.choices,
        default=NetworkType.VPC,
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="networks",
        null=True,
        blank=True,
    )
    provider_network_id = models.CharField(max_length=200, blank=True)
    cidr = models.CharField(max_length=64, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    region = models.CharField(max_length=100, blank=True)
    vlan_id = models.PositiveSmallIntegerField(null=True, blank=True)
    dns_servers = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.NETWORK,
                "Network",
            )
        if self.provider_account_id and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                self.provider_account.resource,
                "provider_account",
            )
        if self.cidr:
            try:
                ipaddress.ip_network(self.cidr, strict=False)
            except ValueError as error:
                raise ValidationError({"cidr": "Enter a valid IPv4 or IPv6 CIDR."}) from error
        if not isinstance(self.dns_servers, list):
            raise ValidationError({"dns_servers": "DNS servers must be stored as a list."})
        for value in self.dns_servers:
            try:
                ipaddress.ip_address(value)
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    {"dns_servers": f"{value!r} is not a valid IP address."}
                ) from error

    def __str__(self) -> str:
        return self.resource.name


class Subnet(models.Model):
    """Typed subnet belonging to a structured Network."""

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="subnet_profile",
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.CASCADE,
        related_name="subnets",
    )
    cidr = models.CharField(max_length=64)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    vlan_id = models.PositiveSmallIntegerField(null=True, blank=True)
    availability_zone = models.CharField(max_length=100, blank=True)
    purpose = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["network__resource__name", "cidr", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.SUBNET,
                "Subnet",
            )
        if self.network_id and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                self.network.resource,
                "network",
            )
        try:
            network = ipaddress.ip_network(self.cidr, strict=False)
        except ValueError as error:
            raise ValidationError({"cidr": "Enter a valid IPv4 or IPv6 CIDR."}) from error
        if self.gateway:
            gateway = ipaddress.ip_address(self.gateway)
            if gateway not in network:
                raise ValidationError({"gateway": "Gateway must belong to the subnet CIDR."})

    def __str__(self) -> str:
        return f"{self.resource.name} ({self.cidr})"


class NetworkInterface(models.Model):
    """Network interface attached to one modern Server profile."""

    server = models.ForeignKey(
        ServerProfile,
        on_delete=models.CASCADE,
        related_name="interfaces",
    )
    name = models.CharField(max_length=100)
    mac_address = models.CharField(max_length=32, blank=True)
    network = models.ForeignKey(
        Network,
        on_delete=models.SET_NULL,
        related_name="interfaces",
        null=True,
        blank=True,
    )
    subnet = models.ForeignKey(
        Subnet,
        on_delete=models.SET_NULL,
        related_name="interfaces",
        null=True,
        blank=True,
    )
    mtu = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(576), MaxValueValidator(65535)],
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["server__hostname", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["server", "name"],
                name="unique_server_network_interface",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.network_id:
            _validate_resource_boundary(
                self.server.resource,
                self.network.resource,
                "network",
            )
        if self.subnet_id:
            _validate_resource_boundary(
                self.server.resource,
                self.subnet.resource,
                "subnet",
            )
        if self.network_id and self.subnet_id and self.subnet.network_id != self.network_id:
            raise ValidationError({"subnet": "Subnet must belong to the selected network."})

    def __str__(self) -> str:
        return f"{self.server.hostname}:{self.name}"


class IPAddress(models.Model):
    """IPv4/IPv6 address owned by a structured resource."""

    class Scope(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        FLOATING = "floating", "Floating"
        VIRTUAL = "virtual", "Virtual"
        LOOPBACK = "loopback", "Loopback"
        OTHER = "other", "Other"

    resource = models.ForeignKey(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="ip_addresses",
    )
    interface = models.ForeignKey(
        NetworkInterface,
        on_delete=models.SET_NULL,
        related_name="ip_addresses",
        null=True,
        blank=True,
    )
    address = models.GenericIPAddressField()
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.PRIVATE,
    )
    is_primary = models.BooleanField(default=False)
    ptr_record = models.CharField(max_length=253, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "address", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "address"],
                name="unique_resource_ip_address",
            )
        ]
        indexes = [models.Index(fields=["address"], name="infra_ip_address_idx")]

    def clean(self) -> None:
        super().clean()
        if self.interface_id:
            if self.resource_id != self.interface.server.resource_id:
                raise ValidationError(
                    {"interface": "Interface must belong to the resource that owns this IP address."}
                )
            if self.interface.subnet_id:
                subnet = ipaddress.ip_network(self.interface.subnet.cidr, strict=False)
                address = ipaddress.ip_address(self.address)
                if address not in subnet:
                    raise ValidationError(
                        {"address": "IP address must belong to the interface subnet."}
                    )

    def __str__(self) -> str:
        return self.address

# Generated manually for structured compute and networking specialists.

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("infrastructure", "0003_legacy_resource_identities"),
    ]

    operations = [
        migrations.CreateModel(
            name="Network",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "network_type",
                    models.CharField(
                        choices=[
                            ("vpc", "VPC"),
                            ("lan", "LAN"),
                            ("vlan", "VLAN"),
                            ("vpn", "VPN"),
                            ("overlay", "Overlay"),
                            ("public", "Public"),
                            ("other", "Other"),
                        ],
                        default="vpc",
                        max_length=30,
                    ),
                ),
                ("provider_network_id", models.CharField(blank=True, max_length=200)),
                ("cidr", models.CharField(blank=True, max_length=64)),
                ("gateway", models.GenericIPAddressField(blank=True, null=True)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("vlan_id", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("dns_servers", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="networks",
                        to="infrastructure.provideraccount",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="network_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
        migrations.CreateModel(
            name="ServerProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("hostname", models.CharField(db_index=True, max_length=200)),
                ("fqdn", models.CharField(blank=True, max_length=253)),
                ("purpose", models.CharField(blank=True, max_length=255)),
                ("role", models.CharField(blank=True, max_length=100)),
                (
                    "compute_type",
                    models.CharField(
                        choices=[
                            ("vps", "VPS"),
                            ("cloud_vm", "Cloud VM"),
                            ("virtual_machine", "Virtual machine"),
                            ("dedicated", "Dedicated"),
                            ("bare_metal", "Bare metal"),
                            ("hypervisor", "Hypervisor"),
                            ("container_host", "Container host"),
                            ("nas", "NAS"),
                            ("other", "Other"),
                        ],
                        default="cloud_vm",
                        max_length=30,
                    ),
                ),
                ("architecture", models.CharField(blank=True, max_length=50)),
                ("cpu_model", models.CharField(blank=True, max_length=200)),
                ("cpu_cores", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("ram_mb", models.PositiveIntegerField(blank=True, null=True)),
                ("root_disk_gb", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "os_family",
                    models.CharField(
                        choices=[
                            ("linux", "Linux"),
                            ("windows", "Windows"),
                            ("bsd", "BSD"),
                            ("appliance", "Appliance"),
                            ("other", "Other"),
                        ],
                        default="linux",
                        max_length=30,
                    ),
                ),
                ("distribution", models.CharField(blank=True, max_length=100)),
                ("os_version", models.CharField(blank=True, max_length=100)),
                ("kernel_version", models.CharField(blank=True, max_length=100)),
                ("provider_resource_id", models.CharField(blank=True, max_length=200)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("zone", models.CharField(blank=True, max_length=100)),
                ("datacenter", models.CharField(blank=True, max_length=100)),
                ("virtualization_type", models.CharField(blank=True, max_length=100)),
                ("hypervisor", models.CharField(blank=True, max_length=100)),
                (
                    "ssh_port",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(65535),
                        ],
                    ),
                ),
                ("timezone", models.CharField(blank=True, max_length=100)),
                ("automatic_updates", models.BooleanField(blank=True, null=True)),
                ("patch_window", models.CharField(blank=True, max_length=200)),
                ("last_patched_at", models.DateTimeField(blank=True, null=True)),
                ("commissioned_at", models.DateField(blank=True, null=True)),
                ("decommissioned_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="servers",
                        to="infrastructure.provideraccount",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="server_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={
                "ordering": ["hostname", "id"],
                "indexes": [
                    models.Index(fields=["hostname"], name="infra_server_hostname_idx"),
                    models.Index(
                        fields=["provider_account", "region"],
                        name="infra_server_provider_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Subnet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cidr", models.CharField(max_length=64)),
                ("gateway", models.GenericIPAddressField(blank=True, null=True)),
                ("vlan_id", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("availability_zone", models.CharField(blank=True, max_length=100)),
                ("purpose", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "network",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subnets",
                        to="infrastructure.network",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subnet_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["network__resource__name", "cidr", "id"]},
        ),
        migrations.CreateModel(
            name="NetworkInterface",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("mac_address", models.CharField(blank=True, max_length=32)),
                (
                    "mtu",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(576),
                            django.core.validators.MaxValueValidator(65535),
                        ],
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "network",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interfaces",
                        to="infrastructure.network",
                    ),
                ),
                (
                    "server",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interfaces",
                        to="infrastructure.serverprofile",
                    ),
                ),
                (
                    "subnet",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="interfaces",
                        to="infrastructure.subnet",
                    ),
                ),
            ],
            options={
                "ordering": ["server__hostname", "name", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("server", "name"),
                        name="unique_server_network_interface",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="IPAddress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("address", models.GenericIPAddressField()),
                (
                    "scope",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("private", "Private"),
                            ("floating", "Floating"),
                            ("virtual", "Virtual"),
                            ("loopback", "Loopback"),
                            ("other", "Other"),
                        ],
                        default="private",
                        max_length=20,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("ptr_record", models.CharField(blank=True, max_length=253)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "interface",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ip_addresses",
                        to="infrastructure.networkinterface",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ip_addresses",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={
                "ordering": ["resource__name", "address", "id"],
                "indexes": [
                    models.Index(fields=["address"], name="infra_ip_address_idx")
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("resource", "address"),
                        name="unique_resource_ip_address",
                    )
                ],
            },
        ),
    ]

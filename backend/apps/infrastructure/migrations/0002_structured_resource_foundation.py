# Generated manually for the structured infrastructure resource foundation.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0004_timeentry_billable_default"),
        ("infrastructure", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InfrastructureTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("colour", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ServiceProvider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("slug", models.SlugField(max_length=200, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("cloud", "Cloud"),
                            ("hosting", "Hosting"),
                            ("registrar", "Registrar"),
                            ("dns", "DNS"),
                            ("cdn", "CDN"),
                            ("saas", "SaaS"),
                            ("source_control", "Source control"),
                            ("monitoring", "Monitoring"),
                            ("hardware", "Hardware"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("website_url", models.URLField(blank=True)),
                ("support_url", models.URLField(blank=True)),
                ("status_page_url", models.URLField(blank=True)),
                ("documentation_url", models.URLField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="InfrastructureResource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "ownership_type",
                    models.CharField(
                        choices=[("internal", "Internal"), ("client", "Client")],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                (
                    "resource_type",
                    models.CharField(
                        choices=[
                            ("server", "Server"),
                            ("network", "Network"),
                            ("subnet", "Subnet"),
                            ("database_instance", "Database instance"),
                            ("logical_database", "Logical database"),
                            ("application", "Application"),
                            ("application_environment", "Application environment"),
                            ("source_repository", "Source repository"),
                            ("website", "Website"),
                            ("website_endpoint", "Website endpoint"),
                            ("domain", "Domain"),
                            ("dns_zone", "DNS zone"),
                            ("tls_certificate", "TLS certificate"),
                            ("provider_account", "Provider account"),
                            ("storage", "Storage"),
                            ("backup_plan", "Backup plan"),
                            ("container_stack", "Container stack"),
                            ("kubernetes_cluster", "Kubernetes cluster"),
                            ("kubernetes_namespace", "Kubernetes namespace"),
                            ("kubernetes_workload", "Kubernetes workload"),
                            ("system_service", "System service"),
                            ("scheduled_job", "Scheduled job"),
                            ("api", "API"),
                            ("bot", "Bot"),
                            ("mobile_app", "Mobile app"),
                            ("licence", "Licence"),
                            ("email_system", "Email system"),
                            ("network_device", "Network device"),
                            ("other", "Other"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "lifecycle_status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("active", "Active"),
                            ("maintenance", "Maintenance"),
                            ("deprecated", "Deprecated"),
                            ("retired", "Retired"),
                            ("archived", "Archived"),
                        ],
                        default="active",
                        max_length=30,
                    ),
                ),
                (
                    "environment",
                    models.CharField(
                        choices=[
                            ("production", "Production"),
                            ("staging", "Staging"),
                            ("development", "Development"),
                            ("testing", "Testing"),
                            ("shared", "Shared"),
                            ("not_applicable", "Not applicable"),
                        ],
                        default="not_applicable",
                        max_length=30,
                    ),
                ),
                (
                    "criticality",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("normal", "Normal"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="normal",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "is_portal_visible",
                    models.BooleanField(
                        default=False,
                        help_text="Reserved for future client-portal visibility. Private by default.",
                    ),
                ),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="infrastructure_resources",
                        to="clients.client",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="infrastructure_resources_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tags",
                    models.ManyToManyField(
                        blank=True,
                        related_name="resources",
                        to="infrastructure.infrastructuretag",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="infrastructure_resources_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="infrastructureresource",
            constraint=models.CheckConstraint(
                condition=(
                    Q(ownership_type="internal", client__isnull=True)
                    | Q(ownership_type="client", client__isnull=False)
                ),
                name="infrastructure_resource_valid_ownership",
            ),
        ),
        migrations.AddIndex(
            model_name="infrastructureresource",
            index=models.Index(
                fields=["ownership_type", "client", "resource_type"],
                name="infra_res_owner_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="infrastructureresource",
            index=models.Index(
                fields=["lifecycle_status", "resource_type"],
                name="infra_res_lifecycle_idx",
            ),
        ),
        migrations.CreateModel(
            name="ProviderAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("account_identifier", models.CharField(blank=True, max_length=200)),
                ("tenant_id", models.CharField(blank=True, max_length=200)),
                ("project_id", models.CharField(blank=True, max_length=200)),
                ("portal_url", models.URLField(blank=True)),
                ("default_region", models.CharField(blank=True, max_length=100)),
                ("support_plan", models.CharField(blank=True, max_length=100)),
                ("billing_reference", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accounts",
                        to="infrastructure.serviceprovider",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_account",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name"]},
        ),
        migrations.CreateModel(
            name="ResourceRelationship",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "relationship_type",
                    models.CharField(
                        choices=[
                            ("depends_on", "Depends on"),
                            ("hosted_on", "Hosted on"),
                            ("connects_to", "Connects to"),
                            ("managed_by", "Managed by"),
                            ("backed_up_to", "Backed up to"),
                            ("protected_by", "Protected by"),
                            ("routes_to", "Routes to"),
                            ("uses", "Uses"),
                            ("contains", "Contains"),
                            ("related_to", "Related to"),
                        ],
                        max_length=30,
                    ),
                ),
                ("label", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="infrastructure_relationships_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outgoing_relationships",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
                (
                    "target_resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incoming_relationships",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["source_resource__name", "target_resource__name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="resourcerelationship",
            constraint=models.CheckConstraint(
                condition=~Q(source_resource=F("target_resource")),
                name="infrastructure_relationship_not_self",
            ),
        ),
        migrations.AddConstraint(
            model_name="resourcerelationship",
            constraint=models.UniqueConstraint(
                fields=("source_resource", "target_resource", "relationship_type"),
                name="unique_infrastructure_resource_relationship",
            ),
        ),
    ]

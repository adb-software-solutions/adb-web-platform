from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.ownership import OwnershipType

from .resource_models import InfrastructureResource, ProviderAccount
from .specialist_models import ServerProfile


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


def _validate_parent_boundary(
    child: InfrastructureResource,
    parent: InfrastructureResource,
    field_name: str,
) -> None:
    _validate_resource_boundary(child, parent, field_name)
    if (
        child.ownership_type == OwnershipType.INTERNAL
        and parent.ownership_type == OwnershipType.CLIENT
    ):
        raise ValidationError(
            {field_name: "Internal infrastructure cannot belong to a Client-owned parent resource."}
        )


class DatabaseInstance(models.Model):
    """Database service/instance that may host one or more logical databases."""

    class Engine(models.TextChoices):
        POSTGRESQL = "postgresql", "PostgreSQL"
        MYSQL = "mysql", "MySQL"
        MARIADB = "mariadb", "MariaDB"
        MONGODB = "mongodb", "MongoDB"
        REDIS = "redis", "Redis"
        SQL_SERVER = "sql_server", "SQL Server"
        ORACLE = "oracle", "Oracle"
        OTHER = "other", "Other"

    class HostingType(models.TextChoices):
        MANAGED = "managed", "Managed service"
        SELF_HOSTED = "self_hosted", "Self-hosted"
        CONTAINER = "container", "Container"
        APPLIANCE = "appliance", "Appliance"
        OTHER = "other", "Other"

    class TLSMode(models.TextChoices):
        REQUIRED = "required", "Required"
        PREFERRED = "preferred", "Preferred"
        DISABLED = "disabled", "Disabled"
        UNKNOWN = "unknown", "Unknown"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="database_instance",
    )
    engine = models.CharField(max_length=30, choices=Engine.choices)
    engine_version = models.CharField(max_length=100, blank=True)
    hosting_type = models.CharField(
        max_length=30,
        choices=HostingType.choices,
        default=HostingType.MANAGED,
    )
    server = models.ForeignKey(
        ServerProfile,
        on_delete=models.SET_NULL,
        related_name="database_instances",
        null=True,
        blank=True,
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="database_instances",
        null=True,
        blank=True,
    )
    provider_resource_id = models.CharField(max_length=200, blank=True)
    endpoint = models.CharField(max_length=253, blank=True)
    port = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )
    region = models.CharField(max_length=100, blank=True)
    zone = models.CharField(max_length=100, blank=True)
    tls_mode = models.CharField(
        max_length=20,
        choices=TLSMode.choices,
        default=TLSMode.UNKNOWN,
    )
    high_availability = models.BooleanField(null=True, blank=True)
    replica_count = models.PositiveSmallIntegerField(null=True, blank=True)
    backup_enabled = models.BooleanField(null=True, blank=True)
    maintenance_window = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]
        indexes = [
            models.Index(fields=["engine", "hosting_type"], name="infra_db_engine_host_idx"),
            models.Index(fields=["provider_account", "region"], name="infra_db_provider_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.DATABASE_INSTANCE,
                "Database instance",
            )
        server = self.server
        provider_account = self.provider_account
        if server is not None and self.resource_id:
            _validate_resource_boundary(self.resource, server.resource, "server")
        if provider_account is not None and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                provider_account.resource,
                "provider_account",
            )
        if self.hosting_type == self.HostingType.MANAGED and server is not None:
            raise ValidationError(
                {"server": "Managed database services cannot also reference a self-hosting Server."}
            )

    def __str__(self) -> str:
        return self.resource.name


class LogicalDatabase(models.Model):
    """Named logical database hosted by a DatabaseInstance."""

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="logical_database",
    )
    instance = models.ForeignKey(
        DatabaseInstance,
        on_delete=models.CASCADE,
        related_name="logical_databases",
    )
    database_name = models.CharField(max_length=200)
    purpose = models.CharField(max_length=255, blank=True)
    default_schema = models.CharField(max_length=100, blank=True)
    charset = models.CharField(max_length=100, blank=True)
    collation = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["instance__resource__name", "database_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "database_name"],
                name="unique_logical_database_on_instance",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.LOGICAL_DATABASE,
                "Logical database",
            )
        if self.resource_id and self.instance_id:
            _validate_parent_boundary(
                self.resource,
                self.instance.resource,
                "instance",
            )

    def __str__(self) -> str:
        return f"{self.instance.resource.name}/{self.database_name}"


class ApplicationProfile(models.Model):
    """Modern logical application attached to a structured Application resource."""

    class ApplicationType(models.TextChoices):
        WEB_APP = "web_app", "Web application"
        SAAS = "saas", "SaaS"
        API = "api", "API"
        SERVICE = "service", "Service"
        WORKER = "worker", "Worker"
        BOT = "bot", "Bot"
        MOBILE = "mobile", "Mobile app"
        HYBRID = "hybrid", "Hybrid"
        INTEGRATION = "integration", "Integration"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="application_profile",
    )
    application_type = models.CharField(
        max_length=30,
        choices=ApplicationType.choices,
        default=ApplicationType.WEB_APP,
    )
    owner_team = models.CharField(max_length=200, blank=True)
    primary_language = models.CharField(max_length=100, blank=True)
    framework = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.APPLICATION,
                "Application",
            )

    def __str__(self) -> str:
        return self.resource.name


class ApplicationEnvironment(models.Model):
    """Deployable environment belonging to one logical Application."""

    class DeploymentType(models.TextChoices):
        SERVER = "server", "Server"
        PAAS = "paas", "PaaS"
        CONTAINER = "container", "Container"
        KUBERNETES = "kubernetes", "Kubernetes"
        SERVERLESS = "serverless", "Serverless"
        STATIC = "static", "Static"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="application_environment",
    )
    application = models.ForeignKey(
        ApplicationProfile,
        on_delete=models.CASCADE,
        related_name="environments",
    )
    deployment_type = models.CharField(
        max_length=30,
        choices=DeploymentType.choices,
        default=DeploymentType.SERVER,
    )
    server = models.ForeignKey(
        ServerProfile,
        on_delete=models.SET_NULL,
        related_name="application_environments",
        null=True,
        blank=True,
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="application_environments",
        null=True,
        blank=True,
    )
    provider_resource_id = models.CharField(max_length=200, blank=True)
    runtime = models.CharField(max_length=100, blank=True)
    runtime_version = models.CharField(max_length=100, blank=True)
    release_version = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    branch_or_ref = models.CharField(max_length=200, blank=True)
    automatic_deployments = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "application__resource__name",
            "resource__environment",
            "resource__name",
            "id",
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.APPLICATION_ENVIRONMENT,
                "Application environment",
            )
        if self.resource_id and self.application_id:
            _validate_parent_boundary(
                self.resource,
                self.application.resource,
                "application",
            )
        server = self.server
        provider_account = self.provider_account
        if server is not None and self.resource_id:
            _validate_resource_boundary(self.resource, server.resource, "server")
        if provider_account is not None and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                provider_account.resource,
                "provider_account",
            )

    def __str__(self) -> str:
        return self.resource.name


class SourceRepository(models.Model):
    """Source-control repository attached to a structured repository resource."""

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        INTERNAL = "internal", "Internal"
        PUBLIC = "public", "Public"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="source_repository",
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="source_repositories",
        null=True,
        blank=True,
    )
    web_url = models.URLField(blank=True)
    clone_url = models.CharField(max_length=500, blank=True)
    provider_repository_id = models.CharField(max_length=200, blank=True)
    owner_name = models.CharField(max_length=200, blank=True)
    repository_name = models.CharField(max_length=200)
    default_branch = models.CharField(max_length=200, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    is_fork = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["owner_name", "repository_name", "id"]
        indexes = [
            models.Index(
                fields=["provider_account", "owner_name", "repository_name"],
                name="infra_repo_provider_idx",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _validate_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.SOURCE_REPOSITORY,
                "Source repository",
            )
        provider_account = self.provider_account
        if provider_account is not None and self.resource_id:
            _validate_resource_boundary(
                self.resource,
                provider_account.resource,
                "provider_account",
            )

    def __str__(self) -> str:
        return self.resource.name


class ApplicationRepositoryLink(models.Model):
    """Explicit source-repository role/context for an Application."""

    class Role(models.TextChoices):
        PRIMARY = "primary", "Primary"
        BACKEND = "backend", "Backend"
        FRONTEND = "frontend", "Frontend"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"
        MOBILE = "mobile", "Mobile"
        DOCUMENTATION = "documentation", "Documentation"
        OTHER = "other", "Other"

    application = models.ForeignKey(
        ApplicationProfile,
        on_delete=models.CASCADE,
        related_name="repository_links",
    )
    repository = models.ForeignKey(
        SourceRepository,
        on_delete=models.CASCADE,
        related_name="application_links",
    )
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.PRIMARY)
    path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional monorepo path or component directory.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "application__resource__name",
            "role",
            "repository__resource__name",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "repository", "role", "path"],
                name="unique_application_repository_role_path",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if not self.application_id or not self.repository_id:
            return
        application_resource = self.application.resource
        repository_resource = self.repository.resource
        _validate_resource_boundary(application_resource, repository_resource, "repository")
        if (
            application_resource.ownership_type == OwnershipType.INTERNAL
            and repository_resource.ownership_type == OwnershipType.CLIENT
        ):
            raise ValidationError(
                {
                    "repository": (
                        "Internal Applications cannot depend on Client-owned source repositories."
                    )
                }
            )

    def __str__(self) -> str:
        return f"{self.application.resource.name} -> {self.repository.resource.name} ({self.role})"

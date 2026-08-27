from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from .resource_models import InfrastructureResource, ProviderAccount


def _require_resource_type(
    resource: InfrastructureResource,
    expected_type: str,
    label: str,
) -> None:
    if resource.resource_type != expected_type:
        raise ValidationError(
            {"resource": f"{label} requires an InfrastructureResource of type '{expected_type}'."}
        )


def _require_same_scope(
    source: InfrastructureResource,
    target: InfrastructureResource,
    field_name: str,
) -> None:
    if source.ownership_type != target.ownership_type or source.client_id != target.client_id:
        raise ValidationError(
            {field_name: "Related operational resources must use the same ownership scope."}
        )


def _validate_provider_scope(
    resource: InfrastructureResource,
    provider_account: ProviderAccount | None,
) -> None:
    if provider_account is not None:
        _require_same_scope(resource, provider_account.resource, "provider_account")


class StorageProfile(models.Model):
    """Operational storage attached to a structured storage resource."""

    class StorageType(models.TextChoices):
        BLOCK = "block", "Block storage"
        OBJECT = "object", "Object storage"
        FILE = "file", "File storage"
        VOLUME = "volume", "Volume"
        DISK = "disk", "Disk"
        BUCKET = "bucket", "Bucket"
        NAS = "nas", "NAS"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="storage_profile",
    )
    storage_type = models.CharField(max_length=30, choices=StorageType.choices)
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="storage_profiles",
        null=True,
        blank=True,
    )
    provider_resource_id = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=100, blank=True)
    capacity_gb = models.PositiveBigIntegerField(null=True, blank=True)
    filesystem = models.CharField(max_length=100, blank=True)
    storage_class = models.CharField(max_length=100, blank=True)
    mount_path = models.CharField(max_length=500, blank=True)
    endpoint_url = models.URLField(blank=True)
    encrypted = models.BooleanField(null=True, blank=True)
    retention_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _require_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.STORAGE,
                "Storage",
            )
            _validate_provider_scope(self.resource, self.provider_account)

    def __str__(self) -> str:
        return self.resource.name


class BackupPlanProfile(models.Model):
    """Backup policy, destination and recent recovery-health metadata."""

    class BackupType(models.TextChoices):
        SNAPSHOT = "snapshot", "Snapshot"
        FILE = "file", "File backup"
        DATABASE = "database", "Database backup"
        IMAGE = "image", "Image"
        VOLUME = "volume", "Volume backup"
        OBJECT = "object", "Object backup"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="backup_plan_profile",
    )
    backup_type = models.CharField(max_length=30, choices=BackupType.choices)
    schedule = models.CharField(max_length=200, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    retention_days = models.PositiveIntegerField(null=True, blank=True)
    retention_copies = models.PositiveIntegerField(null=True, blank=True)
    destination_storage = models.ForeignKey(
        StorageProfile,
        on_delete=models.SET_NULL,
        related_name="backup_plans",
        null=True,
        blank=True,
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="backup_plans",
        null=True,
        blank=True,
    )
    encrypted = models.BooleanField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_restore_test_at = models.DateTimeField(null=True, blank=True)
    recovery_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if not self.resource_id:
            return
        _require_resource_type(
            self.resource,
            InfrastructureResource.ResourceType.BACKUP_PLAN,
            "Backup plan",
        )
        _validate_provider_scope(self.resource, self.provider_account)
        destination_storage = self.destination_storage
        if destination_storage is not None:
            _require_same_scope(
                self.resource,
                destination_storage.resource,
                "destination_storage",
            )

    def __str__(self) -> str:
        return self.resource.name


class BackupSource(models.Model):
    """One resource protected by a backup plan."""

    backup_plan = models.ForeignKey(
        BackupPlanProfile,
        on_delete=models.CASCADE,
        related_name="sources",
    )
    source_resource = models.ForeignKey(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="backup_sources",
    )
    scope = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["backup_plan__resource__name", "source_resource__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["backup_plan", "source_resource"],
                name="unique_backup_plan_source_resource",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.backup_plan_id and self.source_resource_id:
            _require_same_scope(
                self.backup_plan.resource,
                self.source_resource,
                "source_resource",
            )

    def __str__(self) -> str:
        return f"{self.backup_plan.resource.name}: {self.source_resource.name}"


class ContainerStackProfile(models.Model):
    """Docker/Compose/Swarm-style container stack attached to a resource."""

    class Orchestrator(models.TextChoices):
        DOCKER_COMPOSE = "docker_compose", "Docker Compose"
        DOCKER_SWARM = "docker_swarm", "Docker Swarm"
        NOMAD = "nomad", "Nomad"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="container_stack_profile",
    )
    orchestrator = models.CharField(max_length=30, choices=Orchestrator.choices)
    host_resource = models.ForeignKey(
        InfrastructureResource,
        on_delete=models.SET_NULL,
        related_name="hosted_container_stacks",
        null=True,
        blank=True,
    )
    project_name = models.CharField(max_length=200, blank=True)
    orchestrator_version = models.CharField(max_length=100, blank=True)
    compose_path = models.CharField(max_length=500, blank=True)
    working_directory = models.CharField(max_length=500, blank=True)
    management_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if not self.resource_id:
            return
        _require_resource_type(
            self.resource,
            InfrastructureResource.ResourceType.CONTAINER_STACK,
            "Container stack",
        )
        host_resource = self.host_resource
        if host_resource is not None:
            _require_resource_type(
                host_resource,
                InfrastructureResource.ResourceType.SERVER,
                "Container-stack host",
            )
            _require_same_scope(self.resource, host_resource, "host_resource")

    def __str__(self) -> str:
        return self.resource.name


class ContainerService(models.Model):
    """Non-secret service/runtime metadata inside one container stack."""

    stack = models.ForeignKey(
        ContainerStackProfile,
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(max_length=200)
    image = models.CharField(max_length=500, blank=True)
    replicas = models.PositiveIntegerField(null=True, blank=True)
    ports = models.JSONField(default=list, blank=True)
    volumes = models.JSONField(default=list, blank=True)
    healthcheck = models.CharField(max_length=500, blank=True)
    restart_policy = models.CharField(max_length=100, blank=True)
    environment_notes = models.TextField(
        blank=True,
        help_text="Describe environment/configuration shape only. Do not store secret values.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stack__resource__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["stack", "name"],
                name="unique_container_service_name_per_stack",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.ports, list):
            raise ValidationError({"ports": "Container service ports must be stored as a list."})
        if not isinstance(self.volumes, list):
            raise ValidationError(
                {"volumes": "Container service volumes must be stored as a list."}
            )

    def __str__(self) -> str:
        return f"{self.stack.resource.name}/{self.name}"


class KubernetesClusterProfile(models.Model):
    """Operational Kubernetes cluster metadata."""

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="kubernetes_cluster_profile",
    )
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.SET_NULL,
        related_name="kubernetes_clusters",
        null=True,
        blank=True,
    )
    distribution = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=100, blank=True)
    api_server_url = models.URLField(blank=True)
    management_url = models.URLField(blank=True)
    provider_cluster_id = models.CharField(max_length=200, blank=True)
    region = models.CharField(max_length=100, blank=True)
    node_count = models.PositiveIntegerField(null=True, blank=True)
    high_availability = models.BooleanField(null=True, blank=True)
    upgrade_channel = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _require_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.KUBERNETES_CLUSTER,
                "Kubernetes cluster",
            )
            _validate_provider_scope(self.resource, self.provider_account)

    def __str__(self) -> str:
        return self.resource.name


class KubernetesNamespaceProfile(models.Model):
    """Resource-backed Kubernetes namespace within a cluster."""

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="kubernetes_namespace_profile",
    )
    cluster = models.ForeignKey(
        KubernetesClusterProfile,
        on_delete=models.CASCADE,
        related_name="namespaces",
    )
    namespace = models.CharField(max_length=253)
    purpose = models.CharField(max_length=255, blank=True)
    resource_quota_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cluster__resource__name", "namespace", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cluster", "namespace"],
                name="unique_kubernetes_namespace_per_cluster",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _require_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE,
                "Kubernetes namespace",
            )
            _require_same_scope(self.resource, self.cluster.resource, "cluster")

    def __str__(self) -> str:
        return f"{self.cluster.resource.name}/{self.namespace}"


class KubernetesWorkloadProfile(models.Model):
    """Resource-backed Kubernetes workload."""

    class WorkloadKind(models.TextChoices):
        DEPLOYMENT = "deployment", "Deployment"
        STATEFUL_SET = "stateful_set", "StatefulSet"
        DAEMON_SET = "daemon_set", "DaemonSet"
        JOB = "job", "Job"
        CRON_JOB = "cron_job", "CronJob"
        REPLICA_SET = "replica_set", "ReplicaSet"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="kubernetes_workload_profile",
    )
    namespace = models.ForeignKey(
        KubernetesNamespaceProfile,
        on_delete=models.CASCADE,
        related_name="workloads",
    )
    workload_kind = models.CharField(max_length=30, choices=WorkloadKind.choices)
    workload_name = models.CharField(max_length=253)
    replicas_desired = models.PositiveIntegerField(null=True, blank=True)
    image_summary = models.TextField(blank=True)
    selector_summary = models.CharField(max_length=500, blank=True)
    service_account = models.CharField(max_length=253, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["namespace__cluster__resource__name", "workload_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "workload_kind", "workload_name"],
                name="unique_kubernetes_workload_per_namespace_kind",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _require_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD,
                "Kubernetes workload",
            )
            _require_same_scope(self.resource, self.namespace.resource, "namespace")

    def __str__(self) -> str:
        return f"{self.namespace}/{self.workload_name}"


class KubernetesService(models.Model):
    """Service object inside a namespace, optionally targeting a workload."""

    class ServiceType(models.TextChoices):
        CLUSTER_IP = "cluster_ip", "ClusterIP"
        NODE_PORT = "node_port", "NodePort"
        LOAD_BALANCER = "load_balancer", "LoadBalancer"
        EXTERNAL_NAME = "external_name", "ExternalName"
        HEADLESS = "headless", "Headless"
        OTHER = "other", "Other"

    namespace = models.ForeignKey(
        KubernetesNamespaceProfile,
        on_delete=models.CASCADE,
        related_name="services",
    )
    workload = models.ForeignKey(
        KubernetesWorkloadProfile,
        on_delete=models.SET_NULL,
        related_name="services",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=253)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    cluster_ip = models.GenericIPAddressField(null=True, blank=True)
    external_hostname = models.CharField(max_length=253, blank=True)
    ports = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["namespace__cluster__resource__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="unique_kubernetes_service_per_namespace",
            )
        ]

    def clean(self) -> None:
        super().clean()
        workload = self.workload
        if workload is not None and workload.namespace_id != self.namespace_id:
            raise ValidationError({"workload": "Workload must belong to the selected namespace."})
        if not isinstance(self.ports, list):
            raise ValidationError({"ports": "Kubernetes service ports must be stored as a list."})

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"


class KubernetesIngress(models.Model):
    """Ingress routing metadata inside a namespace."""

    namespace = models.ForeignKey(
        KubernetesNamespaceProfile,
        on_delete=models.CASCADE,
        related_name="ingresses",
    )
    name = models.CharField(max_length=253)
    ingress_class = models.CharField(max_length=100, blank=True)
    hosts = models.JSONField(default=list, blank=True)
    tls_enabled = models.BooleanField(default=False)
    target_service = models.ForeignKey(
        KubernetesService,
        on_delete=models.SET_NULL,
        related_name="ingresses",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["namespace__cluster__resource__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="unique_kubernetes_ingress_per_namespace",
            )
        ]

    def clean(self) -> None:
        super().clean()
        target_service = self.target_service
        if target_service is not None and target_service.namespace_id != self.namespace_id:
            raise ValidationError(
                {"target_service": "Ingress target service must belong to the selected namespace."}
            )
        if not isinstance(self.hosts, list):
            raise ValidationError({"hosts": "Ingress hosts must be stored as a list."})

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"


class HelmRelease(models.Model):
    """Non-secret Helm release metadata for a namespace."""

    namespace = models.ForeignKey(
        KubernetesNamespaceProfile,
        on_delete=models.CASCADE,
        related_name="helm_releases",
    )
    name = models.CharField(max_length=253)
    chart = models.CharField(max_length=253)
    chart_version = models.CharField(max_length=100, blank=True)
    app_version = models.CharField(max_length=100, blank=True)
    repository_url = models.URLField(blank=True)
    status = models.CharField(max_length=100, blank=True)
    values_summary = models.TextField(
        blank=True,
        help_text="Non-secret values summary only. Store credentials in the Credential Vault.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["namespace__cluster__resource__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="unique_helm_release_per_namespace",
            )
        ]

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"


class KubernetesPersistentStorage(models.Model):
    """PVC/PV-style operational storage metadata inside a namespace."""

    namespace = models.ForeignKey(
        KubernetesNamespaceProfile,
        on_delete=models.CASCADE,
        related_name="persistent_storage",
    )
    name = models.CharField(max_length=253)
    storage_class = models.CharField(max_length=100, blank=True)
    capacity_gb = models.PositiveBigIntegerField(null=True, blank=True)
    access_modes = models.JSONField(default=list, blank=True)
    volume_name = models.CharField(max_length=253, blank=True)
    backing_storage = models.ForeignKey(
        StorageProfile,
        on_delete=models.SET_NULL,
        related_name="kubernetes_volumes",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["namespace__cluster__resource__name", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["namespace", "name"],
                name="unique_kubernetes_storage_per_namespace",
            )
        ]

    def clean(self) -> None:
        super().clean()
        backing_storage = self.backing_storage
        if backing_storage is not None:
            _require_same_scope(
                self.namespace.resource,
                backing_storage.resource,
                "backing_storage",
            )
        if not isinstance(self.access_modes, list):
            raise ValidationError({"access_modes": "Access modes must be stored as a list."})

    def __str__(self) -> str:
        return f"{self.namespace}/{self.name}"


class SystemServiceProfile(models.Model):
    """System service/process manager configuration tracked as a resource."""

    class Manager(models.TextChoices):
        SYSTEMD = "systemd", "systemd"
        SUPERVISOR = "supervisor", "Supervisor"
        WINDOWS_SERVICE = "windows_service", "Windows Service"
        LAUNCHD = "launchd", "launchd"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="system_service_profile",
    )
    host_resource = models.ForeignKey(
        InfrastructureResource,
        on_delete=models.PROTECT,
        related_name="system_services",
    )
    manager = models.CharField(max_length=30, choices=Manager.choices)
    unit_name = models.CharField(max_length=253)
    display_name = models.CharField(max_length=253, blank=True)
    expected_state = models.CharField(max_length=100, blank=True)
    startup_type = models.CharField(max_length=100, blank=True)
    executable = models.CharField(max_length=500, blank=True)
    config_path = models.CharField(max_length=500, blank=True)
    working_directory = models.CharField(max_length=500, blank=True)
    log_location = models.CharField(max_length=500, blank=True)
    restart_policy = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["host_resource__name", "unit_name", "id"]

    def clean(self) -> None:
        super().clean()
        if self.resource_id:
            _require_resource_type(
                self.resource,
                InfrastructureResource.ResourceType.SYSTEM_SERVICE,
                "System service",
            )
            _require_resource_type(
                self.host_resource,
                InfrastructureResource.ResourceType.SERVER,
                "System-service host",
            )
            _require_same_scope(self.resource, self.host_resource, "host_resource")

    def __str__(self) -> str:
        return f"{self.host_resource.name}:{self.unit_name}"


class ScheduledJobProfile(models.Model):
    """Cron/timer/scheduler job metadata without embedded credentials."""

    class Scheduler(models.TextChoices):
        CRON = "cron", "cron"
        SYSTEMD_TIMER = "systemd_timer", "systemd timer"
        CELERY_BEAT = "celery_beat", "Celery Beat"
        KUBERNETES_CRON_JOB = "kubernetes_cron_job", "Kubernetes CronJob"
        WINDOWS_TASK = "windows_task", "Windows scheduled task"
        OTHER = "other", "Other"

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.CASCADE,
        related_name="scheduled_job_profile",
    )
    scheduler = models.CharField(max_length=40, choices=Scheduler.choices)
    host_resource = models.ForeignKey(
        InfrastructureResource,
        on_delete=models.SET_NULL,
        related_name="scheduled_jobs",
        null=True,
        blank=True,
    )
    schedule_expression = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    command_summary = models.TextField(
        blank=True,
        help_text="Non-secret command/job summary. Store credentials in the Credential Vault.",
    )
    config_path = models.CharField(max_length=500, blank=True)
    working_directory = models.CharField(max_length=500, blank=True)
    run_as = models.CharField(max_length=200, blank=True)
    enabled = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["resource__name", "id"]

    def clean(self) -> None:
        super().clean()
        if not self.resource_id:
            return
        _require_resource_type(
            self.resource,
            InfrastructureResource.ResourceType.SCHEDULED_JOB,
            "Scheduled job",
        )
        host_resource = self.host_resource
        if host_resource is not None:
            _require_same_scope(self.resource, host_resource, "host_resource")

    def __str__(self) -> str:
        return self.resource.name

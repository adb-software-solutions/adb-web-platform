from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.core.ownership import OwnershipType
from apps.infrastructure.models import (
    BackupPlanProfile,
    BackupSource,
    ContainerService,
    ContainerStackProfile,
    HelmRelease,
    InfrastructureResource,
    KubernetesClusterProfile,
    KubernetesIngress,
    KubernetesNamespaceProfile,
    KubernetesPersistentStorage,
    KubernetesService,
    KubernetesWorkloadProfile,
    ProviderAccount,
    ScheduledJobProfile,
    ServerProfile,
    StorageProfile,
    SystemServiceProfile,
)

DEMO_PREFIX = "[DEMO]"
OPERATIONAL_TYPES = [
    InfrastructureResource.ResourceType.STORAGE,
    InfrastructureResource.ResourceType.BACKUP_PLAN,
    InfrastructureResource.ResourceType.CONTAINER_STACK,
    InfrastructureResource.ResourceType.KUBERNETES_CLUSTER,
    InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE,
    InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD,
    InfrastructureResource.ResourceType.SYSTEM_SERVICE,
    InfrastructureResource.ResourceType.SCHEDULED_JOB,
]


class Command(BaseCommand):
    help = "Populate specialist technical operations with deterministic development data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--scale", type=int, default=1)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_specialist_operations_development is disabled when DEBUG=False. "
                "Use --force only in a disposable environment."
            )

        provider = (
            ProviderAccount.objects.select_related("resource", "provider")
            .filter(resource__name=f"{DEMO_PREFIX} ADB DigitalOcean")
            .first()
        )
        server = (
            ServerProfile.objects.select_related("resource")
            .filter(resource__name=f"{DEMO_PREFIX} ADB LON Web 01")
            .first()
        )
        if provider is None or server is None:
            raise CommandError(
                "Run seed_infrastructure_development first so the demo provider and server exist."
            )

        scale = max(1, options["scale"])
        with transaction.atomic():
            if options["reset"]:
                InfrastructureResource.objects.filter(
                    name__startswith=DEMO_PREFIX,
                    resource_type__in=OPERATIONAL_TYPES,
                ).delete()
            self._seed_internal(provider, server)
            self._seed_client_operations()
            self._seed_scaled_jobs(server, scale)

        self.stdout.write(
            self.style.SUCCESS(f"Specialist operations development data ready (scale={scale}).")
        )

    def _resource(
        self,
        *,
        name: str,
        resource_type: str,
        ownership_type: str = OwnershipType.INTERNAL,
        client_id: int | None = None,
        environment: str = InfrastructureResource.Environment.PRODUCTION,
        criticality: str = InfrastructureResource.Criticality.NORMAL,
        description: str = "",
    ) -> InfrastructureResource:
        resource, _ = InfrastructureResource.objects.update_or_create(
            name=name,
            resource_type=resource_type,
            defaults={
                "ownership_type": ownership_type,
                "client_id": client_id,
                "lifecycle_status": InfrastructureResource.LifecycleStatus.ACTIVE,
                "environment": environment,
                "criticality": criticality,
                "description": description,
            },
        )
        resource.full_clean()
        resource.save()
        return resource

    def _seed_internal(
        self,
        provider: ProviderAccount,
        server: ServerProfile,
    ) -> None:
        storage_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Backup Object Storage",
            resource_type=InfrastructureResource.ResourceType.STORAGE,
            environment=InfrastructureResource.Environment.SHARED,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Encrypted development backup destination for ADB platform workloads.",
        )
        storage, _ = StorageProfile.objects.update_or_create(
            resource=storage_resource,
            defaults={
                "storage_type": StorageProfile.StorageType.OBJECT,
                "provider_account": provider,
                "provider_resource_id": "demo-adb-backups",
                "region": "lon1",
                "capacity_gb": 500,
                "storage_class": "standard",
                "endpoint_url": "https://demo-adb-backups.lon1.example.test",
                "encrypted": True,
                "retention_notes": "Lifecycle-managed development backup storage.",
            },
        )
        storage.full_clean()
        storage.save()

        backup_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Nightly Platform Backup",
            resource_type=InfrastructureResource.ResourceType.BACKUP_PLAN,
            environment=InfrastructureResource.Environment.SHARED,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Nightly platform backup policy with recovery-test metadata.",
        )
        backup, _ = BackupPlanProfile.objects.update_or_create(
            resource=backup_resource,
            defaults={
                "backup_type": BackupPlanProfile.BackupType.SNAPSHOT,
                "schedule": "0 2 * * *",
                "timezone": "Europe/London",
                "retention_days": 30,
                "retention_copies": 14,
                "destination_storage": storage,
                "provider_account": provider,
                "encrypted": True,
                "recovery_notes": "Restore into an isolated development environment before validation.",
            },
        )
        backup.full_clean()
        backup.save()
        backup.sources.exclude(source_resource=server.resource).delete()
        source, _ = BackupSource.objects.update_or_create(
            backup_plan=backup,
            source_resource=server.resource,
            defaults={
                "scope": "/srv/adb-platform and persistent application data",
                "notes": "Configuration shape only; credentials remain in Credential Vault.",
            },
        )
        source.full_clean()
        source.save()

        stack_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform Compose",
            resource_type=InfrastructureResource.ResourceType.CONTAINER_STACK,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Docker Compose representation of the ADB platform runtime.",
        )
        stack, _ = ContainerStackProfile.objects.update_or_create(
            resource=stack_resource,
            defaults={
                "orchestrator": ContainerStackProfile.Orchestrator.DOCKER_COMPOSE,
                "host_resource": server.resource,
                "project_name": "adb-platform",
                "orchestrator_version": "Docker Compose v2",
                "compose_path": "/srv/adb-platform/compose.yml",
                "working_directory": "/srv/adb-platform",
                "management_url": "https://containers.example.test",
                "notes": "Development topology only; environment secrets are held in Credential Vault.",
            },
        )
        stack.full_clean()
        stack.save()
        services = [
            (
                "backend",
                "ghcr.io/adb-software-solutions/adb-backend:development",
                ["8000:8000"],
                ["media:/app/media"],
                "Django API and Celery application configuration; no secret values.",
            ),
            (
                "frontend",
                "ghcr.io/adb-software-solutions/adb-software-solutions:development",
                ["3000:3000"],
                [],
                "Next.js application configuration; no secret values.",
            ),
            (
                "redis",
                "redis:8-alpine",
                ["6379"],
                ["redis-data:/data"],
                "Internal cache/queue service; authentication material is not recorded here.",
            ),
        ]
        for name, image, ports, volumes, environment_notes in services:
            service, _ = ContainerService.objects.update_or_create(
                stack=stack,
                name=name,
                defaults={
                    "image": image,
                    "replicas": 1,
                    "ports": ports,
                    "volumes": volumes,
                    "healthcheck": "Application health endpoint / native container healthcheck",
                    "restart_policy": "unless-stopped",
                    "environment_notes": environment_notes,
                },
            )
            service.full_clean()
            service.save()

        cluster_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB LON Kubernetes",
            resource_type=InfrastructureResource.ResourceType.KUBERNETES_CLUSTER,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Development Kubernetes cluster demonstrating operational topology.",
        )
        cluster, _ = KubernetesClusterProfile.objects.update_or_create(
            resource=cluster_resource,
            defaults={
                "provider_account": provider,
                "distribution": "DigitalOcean Kubernetes",
                "version": "1.34",
                "api_server_url": "https://demo-k8s-api.example.test",
                "management_url": "https://cloud.digitalocean.com/kubernetes/clusters/demo-adb",
                "provider_cluster_id": "demo-adb-lon-k8s01",
                "region": "lon1",
                "node_count": 3,
                "high_availability": True,
                "upgrade_channel": "stable",
                "notes": "Demo cluster metadata; kubeconfig and tokens remain in Credential Vault.",
            },
        )
        cluster.full_clean()
        cluster.save()

        namespace_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform Namespace",
            resource_type=InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Primary application namespace in the development Kubernetes topology.",
        )
        namespace, _ = KubernetesNamespaceProfile.objects.update_or_create(
            resource=namespace_resource,
            defaults={
                "cluster": cluster,
                "namespace": "adb-platform",
                "purpose": "ADB platform application workloads",
                "resource_quota_summary": "CPU 4 cores; memory 8 GiB; storage 100 GiB",
            },
        )
        namespace.full_clean()
        namespace.save()

        workload_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform API Workload",
            resource_type=InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Django API workload inside the ADB platform namespace.",
        )
        workload, _ = KubernetesWorkloadProfile.objects.update_or_create(
            resource=workload_resource,
            defaults={
                "namespace": namespace,
                "workload_kind": KubernetesWorkloadProfile.WorkloadKind.DEPLOYMENT,
                "workload_name": "adb-api",
                "replicas_desired": 2,
                "image_summary": "ghcr.io/adb-software-solutions/adb-backend:development",
                "selector_summary": "app=adb-api",
                "service_account": "adb-api",
                "notes": "Non-secret workload topology; runtime secrets are external to this record.",
            },
        )
        workload.full_clean()
        workload.save()

        kube_service, _ = KubernetesService.objects.update_or_create(
            namespace=namespace,
            name="adb-api",
            defaults={
                "workload": workload,
                "service_type": KubernetesService.ServiceType.CLUSTER_IP,
                "cluster_ip": "10.96.42.10",
                "ports": ["80/TCP -> 8000"],
            },
        )
        kube_service.full_clean()
        kube_service.save()

        ingress, _ = KubernetesIngress.objects.update_or_create(
            namespace=namespace,
            name="adb-platform",
            defaults={
                "ingress_class": "nginx",
                "hosts": ["platform.demo.example.test"],
                "tls_enabled": True,
                "target_service": kube_service,
                "notes": "TLS termination and routing metadata for development only.",
            },
        )
        ingress.full_clean()
        ingress.save()

        release, _ = HelmRelease.objects.update_or_create(
            namespace=namespace,
            name="ingress-nginx",
            defaults={
                "chart": "ingress-nginx/ingress-nginx",
                "chart_version": "4.x",
                "app_version": "1.x",
                "repository_url": "https://kubernetes.github.io/ingress-nginx",
                "status": "deployed",
                "values_summary": "2 controller replicas; LoadBalancer service; no secret values recorded.",
            },
        )
        release.full_clean()
        release.save()

        persistent, _ = KubernetesPersistentStorage.objects.update_or_create(
            namespace=namespace,
            name="platform-data",
            defaults={
                "storage_class": "do-block-storage",
                "capacity_gb": 100,
                "access_modes": ["ReadWriteOnce"],
                "volume_name": "pvc-platform-data",
                "backing_storage": storage,
                "notes": "Development persistent-storage relationship to the structured storage record.",
            },
        )
        persistent.full_clean()
        persistent.save()

        service_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Caddy Service",
            resource_type=InfrastructureResource.ResourceType.SYSTEM_SERVICE,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Reverse-proxy service record on the development web server.",
        )
        system_service, _ = SystemServiceProfile.objects.update_or_create(
            resource=service_resource,
            defaults={
                "host_resource": server.resource,
                "manager": SystemServiceProfile.Manager.SYSTEMD,
                "unit_name": "caddy.service",
                "display_name": "Caddy",
                "expected_state": "active",
                "startup_type": "enabled",
                "executable": "/usr/bin/caddy",
                "config_path": "/etc/caddy/Caddyfile",
                "working_directory": "/var/lib/caddy",
                "log_location": "journald",
                "restart_policy": "on-failure",
                "notes": "TLS/DNS provider credentials are linked through Credential Vault, not stored here.",
            },
        )
        system_service.full_clean()
        system_service.save()

        job_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Backup Verification Timer",
            resource_type=InfrastructureResource.ResourceType.SCHEDULED_JOB,
            environment=InfrastructureResource.Environment.SHARED,
            description="Scheduled verification job for recent backup metadata.",
        )
        job, _ = ScheduledJobProfile.objects.update_or_create(
            resource=job_resource,
            defaults={
                "scheduler": ScheduledJobProfile.Scheduler.SYSTEMD_TIMER,
                "host_resource": server.resource,
                "schedule_expression": "daily at 04:30",
                "timezone": "Europe/London",
                "command_summary": "Verify latest backup exists and record health result; no credentials embedded.",
                "config_path": "/etc/systemd/system/adb-backup-verify.timer",
                "working_directory": "/srv/adb-platform",
                "run_as": "adb-platform",
                "enabled": True,
                "notes": "Execution credentials remain in the service environment/Vault boundary.",
            },
        )
        job.full_clean()
        job.save()

    def _seed_client_operations(self) -> None:
        client_server = (
            ServerProfile.objects.select_related("resource", "resource__client")
            .filter(
                resource__name__startswith=DEMO_PREFIX,
                resource__ownership_type=OwnershipType.CLIENT,
            )
            .order_by("resource_id")
            .first()
        )
        if client_server is None or client_server.resource.client_id is None:
            return

        client = client_server.resource.client
        client_name = client.company or client.name if client else "Client"
        stack_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Web Compose",
            resource_type=InfrastructureResource.ResourceType.CONTAINER_STACK,
            ownership_type=OwnershipType.CLIENT,
            client_id=client_server.resource.client_id,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned container stack demonstrating strict operational scoping.",
        )
        stack, _ = ContainerStackProfile.objects.update_or_create(
            resource=stack_resource,
            defaults={
                "orchestrator": ContainerStackProfile.Orchestrator.DOCKER_COMPOSE,
                "host_resource": client_server.resource,
                "project_name": "client-web",
                "compose_path": "/srv/client-web/compose.yml",
                "working_directory": "/srv/client-web",
                "notes": "Client configuration shape only; secrets remain in Credential Vault.",
            },
        )
        stack.full_clean()
        stack.save()
        service, _ = ContainerService.objects.update_or_create(
            stack=stack,
            name="web",
            defaults={
                "image": "wordpress:latest",
                "replicas": 1,
                "ports": ["8080:80"],
                "volumes": ["uploads:/var/www/html/wp-content/uploads"],
                "restart_policy": "unless-stopped",
                "environment_notes": "Database and application settings exist, but secret values are not recorded.",
            },
        )
        service.full_clean()
        service.save()

    def _seed_scaled_jobs(self, server: ServerProfile, scale: int) -> None:
        for index in range(2, scale + 1):
            resource = self._resource(
                name=f"{DEMO_PREFIX} ADB Maintenance Job {index:02d}",
                resource_type=InfrastructureResource.ResourceType.SCHEDULED_JOB,
                environment=InfrastructureResource.Environment.SHARED,
                description="Scaled deterministic scheduled-job sample.",
            )
            job, _ = ScheduledJobProfile.objects.update_or_create(
                resource=resource,
                defaults={
                    "scheduler": ScheduledJobProfile.Scheduler.CRON,
                    "host_resource": server.resource,
                    "schedule_expression": f"{index % 60} 3 * * *",
                    "timezone": "Europe/London",
                    "command_summary": "Run routine platform housekeeping without embedding credentials.",
                    "working_directory": "/srv/adb-platform",
                    "run_as": "adb-platform",
                    "enabled": True,
                    "notes": "Generated development record.",
                },
            )
            job.full_clean()
            job.save()

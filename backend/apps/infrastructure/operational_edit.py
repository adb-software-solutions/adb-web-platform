from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

from .models import (
    BackupPlanProfile,
    ContainerStackProfile,
    InfrastructureResource,
    KubernetesClusterProfile,
    KubernetesNamespaceProfile,
    KubernetesWorkloadProfile,
    ScheduledJobProfile,
    StorageProfile,
    SystemServiceProfile,
)

OperationalEditValue: TypeAlias = str | int | bool | list[str] | list[int] | None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def operational_edit_values(
    resource: InfrastructureResource,
) -> dict[str, OperationalEditValue] | None:
    if resource.resource_type == InfrastructureResource.ResourceType.STORAGE:
        storage = StorageProfile.objects.filter(resource=resource).first()
        if storage is None:
            return None
        provider = storage.provider_account if storage.provider_account_id else None
        return {
            "storage_type": storage.storage_type,
            "provider_account_resource_id": provider.resource_id if provider else None,
            "provider_resource_id": storage.provider_resource_id,
            "region": storage.region,
            "capacity_gb": storage.capacity_gb,
            "filesystem": storage.filesystem,
            "storage_class": storage.storage_class,
            "mount_path": storage.mount_path,
            "endpoint_url": storage.endpoint_url,
            "encrypted": storage.encrypted,
            "retention_notes": storage.retention_notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.BACKUP_PLAN:
        backup = BackupPlanProfile.objects.filter(resource=resource).first()
        if backup is None:
            return None
        provider = backup.provider_account if backup.provider_account_id else None
        destination = backup.destination_storage if backup.destination_storage_id else None
        return {
            "backup_type": backup.backup_type,
            "schedule": backup.schedule,
            "timezone": backup.timezone,
            "retention_days": backup.retention_days,
            "retention_copies": backup.retention_copies,
            "destination_storage_resource_id": destination.resource_id if destination else None,
            "provider_account_resource_id": provider.resource_id if provider else None,
            "encrypted": backup.encrypted,
            "last_success_at": _iso(backup.last_success_at),
            "last_failure_at": _iso(backup.last_failure_at),
            "last_restore_test_at": _iso(backup.last_restore_test_at),
            "source_resource_ids": [source.source_resource_id for source in backup.sources.all()],
            "recovery_notes": backup.recovery_notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.CONTAINER_STACK:
        stack = ContainerStackProfile.objects.filter(resource=resource).first()
        if stack is None:
            return None
        return {
            "orchestrator": stack.orchestrator,
            "host_resource_id": stack.host_resource_id,
            "project_name": stack.project_name,
            "orchestrator_version": stack.orchestrator_version,
            "compose_path": stack.compose_path,
            "working_directory": stack.working_directory,
            "management_url": stack.management_url,
            "notes": stack.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_CLUSTER:
        cluster = KubernetesClusterProfile.objects.filter(resource=resource).first()
        if cluster is None:
            return None
        provider = cluster.provider_account if cluster.provider_account_id else None
        return {
            "provider_account_resource_id": provider.resource_id if provider else None,
            "distribution": cluster.distribution,
            "version": cluster.version,
            "api_server_url": cluster.api_server_url,
            "management_url": cluster.management_url,
            "provider_cluster_id": cluster.provider_cluster_id,
            "region": cluster.region,
            "node_count": cluster.node_count,
            "high_availability": cluster.high_availability,
            "upgrade_channel": cluster.upgrade_channel,
            "notes": cluster.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE:
        namespace = KubernetesNamespaceProfile.objects.filter(resource=resource).first()
        if namespace is None:
            return None
        return {
            "cluster_resource_id": namespace.cluster.resource_id,
            "namespace": namespace.namespace,
            "purpose": namespace.purpose,
            "resource_quota_summary": namespace.resource_quota_summary,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD:
        workload = KubernetesWorkloadProfile.objects.filter(resource=resource).first()
        if workload is None:
            return None
        return {
            "namespace_resource_id": workload.namespace.resource_id,
            "workload_kind": workload.workload_kind,
            "workload_name": workload.workload_name,
            "replicas_desired": workload.replicas_desired,
            "image_summary": workload.image_summary,
            "selector_summary": workload.selector_summary,
            "service_account": workload.service_account,
            "notes": workload.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.SYSTEM_SERVICE:
        service = SystemServiceProfile.objects.filter(resource=resource).first()
        if service is None:
            return None
        return {
            "host_resource_id": service.host_resource_id,
            "manager": service.manager,
            "unit_name": service.unit_name,
            "display_name": service.display_name,
            "expected_state": service.expected_state,
            "startup_type": service.startup_type,
            "executable": service.executable,
            "config_path": service.config_path,
            "working_directory": service.working_directory,
            "log_location": service.log_location,
            "restart_policy": service.restart_policy,
            "notes": service.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.SCHEDULED_JOB:
        job = ScheduledJobProfile.objects.filter(resource=resource).first()
        if job is None:
            return None
        return {
            "scheduler": job.scheduler,
            "host_resource_id": job.host_resource_id,
            "schedule_expression": job.schedule_expression,
            "timezone": job.timezone,
            "command_summary": job.command_summary,
            "config_path": job.config_path,
            "working_directory": job.working_directory,
            "run_as": job.run_as,
            "enabled": job.enabled,
            "last_success_at": _iso(job.last_success_at),
            "last_failure_at": _iso(job.last_failure_at),
            "next_run_at": _iso(job.next_run_at),
            "notes": job.notes,
        }

    return None

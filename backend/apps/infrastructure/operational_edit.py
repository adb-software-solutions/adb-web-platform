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

OperationalEditValue: TypeAlias = str | int | bool | list[str] | None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def operational_edit_values(
    resource: InfrastructureResource,
) -> dict[str, OperationalEditValue] | None:
    if resource.resource_type == InfrastructureResource.ResourceType.STORAGE:
        profile = StorageProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        provider = profile.provider_account if profile.provider_account_id else None
        return {
            "storage_type": profile.storage_type,
            "provider_account_resource_id": provider.resource_id if provider else None,
            "provider_resource_id": profile.provider_resource_id,
            "region": profile.region,
            "capacity_gb": profile.capacity_gb,
            "filesystem": profile.filesystem,
            "storage_class": profile.storage_class,
            "mount_path": profile.mount_path,
            "endpoint_url": profile.endpoint_url,
            "encrypted": profile.encrypted,
            "retention_notes": profile.retention_notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.BACKUP_PLAN:
        profile = BackupPlanProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        provider = profile.provider_account if profile.provider_account_id else None
        destination = profile.destination_storage if profile.destination_storage_id else None
        return {
            "backup_type": profile.backup_type,
            "schedule": profile.schedule,
            "timezone": profile.timezone,
            "retention_days": profile.retention_days,
            "retention_copies": profile.retention_copies,
            "destination_storage_resource_id": destination.resource_id if destination else None,
            "provider_account_resource_id": provider.resource_id if provider else None,
            "encrypted": profile.encrypted,
            "last_success_at": _iso(profile.last_success_at),
            "last_failure_at": _iso(profile.last_failure_at),
            "last_restore_test_at": _iso(profile.last_restore_test_at),
            "source_resource_ids": [source.source_resource_id for source in profile.sources.all()],
            "recovery_notes": profile.recovery_notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.CONTAINER_STACK:
        profile = ContainerStackProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        return {
            "orchestrator": profile.orchestrator,
            "host_resource_id": profile.host_resource_id,
            "project_name": profile.project_name,
            "orchestrator_version": profile.orchestrator_version,
            "compose_path": profile.compose_path,
            "working_directory": profile.working_directory,
            "management_url": profile.management_url,
            "notes": profile.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_CLUSTER:
        profile = KubernetesClusterProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        provider = profile.provider_account if profile.provider_account_id else None
        return {
            "provider_account_resource_id": provider.resource_id if provider else None,
            "distribution": profile.distribution,
            "version": profile.version,
            "api_server_url": profile.api_server_url,
            "management_url": profile.management_url,
            "provider_cluster_id": profile.provider_cluster_id,
            "region": profile.region,
            "node_count": profile.node_count,
            "high_availability": profile.high_availability,
            "upgrade_channel": profile.upgrade_channel,
            "notes": profile.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE:
        profile = KubernetesNamespaceProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        return {
            "cluster_resource_id": profile.cluster.resource_id,
            "namespace": profile.namespace,
            "purpose": profile.purpose,
            "resource_quota_summary": profile.resource_quota_summary,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD:
        profile = KubernetesWorkloadProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        return {
            "namespace_resource_id": profile.namespace.resource_id,
            "workload_kind": profile.workload_kind,
            "workload_name": profile.workload_name,
            "replicas_desired": profile.replicas_desired,
            "image_summary": profile.image_summary,
            "selector_summary": profile.selector_summary,
            "service_account": profile.service_account,
            "notes": profile.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.SYSTEM_SERVICE:
        profile = SystemServiceProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        return {
            "host_resource_id": profile.host_resource_id,
            "manager": profile.manager,
            "unit_name": profile.unit_name,
            "display_name": profile.display_name,
            "expected_state": profile.expected_state,
            "startup_type": profile.startup_type,
            "executable": profile.executable,
            "config_path": profile.config_path,
            "working_directory": profile.working_directory,
            "log_location": profile.log_location,
            "restart_policy": profile.restart_policy,
            "notes": profile.notes,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.SCHEDULED_JOB:
        profile = ScheduledJobProfile.objects.filter(resource=resource).first()
        if profile is None:
            return None
        return {
            "scheduler": profile.scheduler,
            "host_resource_id": profile.host_resource_id,
            "schedule_expression": profile.schedule_expression,
            "timezone": profile.timezone,
            "command_summary": profile.command_summary,
            "config_path": profile.config_path,
            "working_directory": profile.working_directory,
            "run_as": profile.run_as,
            "enabled": profile.enabled,
            "last_success_at": _iso(profile.last_success_at),
            "last_failure_at": _iso(profile.last_failure_at),
            "next_run_at": _iso(profile.next_run_at),
            "notes": profile.notes,
        }

    return None

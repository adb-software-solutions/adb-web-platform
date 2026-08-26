from __future__ import annotations

from typing import TypeAlias

from .models import (
    ApplicationEnvironment,
    ApplicationProfile,
    DatabaseInstance,
    InfrastructureResource,
    LogicalDatabase,
    SourceRepository,
)

DataApplicationEditValue: TypeAlias = str | int | bool | list[str] | None


def data_application_edit_values(
    resource: InfrastructureResource,
) -> dict[str, DataApplicationEditValue] | None:
    """Return exact safe values for the native data/application editor."""

    if resource.resource_type == InfrastructureResource.ResourceType.DATABASE_INSTANCE:
        database = DatabaseInstance.objects.filter(resource=resource).first()
        if database is None:
            return None
        server = database.server if database.server_id else None
        provider_account = database.provider_account if database.provider_account_id else None
        return {
            "engine": database.engine,
            "engine_version": database.engine_version,
            "hosting_type": database.hosting_type,
            "server_resource_id": server.resource_id if server else None,
            "provider_account_resource_id": (
                provider_account.resource_id if provider_account else None
            ),
            "provider_resource_id": database.provider_resource_id,
            "endpoint": database.endpoint,
            "port": database.port,
            "region": database.region,
            "zone": database.zone,
            "tls_mode": database.tls_mode,
            "high_availability": database.high_availability,
            "replica_count": database.replica_count,
            "backup_enabled": database.backup_enabled,
            "maintenance_window": database.maintenance_window,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.LOGICAL_DATABASE:
        database = LogicalDatabase.objects.select_related("instance").filter(resource=resource).first()
        if database is None:
            return None
        return {
            "instance_resource_id": database.instance.resource_id,
            "database_name": database.database_name,
            "purpose": database.purpose,
            "default_schema": database.default_schema,
            "charset": database.charset,
            "collation": database.collation,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.APPLICATION:
        application = ApplicationProfile.objects.filter(resource=resource).first()
        if application is None:
            return None
        return {
            "application_type": application.application_type,
            "owner_team": application.owner_team,
            "primary_language": application.primary_language,
            "framework": application.framework,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.APPLICATION_ENVIRONMENT:
        environment = ApplicationEnvironment.objects.filter(resource=resource).first()
        if environment is None:
            return None
        server = environment.server if environment.server_id else None
        provider_account = (
            environment.provider_account if environment.provider_account_id else None
        )
        return {
            "application_resource_id": environment.application.resource_id,
            "deployment_type": environment.deployment_type,
            "server_resource_id": server.resource_id if server else None,
            "provider_account_resource_id": (
                provider_account.resource_id if provider_account else None
            ),
            "provider_resource_id": environment.provider_resource_id,
            "runtime": environment.runtime,
            "runtime_version": environment.runtime_version,
            "release_version": environment.release_version,
            "region": environment.region,
            "branch_or_ref": environment.branch_or_ref,
            "automatic_deployments": environment.automatic_deployments,
        }

    if resource.resource_type == InfrastructureResource.ResourceType.SOURCE_REPOSITORY:
        repository = SourceRepository.objects.filter(resource=resource).first()
        if repository is None:
            return None
        provider_account = repository.provider_account if repository.provider_account_id else None
        return {
            "provider_account_resource_id": (
                provider_account.resource_id if provider_account else None
            ),
            "web_url": repository.web_url,
            "clone_url": repository.clone_url,
            "provider_repository_id": repository.provider_repository_id,
            "owner_name": repository.owner_name,
            "repository_name": repository.repository_name,
            "default_branch": repository.default_branch,
            "visibility": repository.visibility,
            "is_fork": repository.is_fork,
        }

    return None

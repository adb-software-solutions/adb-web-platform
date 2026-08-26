from __future__ import annotations

from typing import Any

from .models import (
    Application,
    ApplicationProfile,
    Database,
    DatabaseInstance,
    InfrastructureResource,
    IPAddress,
    Server,
    ServerProfile,
)

_SERVER_OS_MAP: dict[str, tuple[str, str, str]] = {
    "ubuntu_20": (ServerProfile.OSFamily.LINUX, "Ubuntu", "20.04"),
    "ubuntu_22": (ServerProfile.OSFamily.LINUX, "Ubuntu", "22.04"),
    "ubuntu_24": (ServerProfile.OSFamily.LINUX, "Ubuntu", "24.04"),
    "debian_11": (ServerProfile.OSFamily.LINUX, "Debian", "11"),
    "debian_12": (ServerProfile.OSFamily.LINUX, "Debian", "12"),
    "centos_7": (ServerProfile.OSFamily.LINUX, "CentOS", "7"),
    "centos_8": (ServerProfile.OSFamily.LINUX, "CentOS", "8"),
}
_SERVER_COMPUTE_MAP: dict[str, str] = {
    "bare_metal": ServerProfile.ComputeType.BARE_METAL,
    "vm": ServerProfile.ComputeType.VIRTUAL_MACHINE,
    "container_host": ServerProfile.ComputeType.CONTAINER_HOST,
}
_DATABASE_ENGINE_MAP: dict[str, str] = {
    "mysql": DatabaseInstance.Engine.MYSQL,
    "postgres": DatabaseInstance.Engine.POSTGRESQL,
    "mongodb": DatabaseInstance.Engine.MONGODB,
    "redis": DatabaseInstance.Engine.REDIS,
    "mariadb": DatabaseInstance.Engine.MARIADB,
    "other": DatabaseInstance.Engine.OTHER,
}
_DATABASE_HOSTING_MAP: dict[str, str] = {
    "self_hosted": DatabaseInstance.HostingType.SELF_HOSTED,
    "do": DatabaseInstance.HostingType.MANAGED,
    "aws_rds": DatabaseInstance.HostingType.MANAGED,
    "aws_dynamodb": DatabaseInstance.HostingType.MANAGED,
    "google_cloud": DatabaseInstance.HostingType.MANAGED,
    "azure": DatabaseInstance.HostingType.MANAGED,
    "heroku": DatabaseInstance.HostingType.MANAGED,
    "other": DatabaseInstance.HostingType.OTHER,
}
_APPLICATION_TYPE_MAP: dict[str, str] = {
    "web_app": ApplicationProfile.ApplicationType.WEB_APP,
    "saas": ApplicationProfile.ApplicationType.SAAS,
    "bot": ApplicationProfile.ApplicationType.BOT,
    "mobile": ApplicationProfile.ApplicationType.MOBILE,
    "hybrid": ApplicationProfile.ApplicationType.HYBRID,
    "api": ApplicationProfile.ApplicationType.API,
}


def _promote_server(legacy: Server, resource: InfrastructureResource) -> ServerProfile:
    os_family, distribution, os_version = _SERVER_OS_MAP.get(
        legacy.os,
        (ServerProfile.OSFamily.OTHER, "", ""),
    )
    role = dict(Server.ROLE_CHOICES).get(legacy.role, legacy.role)
    profile, _ = ServerProfile.objects.get_or_create(
        resource=resource,
        defaults={
            "hostname": legacy.hostname,
            "role": role,
            "compute_type": _SERVER_COMPUTE_MAP.get(
                legacy.virtualization_type,
                ServerProfile.ComputeType.OTHER,
            ),
            "cpu_model": legacy.cpu,
            "ram_mb": legacy.ram_gb * 1024 if legacy.ram_gb is not None else None,
            "root_disk_gb": legacy.disk_gb,
            "os_family": os_family,
            "distribution": distribution,
            "os_version": os_version,
            "region": legacy.region,
            "virtualization_type": legacy.get_virtualization_type_display(),
        },
    )
    profile.full_clean()
    profile.save()

    address_rows: list[tuple[str, str]] = []
    if legacy.public_ip:
        address_rows.append((legacy.public_ip, IPAddress.Scope.PUBLIC))
    if legacy.private_ip and legacy.private_ip != legacy.public_ip:
        address_rows.append((legacy.private_ip, IPAddress.Scope.PRIVATE))

    for index, (address, scope) in enumerate(address_rows):
        ip_address, created = IPAddress.objects.get_or_create(
            resource=resource,
            address=address,
            defaults={
                "scope": scope,
                "is_primary": index == 0,
                "description": "Promoted from the legacy Server inventory.",
            },
        )
        if created:
            ip_address.full_clean()
            ip_address.save()

    return profile


def _promote_database(
    legacy: Database,
    resource: InfrastructureResource,
) -> DatabaseInstance:
    database, _ = DatabaseInstance.objects.get_or_create(
        resource=resource,
        defaults={
            "engine": _DATABASE_ENGINE_MAP.get(
                legacy.db_type,
                DatabaseInstance.Engine.OTHER,
            ),
            "engine_version": legacy.version,
            "hosting_type": _DATABASE_HOSTING_MAP.get(
                legacy.provider,
                DatabaseInstance.HostingType.OTHER,
            ),
        },
    )
    database.full_clean()
    database.save()
    return database


def _promote_application(
    legacy: Application,
    resource: InfrastructureResource,
) -> ApplicationProfile:
    application, _ = ApplicationProfile.objects.get_or_create(
        resource=resource,
        defaults={
            "application_type": _APPLICATION_TYPE_MAP.get(
                legacy.app_type,
                ApplicationProfile.ApplicationType.OTHER,
            ),
        },
    )
    application.full_clean()
    application.save()
    return application


def promote_legacy_specialist(
    legacy_type: str,
    legacy: Any,
    resource: InfrastructureResource,
) -> None:
    """Promote deterministic legacy fields into modern typed specialists.

    Provider/account identity, free-text operational notes, and ambiguous component
    relationships are deliberately not inferred here. Those remain explicit operator
    decisions in the modern workspace.
    """

    if legacy_type == "server" and isinstance(legacy, Server):
        _promote_server(legacy, resource)
    elif legacy_type == "database" and isinstance(legacy, Database):
        _promote_database(legacy, resource)
    elif legacy_type == "application" and isinstance(legacy, Application):
        _promote_application(legacy, resource)

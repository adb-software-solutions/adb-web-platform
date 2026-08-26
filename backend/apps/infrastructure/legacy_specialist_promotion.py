from __future__ import annotations

from datetime import datetime, time
from typing import Any

from django.utils import timezone

from .models import (
    Application,
    ApplicationProfile,
    Database,
    DatabaseInstance,
    Domain,
    DomainProfile,
    DomainResourceIdentity,
    InfrastructureResource,
    IPAddress,
    Server,
    ServerProfile,
    SSLCertificate,
    TLSCertificate,
    TLSCertificateDomain,
    Website,
    WebsiteEndpoint,
    WebsiteProfile,
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
_SSL_CERTIFICATE_TYPE_MAP: dict[str, str] = {
    "letsencrypt": TLSCertificate.CertificateType.ACME,
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


def _promote_website(
    legacy: Website,
    resource: InfrastructureResource,
) -> WebsiteProfile:
    website, _ = WebsiteProfile.objects.get_or_create(
        resource=resource,
        defaults={
            "website_type": WebsiteProfile.WebsiteType.WEB_APP,
            "admin_url": legacy.admin_url,
        },
    )
    website.full_clean()
    website.save()

    endpoint = WebsiteEndpoint.objects.filter(
        website=website,
        url=legacy.primary_url,
    ).first()
    if endpoint is None:
        endpoint_resource = InfrastructureResource(
            ownership_type=resource.ownership_type,
            client=resource.client,
            name=f"{resource.name} primary endpoint",
            resource_type=InfrastructureResource.ResourceType.WEBSITE_ENDPOINT,
            lifecycle_status=resource.lifecycle_status,
            environment=resource.environment,
            criticality=resource.criticality,
            description="Promoted from the legacy Website primary URL.",
            created_by=resource.created_by,
            updated_by=resource.updated_by,
        )
        endpoint_resource.full_clean()
        endpoint_resource.save()
        endpoint = WebsiteEndpoint(
            resource=endpoint_resource,
            website=website,
            url=legacy.primary_url,
            role=WebsiteEndpoint.Role.PRIMARY,
            is_primary=True,
        )
        endpoint.full_clean()
        endpoint.save()

    return website


def _promote_domain(
    legacy: Domain,
    resource: InfrastructureResource,
) -> DomainProfile:
    domain, _ = DomainProfile.objects.get_or_create(
        resource=resource,
        defaults={
            "domain_name": legacy.domain_name,
            "expires_on": legacy.expiry_date,
            "auto_renew": legacy.auto_renew,
        },
    )
    domain.full_clean()
    domain.save()
    return domain


def _legacy_expiry_datetime(legacy: SSLCertificate) -> datetime:
    return timezone.make_aware(datetime.combine(legacy.expiry_date, time.max))


def _promote_ssl_certificate(
    legacy: SSLCertificate,
    resource: InfrastructureResource,
) -> TLSCertificate:
    certificate, _ = TLSCertificate.objects.get_or_create(
        resource=resource,
        defaults={
            "certificate_type": _SSL_CERTIFICATE_TYPE_MAP.get(
                legacy.provider,
                TLSCertificate.CertificateType.OTHER,
            ),
            "issuer": dict(SSLCertificate.PROVIDER_CHOICES).get(
                legacy.provider,
                legacy.provider,
            ),
            "subject_common_name": legacy.domain.domain_name,
            "expires_at": _legacy_expiry_datetime(legacy),
        },
    )
    certificate.full_clean()
    certificate.save()

    domain_identity = (
        DomainResourceIdentity.objects.select_related("resource")
        .filter(domain=legacy.domain)
        .first()
    )
    if domain_identity is not None:
        domain = DomainProfile.objects.filter(resource=domain_identity.resource).first()
        if domain is not None:
            link, _ = TLSCertificateDomain.objects.get_or_create(
                certificate=certificate,
                domain=domain,
                defaults={"is_primary": True},
            )
            link.full_clean()
            link.save()

    return certificate


def promote_legacy_specialist(
    legacy_type: str,
    legacy: Any,
    resource: InfrastructureResource,
) -> None:
    """Promote deterministic legacy fields into modern typed specialists.

    Provider/account identity, free-text operational notes, comma-separated aliases
    and nameservers, and ambiguous component relationships are deliberately not
    inferred here. Those remain explicit operator decisions in the modern workspace.
    """

    if legacy_type == "server" and isinstance(legacy, Server):
        _promote_server(legacy, resource)
    elif legacy_type == "database" and isinstance(legacy, Database):
        _promote_database(legacy, resource)
    elif legacy_type == "application" and isinstance(legacy, Application):
        _promote_application(legacy, resource)
    elif legacy_type == "website" and isinstance(legacy, Website):
        _promote_website(legacy, resource)
    elif legacy_type == "domain" and isinstance(legacy, Domain):
        _promote_domain(legacy, resource)
    elif legacy_type == "ssl_certificate" and isinstance(legacy, SSLCertificate):
        _promote_ssl_certificate(legacy, resource)

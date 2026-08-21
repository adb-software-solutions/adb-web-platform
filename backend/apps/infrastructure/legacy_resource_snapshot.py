from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from django.db import models

from apps.infrastructure.legacy_reconciliation import get_legacy_definition_for_resource
from apps.infrastructure.models import (
    API,
    Application,
    Bot,
    Database,
    Domain,
    EmailSystem,
    InfrastructureResource,
    Licence,
    MobileApp,
    Server,
    SSLCertificate,
    Website,
)

SpecialistFieldKind = Literal["text", "code", "url", "multiline"]


@dataclass(frozen=True)
class SpecialistField:
    key: str
    label: str
    value: str
    kind: SpecialistFieldKind = "text"


@dataclass(frozen=True)
class LegacyResourceSnapshot:
    legacy_type: str
    legacy_id: int
    name: str
    register_path: str
    fields: tuple[SpecialistField, ...]


REGISTER_PATHS = {
    "server": "/admin/infrastructure/servers",
    "database": "/admin/infrastructure/databases",
    "website": "/admin/infrastructure/websites",
    "domain": "/admin/infrastructure/domains",
    "ssl_certificate": "/admin/infrastructure/ssl-certificates",
    "licence": "/admin/infrastructure/licences",
    "application": "/admin/infrastructure/applications",
    "mobile_app": "/admin/infrastructure/mobile-apps",
    "api": "/admin/infrastructure/apis",
    "bot": "/admin/infrastructure/bots",
    "email_system": "/admin/infrastructure/email-systems",
}


def _choice(instance: Any, field_name: str) -> str:
    display = getattr(instance, f"get_{field_name}_display", None)
    if callable(display):
        return str(display())
    return str(getattr(instance, field_name, ""))


def _related(manager: Any) -> str:
    return ", ".join(str(item) for item in manager.all())


def _value(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _field(
    key: str,
    label: str,
    value: Any,
    kind: SpecialistFieldKind = "text",
) -> SpecialistField | None:
    rendered = _value(value)
    if not rendered:
        return None
    return SpecialistField(key=key, label=label, value=rendered, kind=kind)


def _fields(*fields: SpecialistField | None) -> tuple[SpecialistField, ...]:
    return tuple(field for field in fields if field is not None)


def _specialist_fields(legacy: models.Model) -> tuple[SpecialistField, ...]:
    if isinstance(legacy, Server):
        return _fields(
            _field("hostname", "Hostname", legacy.hostname, "code"),
            _field("role", "Role", _choice(legacy, "role")),
            _field("provider", "Provider", _choice(legacy, "provider")),
            _field("region", "Region", legacy.region),
            _field("os", "Operating system", _choice(legacy, "os")),
            _field("public_ip", "Public IP", legacy.public_ip, "code"),
            _field("private_ip", "Private IP", legacy.private_ip, "code"),
            _field("cpu", "CPU", legacy.cpu),
            _field("ram_gb", "RAM", f"{legacy.ram_gb} GB" if legacy.ram_gb is not None else ""),
            _field("disk_gb", "Disk", f"{legacy.disk_gb} GB" if legacy.disk_gb is not None else ""),
            _field(
                "virtualization_type",
                "Virtualisation",
                _choice(legacy, "virtualization_type"),
            ),
        )

    if isinstance(legacy, Database):
        return _fields(
            _field("db_type", "Database type", _choice(legacy, "db_type")),
            _field("provider", "Provider", _choice(legacy, "provider")),
            _field("server", "Server", legacy.server),
            _field("version", "Version", legacy.version, "code"),
            _field("backup_strategy", "Backup strategy", legacy.backup_strategy, "multiline"),
        )

    if isinstance(legacy, Website):
        return _fields(
            _field("primary_url", "Primary URL", legacy.primary_url, "url"),
            _field("environment_type", "Legacy environment", _choice(legacy, "environment_type")),
            _field("servers", "Servers", _related(legacy.servers)),
            _field("database", "Database", legacy.database),
            _field("admin_url", "Admin URL", legacy.admin_url, "url"),
            _field("github_repository", "GitHub repository", legacy.github_repository, "url"),
            _field("has_cdn", "CDN enabled", legacy.has_cdn),
            _field("cdn_provider", "CDN provider", legacy.cdn_provider),
            _field("cache_layer", "Cache layer", legacy.cache_layer),
            _field("aliases", "Aliases / redirects", legacy.aliases, "multiline"),
            _field("staging_site", "Staging site", legacy.staging_site),
        )

    if isinstance(legacy, Domain):
        return _fields(
            _field("domain_name", "Domain", legacy.domain_name, "code"),
            _field("registrar", "Registrar", _choice(legacy, "registrar")),
            _field("expiry_date", "Expiry date", legacy.expiry_date),
            _field("auto_renew", "Auto renew", legacy.auto_renew),
            _field("nameservers", "Nameservers", legacy.nameservers, "multiline"),
            _field("websites", "Websites", _related(legacy.websites)),
        )

    if isinstance(legacy, SSLCertificate):
        return _fields(
            _field("domain", "Domain", legacy.domain),
            _field("provider", "Provider", _choice(legacy, "provider")),
            _field("cert_type", "Certificate type", legacy.cert_type),
            _field("expiry_date", "Expiry date", legacy.expiry_date),
        )

    if isinstance(legacy, Licence):
        return _fields(
            _field("licence_type", "Licence type", _choice(legacy, "licence_type")),
            _field("vendor", "Vendor", legacy.vendor),
            _field("renewal_date", "Renewal date", legacy.renewal_date),
            _field("renewal_cost", "Renewal cost", legacy.renewal_cost),
            _field("auto_renew", "Auto renew", legacy.auto_renew),
            _field("portal_url", "Vendor portal", legacy.portal_url, "url"),
            _field("websites", "Websites", _related(legacy.websites)),
        )

    if isinstance(legacy, Application):
        return _fields(
            _field("app_type", "Application type", _choice(legacy, "app_type")),
            _field("status", "Legacy status", _choice(legacy, "status")),
            _field("description", "Description", legacy.description, "multiline"),
            _field("websites", "Websites", _related(legacy.websites)),
            _field("servers", "Servers", _related(legacy.servers)),
            _field("databases", "Databases", _related(legacy.databases)),
            _field("domains", "Domains", _related(legacy.domains)),
            _field("licences", "Licences", _related(legacy.licences)),
        )

    if isinstance(legacy, MobileApp):
        return _fields(
            _field("platform", "Platform", _choice(legacy, "platform")),
            _field("framework", "Framework", _choice(legacy, "framework")),
            _field("bundle_id", "Bundle / package ID", legacy.bundle_id, "code"),
            _field("current_version", "Current version", legacy.current_version, "code"),
            _field("release_status", "Release status", _choice(legacy, "release_status")),
            _field("app_store_link", "App Store", legacy.app_store_link, "url"),
            _field("play_store_link", "Play Store", legacy.play_store_link, "url"),
            _field("backend_api", "Backend API", legacy.backend_api, "url"),
            _field("github_repository", "GitHub repository", legacy.github_repository, "url"),
        )

    if isinstance(legacy, API):
        return _fields(
            _field("api_type", "API type", _choice(legacy, "api_type")),
            _field("description", "Description", legacy.description, "multiline"),
            _field("base_url", "Base URL", legacy.base_url, "url"),
            _field("visibility", "Visibility", _choice(legacy, "visibility")),
            _field("authentication", "Authentication", _choice(legacy, "authentication")),
            _field("versioning_strategy", "Versioning", legacy.versioning_strategy),
            _field("rate_limiting", "Rate limiting", legacy.rate_limiting, "multiline"),
            _field("documentation_url", "Documentation", legacy.documentation_url, "url"),
            _field("github_repository", "GitHub repository", legacy.github_repository, "url"),
        )

    if isinstance(legacy, Bot):
        return _fields(
            _field("platform", "Platform", _choice(legacy, "platform")),
            _field("bot_type", "Bot type", _choice(legacy, "bot_type")),
            _field("runtime", "Runtime", _choice(legacy, "runtime")),
            _field("hosting_location", "Hosting location", legacy.hosting_location),
            _field("permissions", "Permissions / scopes", legacy.permissions, "multiline"),
            _field("github_repository", "GitHub repository", legacy.github_repository, "url"),
        )

    if isinstance(legacy, EmailSystem):
        return _fields(
            _field("provider", "Provider", _choice(legacy, "provider")),
            _field("admin_portal_url", "Admin portal", legacy.admin_portal_url, "url"),
            _field("domains", "Domains", legacy.domains, "multiline"),
            _field("spf_status", "SPF status", legacy.spf_status),
            _field("dkim_status", "DKIM status", legacy.dkim_status),
            _field("dmarc_status", "DMARC status", legacy.dmarc_status),
        )

    return ()


def legacy_resource_snapshot(resource: InfrastructureResource) -> LegacyResourceSnapshot | None:
    definition = get_legacy_definition_for_resource(resource)
    if definition is None:
        return None

    identity_manager = cast(Any, definition.identity_model).objects
    identity = (
        identity_manager.filter(resource_id=resource.id)
        .select_related(definition.identity_field)
        .first()
    )
    if identity is None:
        return None

    legacy = cast(models.Model, getattr(identity, definition.identity_field))
    return LegacyResourceSnapshot(
        legacy_type=definition.key,
        legacy_id=int(legacy.pk),
        name=definition.display_name(legacy),
        register_path=REGISTER_PATHS[definition.key],
        fields=_specialist_fields(legacy),
    )

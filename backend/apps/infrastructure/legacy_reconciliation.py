from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import models, transaction

from apps.clients.models import Client

from .legacy_specialist_promotion import promote_legacy_specialist
from .models import (
    API,
    APIResourceIdentity,
    Application,
    ApplicationResourceIdentity,
    Bot,
    BotResourceIdentity,
    Database,
    DatabaseResourceIdentity,
    Domain,
    DomainResourceIdentity,
    EmailSystem,
    EmailSystemResourceIdentity,
    InfrastructureResource,
    Licence,
    LicenceResourceIdentity,
    MobileApp,
    MobileAppResourceIdentity,
    Server,
    ServerResourceIdentity,
    SSLCertificate,
    SSLCertificateResourceIdentity,
    Website,
    WebsiteResourceIdentity,
)


class LegacyResourceError(Exception):
    """Base exception for legacy reconciliation failures."""


class LegacyResourceTypeError(LegacyResourceError):
    """Raised when an unknown legacy resource type is requested."""


class LegacyResourceNotFoundError(LegacyResourceError):
    """Raised when the requested legacy record does not exist."""


class LegacyResourceAlreadyLinkedError(LegacyResourceError):
    """Raised when the legacy record already has a structured identity."""


@dataclass(frozen=True)
class LegacyResourceDefinition:
    key: str
    label: str
    model: Any
    identity_model: Any
    identity_field: str
    resource_type: str
    display_name: Callable[[Any], str]
    select_related: tuple[str, ...] = ()


def _name(instance: Any) -> str:
    return str(instance.name)


def _server_name(instance: Any) -> str:
    return str(instance.hostname)


def _domain_name(instance: Any) -> str:
    return str(instance.domain_name)


LEGACY_RESOURCE_DEFINITIONS: tuple[LegacyResourceDefinition, ...] = (
    LegacyResourceDefinition(
        key="server",
        label="Server",
        model=Server,
        identity_model=ServerResourceIdentity,
        identity_field="server",
        resource_type=InfrastructureResource.ResourceType.SERVER,
        display_name=_server_name,
    ),
    LegacyResourceDefinition(
        key="database",
        label="Database",
        model=Database,
        identity_model=DatabaseResourceIdentity,
        identity_field="database",
        resource_type=InfrastructureResource.ResourceType.DATABASE_INSTANCE,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="website",
        label="Website",
        model=Website,
        identity_model=WebsiteResourceIdentity,
        identity_field="website",
        resource_type=InfrastructureResource.ResourceType.WEBSITE,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="domain",
        label="Domain",
        model=Domain,
        identity_model=DomainResourceIdentity,
        identity_field="domain",
        resource_type=InfrastructureResource.ResourceType.DOMAIN,
        display_name=_domain_name,
    ),
    LegacyResourceDefinition(
        key="ssl_certificate",
        label="SSL certificate",
        model=SSLCertificate,
        identity_model=SSLCertificateResourceIdentity,
        identity_field="ssl_certificate",
        resource_type=InfrastructureResource.ResourceType.TLS_CERTIFICATE,
        display_name=str,
        select_related=("domain",),
    ),
    LegacyResourceDefinition(
        key="licence",
        label="Licence",
        model=Licence,
        identity_model=LicenceResourceIdentity,
        identity_field="licence",
        resource_type=InfrastructureResource.ResourceType.LICENCE,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="application",
        label="Application",
        model=Application,
        identity_model=ApplicationResourceIdentity,
        identity_field="application",
        resource_type=InfrastructureResource.ResourceType.APPLICATION,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="mobile_app",
        label="Mobile app",
        model=MobileApp,
        identity_model=MobileAppResourceIdentity,
        identity_field="mobile_app",
        resource_type=InfrastructureResource.ResourceType.MOBILE_APP,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="api",
        label="API",
        model=API,
        identity_model=APIResourceIdentity,
        identity_field="api",
        resource_type=InfrastructureResource.ResourceType.API,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="bot",
        label="Bot",
        model=Bot,
        identity_model=BotResourceIdentity,
        identity_field="bot",
        resource_type=InfrastructureResource.ResourceType.BOT,
        display_name=_name,
    ),
    LegacyResourceDefinition(
        key="email_system",
        label="Email system",
        model=EmailSystem,
        identity_model=EmailSystemResourceIdentity,
        identity_field="email_system",
        resource_type=InfrastructureResource.ResourceType.EMAIL_SYSTEM,
        display_name=str,
    ),
)

_DEFINITIONS_BY_KEY = {definition.key: definition for definition in LEGACY_RESOURCE_DEFINITIONS}
_DEFINITIONS_BY_RESOURCE_TYPE = {
    definition.resource_type: definition for definition in LEGACY_RESOURCE_DEFINITIONS
}


def get_legacy_resource_definition(key: str) -> LegacyResourceDefinition:
    try:
        return _DEFINITIONS_BY_KEY[key]
    except KeyError as exc:
        raise LegacyResourceTypeError(f"Unknown legacy infrastructure type: {key}") from exc


def get_legacy_definition_for_resource(
    resource: InfrastructureResource,
) -> LegacyResourceDefinition | None:
    return _DEFINITIONS_BY_RESOURCE_TYPE.get(resource.resource_type)


def get_legacy_identity(
    definition: LegacyResourceDefinition,
    legacy_id: int,
) -> models.Model | None:
    return (
        definition.identity_model.objects.select_related("resource", "resource__client")
        .filter(**{f"{definition.identity_field}_id": legacy_id})
        .first()
    )


def legacy_resource_reference(
    resource: InfrastructureResource,
) -> tuple[str, int, str] | None:
    definition = get_legacy_definition_for_resource(resource)
    if definition is None:
        return None

    identity = (
        definition.identity_model.objects.filter(resource_id=resource.id)
        .select_related(definition.identity_field)
        .first()
    )
    if identity is None:
        return None

    legacy = getattr(identity, definition.identity_field)
    return definition.key, int(legacy.pk), definition.display_name(legacy)


@transaction.atomic
def reconcile_legacy_resource(
    *,
    legacy_type: str,
    legacy_id: int,
    ownership_type: str,
    client: Client | None,
    lifecycle_status: str,
    environment: str,
    criticality: str,
    name: str | None,
    linked_by: Any | None,
) -> InfrastructureResource:
    definition = get_legacy_resource_definition(legacy_type)
    queryset = definition.model.objects.select_for_update()
    if definition.select_related:
        queryset = queryset.select_related(*definition.select_related)
    legacy = queryset.filter(pk=legacy_id).first()
    if legacy is None:
        raise LegacyResourceNotFoundError(f"{definition.label} record {legacy_id} was not found.")

    if get_legacy_identity(definition, legacy_id) is not None:
        raise LegacyResourceAlreadyLinkedError(
            f"{definition.label} record {legacy_id} is already reconciled."
        )

    resource_name = (name or "").strip() or definition.display_name(legacy)
    resource = InfrastructureResource(
        ownership_type=ownership_type,
        client=client,
        name=resource_name,
        resource_type=definition.resource_type,
        lifecycle_status=lifecycle_status,
        environment=environment,
        criticality=criticality,
        created_by=linked_by,
        updated_by=linked_by,
    )
    resource.full_clean()
    resource.save()

    identity_kwargs: dict[str, Any] = {
        "resource": resource,
        definition.identity_field: legacy,
        "linked_by": linked_by,
    }
    identity = definition.identity_model(**identity_kwargs)
    identity.full_clean()
    identity.save()

    promote_legacy_specialist(definition.key, legacy, resource)
    return resource


def reconciliation_counts() -> tuple[int, int]:
    total = 0
    linked = 0
    for definition in LEGACY_RESOURCE_DEFINITIONS:
        total += definition.model.objects.count()
        linked += definition.identity_model.objects.count()
    return total, linked


def legacy_rows(
    *,
    legacy_type: str | None = None,
    status: str = "unlinked",
) -> list[tuple[LegacyResourceDefinition, models.Model, models.Model | None]]:
    definitions = (
        (get_legacy_resource_definition(legacy_type),)
        if legacy_type
        else LEGACY_RESOURCE_DEFINITIONS
    )
    rows: list[tuple[LegacyResourceDefinition, models.Model, models.Model | None]] = []

    for definition in definitions:
        identities = {
            getattr(identity, f"{definition.identity_field}_id"): identity
            for identity in definition.identity_model.objects.select_related(
                "resource",
                "resource__client",
            )
        }
        queryset = definition.model.objects.all()
        if definition.select_related:
            queryset = queryset.select_related(*definition.select_related)
        for legacy in queryset:
            identity = identities.get(legacy.pk)
            if status == "linked" and identity is None:
                continue
            if status == "unlinked" and identity is not None:
                continue
            rows.append((definition, legacy, identity))

    rows.sort(key=lambda row: (row[0].label.lower(), row[0].display_name(row[1]).lower()))
    return rows

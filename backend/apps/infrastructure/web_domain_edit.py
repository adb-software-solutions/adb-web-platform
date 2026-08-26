from __future__ import annotations

from datetime import date, datetime
from typing import TypeAlias

from .models import (
    DNSZone,
    DomainProfile,
    InfrastructureResource,
    TLSCertificate,
    WebsiteEndpoint,
    WebsiteProfile,
)

SpecialistEditValue: TypeAlias = str | int | bool | list[str] | None


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _provider_resource_id(provider_account: object | None) -> int | None:
    if provider_account is None:
        return None
    return getattr(provider_account, "resource_id", None)


def _website_edit(resource: InfrastructureResource) -> dict[str, SpecialistEditValue] | None:
    website = WebsiteProfile.objects.filter(resource=resource).first()
    if website is None:
        return None
    return {
        "website_type": website.website_type,
        "admin_url": website.admin_url,
        "cms": website.cms,
        "cms_version": website.cms_version,
        "hosting_provider_account_resource_id": _provider_resource_id(
            website.hosting_provider_account if website.hosting_provider_account_id else None
        ),
        "cdn_provider_account_resource_id": _provider_resource_id(
            website.cdn_provider_account if website.cdn_provider_account_id else None
        ),
        "waf_provider_account_resource_id": _provider_resource_id(
            website.waf_provider_account if website.waf_provider_account_id else None
        ),
    }


def _website_endpoint_edit(
    resource: InfrastructureResource,
) -> dict[str, SpecialistEditValue] | None:
    endpoint = WebsiteEndpoint.objects.filter(resource=resource).first()
    if endpoint is None:
        return None

    application_environment = endpoint.application_environment
    domain = endpoint.domain
    tls_certificate = endpoint.tls_certificate
    return {
        "website_resource_id": endpoint.website.resource_id,
        "application_environment_resource_id": (
            application_environment.resource_id if application_environment is not None else None
        ),
        "domain_resource_id": domain.resource_id if domain is not None else None,
        "tls_certificate_resource_id": (
            tls_certificate.resource_id if tls_certificate is not None else None
        ),
        "url": endpoint.url,
        "role": endpoint.role,
        "is_primary": endpoint.is_primary,
        "redirects_to": endpoint.redirects_to,
    }


def _domain_edit(resource: InfrastructureResource) -> dict[str, SpecialistEditValue] | None:
    domain = DomainProfile.objects.filter(resource=resource).first()
    if domain is None:
        return None
    return {
        "domain_name": domain.domain_name,
        "registrar_account_resource_id": _provider_resource_id(
            domain.registrar_account if domain.registrar_account_id else None
        ),
        "provider_domain_id": domain.provider_domain_id,
        "status": domain.status,
        "registered_on": _iso(domain.registered_on),
        "expires_on": _iso(domain.expires_on),
        "auto_renew": domain.auto_renew,
        "transfer_lock_enabled": domain.transfer_lock_enabled,
        "privacy_enabled": domain.privacy_enabled,
    }


def _dns_zone_edit(resource: InfrastructureResource) -> dict[str, SpecialistEditValue] | None:
    zone = DNSZone.objects.filter(resource=resource).first()
    if zone is None:
        return None
    return {
        "domain_resource_id": zone.domain.resource_id,
        "provider_account_resource_id": _provider_resource_id(
            zone.provider_account if zone.provider_account_id else None
        ),
        "zone_name": zone.zone_name,
        "provider_zone_id": zone.provider_zone_id,
        "dnssec_enabled": zone.dnssec_enabled,
        "is_primary": zone.is_primary,
    }


def _tls_certificate_edit(
    resource: InfrastructureResource,
) -> dict[str, SpecialistEditValue] | None:
    certificate = TLSCertificate.objects.filter(resource=resource).first()
    if certificate is None:
        return None
    return {
        "provider_account_resource_id": _provider_resource_id(
            certificate.provider_account if certificate.provider_account_id else None
        ),
        "certificate_type": certificate.certificate_type,
        "issuer": certificate.issuer,
        "subject_common_name": certificate.subject_common_name,
        "provider_certificate_id": certificate.provider_certificate_id,
        "serial_number": certificate.serial_number,
        "fingerprint_sha256": certificate.fingerprint_sha256,
        "issued_at": _iso(certificate.issued_at),
        "expires_at": _iso(certificate.expires_at),
        "auto_renew": certificate.auto_renew,
    }


def web_domain_edit_values(
    resource: InfrastructureResource,
) -> dict[str, SpecialistEditValue] | None:
    """Return exact non-secret web/domain values for the shared resource editor."""

    if resource.resource_type == InfrastructureResource.ResourceType.WEBSITE:
        return _website_edit(resource)
    if resource.resource_type == InfrastructureResource.ResourceType.WEBSITE_ENDPOINT:
        return _website_endpoint_edit(resource)
    if resource.resource_type == InfrastructureResource.ResourceType.DOMAIN:
        return _domain_edit(resource)
    if resource.resource_type == InfrastructureResource.ResourceType.DNS_ZONE:
        return _dns_zone_edit(resource)
    if resource.resource_type == InfrastructureResource.ResourceType.TLS_CERTIFICATE:
        return _tls_certificate_edit(resource)
    return None

from datetime import date, datetime

from ninja import Schema

from .specialist_schemas import (
    ClientOptionOut,
    ProviderAccountOptionOut,
    StructuredResourceIn,
    StructuredResourceUpdateIn,
)


class ApplicationEnvironmentOptionOut(Schema):
    resource_id: int
    name: str
    application_name: str
    environment: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class WebsiteOptionOut(Schema):
    resource_id: int
    name: str
    website_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class DomainOptionOut(Schema):
    resource_id: int
    name: str
    domain_name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class TLSCertificateOptionOut(Schema):
    resource_id: int
    name: str
    subject_common_name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class WebDomainSpecialistOptionsOut(Schema):
    clients: list[ClientOptionOut]
    provider_accounts: list[ProviderAccountOptionOut]
    application_environments: list[ApplicationEnvironmentOptionOut]
    websites: list[WebsiteOptionOut]
    domains: list[DomainOptionOut]
    tls_certificates: list[TLSCertificateOptionOut]


class WebsiteCreateIn(StructuredResourceIn):
    website_type: str = "web_app"
    admin_url: str = ""
    cms: str = ""
    cms_version: str = ""
    hosting_provider_account_resource_id: int | None = None
    cdn_provider_account_resource_id: int | None = None
    waf_provider_account_resource_id: int | None = None


class WebsiteUpdateIn(StructuredResourceUpdateIn):
    website_type: str
    admin_url: str = ""
    cms: str = ""
    cms_version: str = ""
    hosting_provider_account_resource_id: int | None = None
    cdn_provider_account_resource_id: int | None = None
    waf_provider_account_resource_id: int | None = None


class WebsiteEndpointOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    website_resource_id: int
    website_name: str
    application_environment_resource_id: int | None
    application_environment_name: str | None
    domain_resource_id: int | None
    domain_name: str | None
    tls_certificate_resource_id: int | None
    tls_certificate_name: str | None
    url: str
    role: str
    is_primary: bool
    redirects_to: str
    updated_at: datetime


class WebsiteOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    website_type: str
    admin_url: str
    cms: str
    cms_version: str
    hosting_provider_account_resource_id: int | None
    hosting_provider_account_name: str | None
    cdn_provider_account_resource_id: int | None
    cdn_provider_account_name: str | None
    waf_provider_account_resource_id: int | None
    waf_provider_account_name: str | None
    endpoints: list[WebsiteEndpointOut]
    updated_at: datetime


class WebsiteEndpointCreateIn(StructuredResourceIn):
    website_resource_id: int
    application_environment_resource_id: int | None = None
    domain_resource_id: int | None = None
    tls_certificate_resource_id: int | None = None
    url: str
    role: str = "primary"
    is_primary: bool = False
    redirects_to: str = ""


class WebsiteEndpointUpdateIn(StructuredResourceUpdateIn):
    website_resource_id: int
    application_environment_resource_id: int | None = None
    domain_resource_id: int | None = None
    tls_certificate_resource_id: int | None = None
    url: str
    role: str
    is_primary: bool = False
    redirects_to: str = ""


class DomainCreateIn(StructuredResourceIn):
    domain_name: str
    registrar_account_resource_id: int | None = None
    provider_domain_id: str = ""
    status: str = "unknown"
    registered_on: date | None = None
    expires_on: date | None = None
    auto_renew: bool | None = None
    transfer_lock_enabled: bool | None = None
    privacy_enabled: bool | None = None


class DomainUpdateIn(StructuredResourceUpdateIn):
    domain_name: str
    registrar_account_resource_id: int | None = None
    provider_domain_id: str = ""
    status: str
    registered_on: date | None = None
    expires_on: date | None = None
    auto_renew: bool | None = None
    transfer_lock_enabled: bool | None = None
    privacy_enabled: bool | None = None


class DomainOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    domain_name: str
    registrar_account_resource_id: int | None
    registrar_account_name: str | None
    registrar_name: str | None
    provider_domain_id: str
    status: str
    registered_on: date | None
    expires_on: date | None
    auto_renew: bool | None
    transfer_lock_enabled: bool | None
    privacy_enabled: bool | None
    updated_at: datetime


class DNSRecordCreateIn(Schema):
    name: str
    record_type: str
    value: str
    ttl: int = 300
    priority: int | None = None
    weight: int | None = None
    port: int | None = None
    proxied: bool | None = None
    provider_record_id: str = ""


class DNSRecordUpdateIn(DNSRecordCreateIn):
    pass


class DNSRecordOut(Schema):
    id: int
    name: str
    record_type: str
    value: str
    ttl: int
    priority: int | None
    weight: int | None
    port: int | None
    proxied: bool | None
    provider_record_id: str


class DNSZoneCreateIn(StructuredResourceIn):
    domain_resource_id: int
    provider_account_resource_id: int | None = None
    zone_name: str
    provider_zone_id: str = ""
    dnssec_enabled: bool | None = None
    is_primary: bool = True


class DNSZoneUpdateIn(StructuredResourceUpdateIn):
    domain_resource_id: int
    provider_account_resource_id: int | None = None
    zone_name: str
    provider_zone_id: str = ""
    dnssec_enabled: bool | None = None
    is_primary: bool = True


class DNSZoneOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    domain_resource_id: int | None
    domain_name: str | None
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    zone_name: str
    provider_zone_id: str
    dnssec_enabled: bool | None
    is_primary: bool
    records: list[DNSRecordOut]
    updated_at: datetime


class TLSCertificateDomainCreateIn(Schema):
    domain_resource_id: int
    is_primary: bool = False


class TLSCertificateDomainOut(Schema):
    id: int
    domain_resource_id: int
    domain_name: str
    is_primary: bool


class TLSCertificateCreateIn(StructuredResourceIn):
    provider_account_resource_id: int | None = None
    certificate_type: str = "managed"
    issuer: str = ""
    subject_common_name: str = ""
    provider_certificate_id: str = ""
    serial_number: str = ""
    fingerprint_sha256: str = ""
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    auto_renew: bool | None = None


class TLSCertificateUpdateIn(StructuredResourceUpdateIn):
    provider_account_resource_id: int | None = None
    certificate_type: str
    issuer: str = ""
    subject_common_name: str = ""
    provider_certificate_id: str = ""
    serial_number: str = ""
    fingerprint_sha256: str = ""
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    auto_renew: bool | None = None


class TLSCertificateOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    certificate_type: str
    issuer: str
    subject_common_name: str
    provider_certificate_id: str
    serial_number: str
    fingerprint_sha256: str
    issued_at: datetime | None
    expires_at: datetime | None
    auto_renew: bool | None
    domains: list[TLSCertificateDomainOut]
    updated_at: datetime

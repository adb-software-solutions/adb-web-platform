from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from authentication.ninja.schemas import ProblemDetail

from .specialist_views import (
    CURRENT_LIFECYCLE_STATUSES,
    StaffProblem,
    _permission_problem,
    _problem,
)
from .web_domain_schemas import DNSRecordOut, TLSCertificateDomainOut, WebsiteEndpointOut
from .web_domain_views import (
    _dns_record_out,
    _endpoint_out,
    _tls_domain_out,
    _visible_dns_zone,
    _visible_resource_ids,
    _visible_tls_certificate,
    _visible_website,
)

web_domain_nested_router = Router(tags=["admin-infrastructure-web-domain-nested"])


@web_domain_nested_router.get(
    "/infrastructure/websites/{resource_id}/endpoints",
    response={
        200: list[WebsiteEndpointOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_website_endpoints(
    request: HttpRequest,
    resource_id: int,
) -> list[WebsiteEndpointOut] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_websiteprofile",
        "infrastructure.view_websiteendpoint",
    )
    if problem:
        return problem
    website = _visible_website(request, resource_id)
    if website is None:
        return _problem(404, "Website not found.", "not_found")
    visible_ids = _visible_resource_ids(request)
    return [
        _endpoint_out(endpoint, visible_ids)
        for endpoint in website.endpoints.all()
        if endpoint.resource_id in visible_ids
        and endpoint.resource.lifecycle_status in CURRENT_LIFECYCLE_STATUSES
    ]


@web_domain_nested_router.get(
    "/infrastructure/dns-zones/{resource_id}/records",
    response={
        200: list[DNSRecordOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_dns_records(
    request: HttpRequest,
    resource_id: int,
) -> list[DNSRecordOut] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_dnszone",
        "infrastructure.view_dnsrecord",
    )
    if problem:
        return problem
    zone = _visible_dns_zone(request, resource_id)
    if zone is None:
        return _problem(404, "DNS zone not found.", "not_found")
    return [_dns_record_out(record) for record in zone.records.all()]


@web_domain_nested_router.get(
    "/infrastructure/tls-certificates/{resource_id}/domains",
    response={
        200: list[TLSCertificateDomainOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_tls_certificate_domains(
    request: HttpRequest,
    resource_id: int,
) -> list[TLSCertificateDomainOut] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_tlscertificate",
        "infrastructure.view_domainprofile",
        "infrastructure.view_tlscertificatedomain",
    )
    if problem:
        return problem
    certificate = _visible_tls_certificate(request, resource_id)
    if certificate is None:
        return _problem(404, "TLS certificate not found.", "not_found")
    visible_ids = _visible_resource_ids(request)
    return [
        _tls_domain_out(link)
        for link in certificate.domain_links.all()
        if link.domain.resource_id in visible_ids
    ]

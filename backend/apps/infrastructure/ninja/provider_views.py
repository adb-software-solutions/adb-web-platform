from __future__ import annotations

import math
from typing import cast

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.text import slugify
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client
from apps.core.models import AuditEvent
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import InfrastructureResource, ProviderAccount, ServiceProvider
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .provider_schemas import (
    ProviderAccountCreateIn,
    ProviderAccountDetailOut,
    ProviderAccountLifecycleFilter,
    ProviderAccountOwnershipFilter,
    ProviderAccountPageOut,
    ProviderAccountSummaryOut,
    ProviderAccountUpdateIn,
    ProviderActiveFilter,
    ProviderCategoryOut,
    ProviderClientOptionOut,
    ProviderOptionsOut,
    ServiceProviderCreateIn,
    ServiceProviderDetailOut,
    ServiceProviderPageOut,
    ServiceProviderSummaryOut,
    ServiceProviderUpdateIn,
)

provider_router = Router(tags=["admin-infrastructure-providers"])
StaffProblem = tuple[int, dict[str, object]]
CURRENT_LIFECYCLE_STATUSES = (
    InfrastructureResource.LifecycleStatus.PLANNED,
    InfrastructureResource.LifecycleStatus.ACTIVE,
    InfrastructureResource.LifecycleStatus.MAINTENANCE,
    InfrastructureResource.LifecycleStatus.DEPRECATED,
)


def _permission_problem(
    request: HttpRequest,
    permission: str,
    message: str,
) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return 401, {
            "message": "User not authenticated",
            "success": False,
            "code": "unauthenticated",
        }
    if not (request.user.is_staff or request.user.is_superuser):
        return 403, {
            "message": "You do not have permission to access this resource.",
            "success": False,
            "code": "forbidden",
        }
    if not request.user.has_perm(permission):
        return 403, {"message": message, "success": False, "code": "forbidden"}
    return None


def _combined_permission_problem(
    request: HttpRequest,
    permissions: tuple[str, ...],
    message: str,
) -> StaffProblem | None:
    problem = _permission_problem(request, permissions[0], message)
    if problem:
        return problem
    if any(not request.user.has_perm(permission) for permission in permissions[1:]):
        return 403, {"message": message, "success": False, "code": "forbidden"}
    return None


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _validation_problem(error: ValidationError) -> StaffProblem:
    return _problem(400, " ".join(error.messages), "invalid_provider_data")


def _provider_queryset() -> QuerySet[ServiceProvider]:
    return ServiceProvider.objects.annotate(account_count=Count("accounts"))


def _provider_summary(provider: ServiceProvider) -> ServiceProviderSummaryOut:
    return ServiceProviderSummaryOut(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        category=provider.category,
        website_url=provider.website_url,
        support_url=provider.support_url,
        status_page_url=provider.status_page_url,
        documentation_url=provider.documentation_url,
        is_active=provider.is_active,
        account_count=getattr(provider, "account_count", provider.accounts.count()),
        updated_at=provider.updated_at,
    )


def _provider_detail(provider: ServiceProvider) -> ServiceProviderDetailOut:
    return ServiceProviderDetailOut(
        **_provider_summary(provider).model_dump(),
        notes=provider.notes,
        created_at=provider.created_at,
    )


def _account_queryset() -> QuerySet[ProviderAccount]:
    return ProviderAccount.objects.select_related("resource__client", "provider")


def _visible_accounts(request: HttpRequest) -> QuerySet[ProviderAccount]:
    visible_resources = scope_infrastructure_resources_for_user(request.user).filter(
        resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT
    )
    return _account_queryset().filter(resource__in=visible_resources)


def _account_summary(account: ProviderAccount) -> ProviderAccountSummaryOut:
    resource = account.resource
    return ProviderAccountSummaryOut(
        id=account.id,
        resource_id=resource.id,
        name=resource.name,
        provider_id=account.provider_id,
        provider_name=account.provider.name,
        provider_category=account.provider.category,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        lifecycle_status=resource.lifecycle_status,
        environment=resource.environment,
        criticality=resource.criticality,
        account_identifier=account.account_identifier,
        tenant_id=account.tenant_id,
        project_id=account.project_id,
        portal_url=account.portal_url,
        default_region=account.default_region,
        support_plan=account.support_plan,
        billing_reference=account.billing_reference,
        updated_at=max(resource.updated_at, account.updated_at),
    )


def _account_detail(account: ProviderAccount) -> ProviderAccountDetailOut:
    return ProviderAccountDetailOut(
        **_account_summary(account).model_dump(),
        description=account.resource.description,
        is_portal_visible=account.resource.is_portal_visible,
        created_at=account.resource.created_at,
    )


def _unique_provider_slug(name: str, *, provider_id: int | None = None) -> str:
    base = (slugify(name) or "provider")[:200]
    candidate = base
    suffix = 2
    providers = ServiceProvider.objects.all()
    if provider_id is not None:
        providers = providers.exclude(id=provider_id)
    while providers.filter(slug=candidate).exists():
        suffix_text = f"-{suffix}"
        candidate = f"{base[: 200 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def _active_provider(provider_id: int) -> ServiceProvider | None:
    return ServiceProvider.objects.filter(id=provider_id, is_active=True).first()


def _resolve_client(
    request: HttpRequest,
    ownership_type: str,
    client_id: int | None,
) -> tuple[Client | None, StaffProblem | None]:
    if ownership_type == OwnershipType.INTERNAL:
        if client_id is not None:
            return None, _problem(
                400, "Internal provider accounts cannot reference a client.", "invalid_ownership"
            )
        return None, None
    if ownership_type != OwnershipType.CLIENT or client_id is None:
        return None, _problem(
            400, "Client-owned provider accounts require a client.", "invalid_ownership"
        )
    client = scope_clients_for_user(request.user, Client.objects.all()).filter(id=client_id).first()
    if client is None:
        return None, _problem(404, "Client not found.", "not_found")
    return client, None


def _validate_resource_values(resource: InfrastructureResource) -> StaffProblem | None:
    if resource.lifecycle_status not in InfrastructureResource.LifecycleStatus.values:
        return _problem(400, "Choose a valid lifecycle status.", "invalid_lifecycle")
    if resource.environment not in InfrastructureResource.Environment.values:
        return _problem(400, "Choose a valid environment.", "invalid_environment")
    if resource.criticality not in InfrastructureResource.Criticality.values:
        return _problem(400, "Choose a valid criticality.", "invalid_criticality")
    return None


@provider_router.get(
    "/infrastructure/provider-options",
    response={200: ProviderOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def provider_options(request: HttpRequest) -> ProviderOptionsOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_provideraccount",
        "You do not have permission to view provider accounts.",
    )
    if problem:
        return problem
    clients = scope_clients_for_user(request.user, Client.objects.all()).filter(status="active")
    providers = _provider_queryset().filter(is_active=True).order_by("name")
    return ProviderOptionsOut(
        categories=[
            ProviderCategoryOut(value=value, label=label)
            for value, label in ServiceProvider.Category.choices
        ],
        clients=[
            ProviderClientOptionOut(id=client.id, name=str(client))
            for client in clients.order_by("company", "name", "id")
        ],
        providers=[_provider_summary(provider) for provider in providers],
    )


@provider_router.get(
    "/infrastructure/providers",
    response={200: ServiceProviderPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_service_providers(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    active: ProviderActiveFilter = "active",
    category: str | None = None,
    search: str | None = None,
) -> ServiceProviderPageOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_serviceprovider",
        "You do not have permission to view service providers.",
    )
    if problem:
        return problem
    providers = _provider_queryset()
    if active != "all":
        providers = providers.filter(is_active=active == "active")
    if category:
        providers = providers.filter(category=category)
    if search and search.strip():
        term = search.strip()
        providers = providers.filter(Q(name__icontains=term) | Q(notes__icontains=term))
    providers = providers.order_by("name", "id")
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = providers.count()
    start = (page - 1) * page_size
    return ServiceProviderPageOut(
        items=[_provider_summary(provider) for provider in providers[start : start + page_size]],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@provider_router.post(
    "/infrastructure/providers",
    response={
        201: ServiceProviderDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def create_service_provider(
    request: HttpRequest,
    payload: ServiceProviderCreateIn,
) -> tuple[int, ServiceProviderDetailOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_serviceprovider",
        "You do not have permission to create service providers.",
    )
    if problem:
        return problem
    name = payload.name.strip()
    if not name or payload.category not in ServiceProvider.Category.values:
        return _problem(
            400, "Enter a name and choose a valid provider category.", "invalid_provider"
        )
    provider = ServiceProvider(
        name=name,
        slug=_unique_provider_slug(name),
        category=payload.category,
        website_url=payload.website_url.strip(),
        support_url=payload.support_url.strip(),
        status_page_url=payload.status_page_url.strip(),
        documentation_url=payload.documentation_url.strip(),
        notes=payload.notes.strip(),
    )
    try:
        provider.full_clean()
        provider.save()
    except (ValidationError, IntegrityError) as error:
        if isinstance(error, ValidationError):
            return _validation_problem(error)
        return _problem(400, "A provider with this name already exists.", "duplicate_provider")
    AuditEvent.record(action="infrastructure.provider_created", actor=request.user, target=provider)
    provider = _provider_queryset().get(id=provider.id)
    return 201, _provider_detail(provider)


@provider_router.put(
    "/infrastructure/providers/{provider_id}",
    response={
        200: ServiceProviderDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_service_provider(
    request: HttpRequest,
    provider_id: int,
    payload: ServiceProviderUpdateIn,
) -> ServiceProviderDetailOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_serviceprovider",
        "You do not have permission to change service providers.",
    )
    if problem:
        return problem
    provider = ServiceProvider.objects.filter(id=provider_id).first()
    if provider is None:
        return _problem(404, "Service provider not found.", "not_found")
    if payload.name is not None:
        provider.name = payload.name.strip()
        provider.slug = _unique_provider_slug(provider.name, provider_id=provider.id)
    if payload.category is not None:
        provider.category = payload.category
    for field in ("website_url", "support_url", "status_page_url", "documentation_url", "notes"):
        value = getattr(payload, field)
        if value is not None:
            setattr(provider, field, value.strip())
    if payload.is_active is not None:
        provider.is_active = payload.is_active
    if not provider.name or provider.category not in ServiceProvider.Category.values:
        return _problem(
            400, "Enter a name and choose a valid provider category.", "invalid_provider"
        )
    try:
        provider.full_clean()
        provider.save()
    except ValidationError as error:
        return _validation_problem(error)
    AuditEvent.record(action="infrastructure.provider_updated", actor=request.user, target=provider)
    return _provider_detail(_provider_queryset().get(id=provider.id))


@provider_router.get(
    "/infrastructure/provider-accounts",
    response={200: ProviderAccountPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_provider_accounts(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    lifecycle: ProviderAccountLifecycleFilter = "current",
    ownership: ProviderAccountOwnershipFilter = "all",
    client_id: int | None = None,
    provider_id: int | None = None,
    search: str | None = None,
) -> ProviderAccountPageOut | StaffProblem:
    problem = _combined_permission_problem(
        request,
        ("infrastructure.view_provideraccount", "infrastructure.view_infrastructureresource"),
        "You do not have permission to view provider accounts.",
    )
    if problem:
        return problem
    accounts = _visible_accounts(request)
    if lifecycle == "current":
        accounts = accounts.filter(resource__lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES)
    elif lifecycle != "all":
        accounts = accounts.filter(resource__lifecycle_status=lifecycle)
    if ownership != "all":
        accounts = accounts.filter(resource__ownership_type=ownership)
    if client_id is not None:
        accounts = accounts.filter(resource__client_id=client_id)
    if provider_id is not None:
        accounts = accounts.filter(provider_id=provider_id)
    if search and search.strip():
        term = search.strip()
        accounts = accounts.filter(
            Q(resource__name__icontains=term)
            | Q(provider__name__icontains=term)
            | Q(account_identifier__icontains=term)
            | Q(tenant_id__icontains=term)
            | Q(project_id__icontains=term)
            | Q(resource__client__name__icontains=term)
            | Q(resource__client__company__icontains=term)
        )
    accounts = accounts.order_by("resource__name", "id")
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = accounts.count()
    start = (page - 1) * page_size
    return ProviderAccountPageOut(
        items=[_account_summary(account) for account in accounts[start : start + page_size]],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if total else 0,
    )


@provider_router.get(
    "/infrastructure/provider-accounts/{account_id}",
    response={
        200: ProviderAccountDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_provider_account(
    request: HttpRequest,
    account_id: int,
) -> ProviderAccountDetailOut | StaffProblem:
    problem = _combined_permission_problem(
        request,
        ("infrastructure.view_provideraccount", "infrastructure.view_infrastructureresource"),
        "You do not have permission to view provider accounts.",
    )
    if problem:
        return problem
    account = _visible_accounts(request).filter(id=account_id).first()
    if account is None:
        return _problem(404, "Provider account not found.", "not_found")
    return _account_detail(account)


@provider_router.post(
    "/infrastructure/provider-accounts",
    response={
        201: ProviderAccountDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_provider_account(
    request: HttpRequest,
    payload: ProviderAccountCreateIn,
) -> tuple[int, ProviderAccountDetailOut | dict[str, object]]:
    problem = _combined_permission_problem(
        request,
        ("infrastructure.add_provideraccount", "infrastructure.add_infrastructureresource"),
        "You do not have permission to create provider accounts.",
    )
    if problem:
        return problem
    provider = _active_provider(payload.provider_id)
    if provider is None:
        return _problem(400, "Choose a valid active service provider.", "invalid_provider")
    client, client_problem = _resolve_client(request, payload.ownership_type, payload.client_id)
    if client_problem:
        return client_problem
    actor = cast(User, request.user)
    try:
        with transaction.atomic():
            resource = InfrastructureResource(
                ownership_type=payload.ownership_type,
                client=client,
                name=payload.name.strip(),
                resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
                lifecycle_status=payload.lifecycle_status,
                environment=payload.environment,
                criticality=payload.criticality,
                description=payload.description.strip(),
                created_by=actor,
                updated_by=actor,
            )
            value_problem = _validate_resource_values(resource)
            if value_problem:
                return value_problem
            resource.full_clean()
            resource.save()
            account = ProviderAccount(
                resource=resource,
                provider=provider,
                account_identifier=payload.account_identifier.strip(),
                tenant_id=payload.tenant_id.strip(),
                project_id=payload.project_id.strip(),
                portal_url=payload.portal_url.strip(),
                default_region=payload.default_region.strip(),
                support_plan=payload.support_plan.strip(),
                billing_reference=payload.billing_reference.strip(),
            )
            account.full_clean()
            account.save()
            AuditEvent.record(
                action="infrastructure.provider_account_created",
                actor=actor,
                target=resource,
                metadata={"provider_id": provider.id},
            )
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _account_detail(_account_queryset().get(id=account.id))


@provider_router.put(
    "/infrastructure/provider-accounts/{account_id}",
    response={
        200: ProviderAccountDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_provider_account(
    request: HttpRequest,
    account_id: int,
    payload: ProviderAccountUpdateIn,
) -> ProviderAccountDetailOut | StaffProblem:
    problem = _combined_permission_problem(
        request,
        ("infrastructure.change_provideraccount", "infrastructure.change_infrastructureresource"),
        "You do not have permission to change provider accounts.",
    )
    if problem:
        return problem
    account = _visible_accounts(request).filter(id=account_id).first()
    if account is None:
        return _problem(404, "Provider account not found.", "not_found")
    actor = cast(User, request.user)
    try:
        with transaction.atomic():
            resource = account.resource
            for field in ("name", "lifecycle_status", "environment", "criticality", "description"):
                value = getattr(payload, field)
                if value is not None:
                    setattr(resource, field, value.strip())
            value_problem = _validate_resource_values(resource)
            if value_problem:
                return value_problem
            resource.updated_by = actor
            resource.full_clean()
            resource.save()
            if payload.provider_id is not None:
                provider = _active_provider(payload.provider_id)
                if provider is None:
                    return _problem(
                        400, "Choose a valid active service provider.", "invalid_provider"
                    )
                account.provider = provider
            for field in (
                "account_identifier",
                "tenant_id",
                "project_id",
                "portal_url",
                "default_region",
                "support_plan",
                "billing_reference",
            ):
                value = getattr(payload, field)
                if value is not None:
                    setattr(account, field, value.strip())
            account.full_clean()
            account.save()
            AuditEvent.record(
                action="infrastructure.provider_account_updated",
                actor=actor,
                target=resource,
                metadata={"provider_id": account.provider_id},
            )
    except ValidationError as error:
        return _validation_problem(error)
    return _account_detail(_account_queryset().get(id=account.id))


@provider_router.post(
    "/infrastructure/provider-accounts/{account_id}/archive",
    response={
        200: ProviderAccountDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def archive_provider_account(
    request: HttpRequest,
    account_id: int,
) -> ProviderAccountDetailOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.delete_provideraccount",
        "You do not have permission to archive provider accounts.",
    )
    if problem:
        return problem
    account = _visible_accounts(request).filter(id=account_id).first()
    if account is None:
        return _problem(404, "Provider account not found.", "not_found")
    resource = account.resource
    resource.lifecycle_status = InfrastructureResource.LifecycleStatus.ARCHIVED
    resource.archived_at = timezone.now()
    resource.updated_by_id = request.user.pk
    resource.save(update_fields=["lifecycle_status", "archived_at", "updated_by", "updated_at"])
    AuditEvent.record(
        action="infrastructure.provider_account_archived", actor=request.user, target=resource
    )
    return _account_detail(_account_queryset().get(id=account.id))

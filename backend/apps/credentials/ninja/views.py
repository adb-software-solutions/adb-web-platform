from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, cast

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.text import slugify
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client
from apps.core.models import AuditEvent
from apps.core.ownership import OwnershipType
from apps.credentials.models import (
    CredentialResourceLink,
    CredentialType,
    StoredCredential,
    credential_field_schema,
)
from apps.credentials.policies import scope_credentials_for_user
from apps.credentials.secrets import (
    CredentialDecryptionError,
    CredentialEncryptionError,
    CredentialSecretFieldError,
    copy_credential_secret,
    download_credential_secret,
    merge_credential_secrets,
    migrate_legacy_plaintext_secrets,
    reveal_credential_secrets,
    store_credential_secrets,
)
from apps.infrastructure.models import InfrastructureResource
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .schemas import (
    CredentialClientOptionOut,
    CredentialCreateIn,
    CredentialDetailOut,
    CredentialFieldOut,
    CredentialLegacyMigrationOut,
    CredentialOptionsOut,
    CredentialOwnershipFilter,
    CredentialPageOut,
    CredentialResourceLinkIn,
    CredentialResourceLinkOut,
    CredentialResourceOptionOut,
    CredentialSecretRevealIn,
    CredentialSecretsOut,
    CredentialSecretValueOut,
    CredentialStatusFilter,
    CredentialSummaryOut,
    CredentialTypeOut,
    CredentialUpdateIn,
)

credential_router = Router(tags=["admin-credentials"])
StaffProblem = tuple[int, dict[str, object]]
CURRENT_RESOURCE_STATUSES = (
    InfrastructureResource.LifecycleStatus.PLANNED,
    InfrastructureResource.LifecycleStatus.ACTIVE,
    InfrastructureResource.LifecycleStatus.MAINTENANCE,
    InfrastructureResource.LifecycleStatus.DEPRECATED,
)
LEGACY_PLAINTEXT_FIELDS = ("password", "api_key", "secret_key", "private_key", "notes")
ALLOWED_FIELD_KINDS = {"text", "password", "textarea", "url"}
ALLOWED_FIELD_STORAGE = {"username", "url", "metadata", "secret"}


class CredentialPayloadError(ValueError):
    """The submitted dynamic credential field payload is invalid."""


def _staff_problem(request: HttpRequest) -> StaffProblem | None:
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
    return None


def _permission_problem(
    request: HttpRequest,
    permission: str,
    message: str,
) -> StaffProblem | None:
    problem = _staff_problem(request)
    if problem:
        return problem
    if not request.user.has_perm(permission):
        return 403, {
            "message": message,
            "success": False,
            "code": "forbidden",
        }
    return None


def _not_found() -> StaffProblem:
    return 404, {
        "message": "Credential not found.",
        "success": False,
        "code": "not_found",
    }


def _credential_queryset() -> QuerySet[StoredCredential]:
    return StoredCredential.objects.select_related(
        "client",
        "credential_type",
        "created_by",
        "updated_by",
    ).prefetch_related("resource_links__resource__client")


def _visible_credential(
    request: HttpRequest,
    credential_id: int,
) -> StoredCredential | None:
    return (
        scope_credentials_for_user(request.user, _credential_queryset())
        .filter(id=credential_id)
        .first()
    )


def _has_legacy_plaintext(credential: StoredCredential) -> bool:
    return any(bool(getattr(credential, field)) for field in LEGACY_PLAINTEXT_FIELDS)


def _field_rows(credential_type: CredentialType | None) -> list[CredentialFieldOut]:
    rows: list[CredentialFieldOut] = []
    for raw in credential_field_schema(credential_type):
        key = str(raw.get("key", "")).strip()
        label = str(raw.get("label", "")).strip()
        kind = str(raw.get("kind", "text")).strip()
        storage = str(raw.get("storage", "secret")).strip()
        if not key or not label:
            continue
        if kind not in ALLOWED_FIELD_KINDS:
            kind = "text"
        if storage not in ALLOWED_FIELD_STORAGE:
            storage = "secret"
        rows.append(
            CredentialFieldOut(
                key=key,
                label=label,
                kind=cast(Any, kind),
                storage=cast(Any, storage),
                required=bool(raw.get("required", False)),
            )
        )
    return rows


def _type_out(credential_type: CredentialType) -> CredentialTypeOut:
    return CredentialTypeOut(
        id=credential_type.id,
        slug=credential_type.slug,
        name=credential_type.name,
        icon=credential_type.icon,
        description=credential_type.description,
        fields=_field_rows(credential_type),
    )


def _resource_link_out(link: CredentialResourceLink) -> CredentialResourceLinkOut:
    resource = link.resource
    return CredentialResourceLinkOut(
        id=link.id,
        resource_id=resource.id,
        resource_name=resource.name,
        resource_type=resource.resource_type,
        ownership_type=resource.ownership_type,
        client_name=str(resource.client) if resource.client else None,
        purpose=link.purpose,
        is_primary=link.is_primary,
    )


def _summary(credential: StoredCredential) -> CredentialSummaryOut:
    links = list(credential.resource_links.all())
    credential_type = credential.credential_type
    return CredentialSummaryOut(
        id=credential.id,
        name=credential.name,
        status=credential.status,
        ownership_type=credential.ownership_type,
        client_id=credential.client_id,
        client_name=str(credential.client) if credential.client else None,
        credential_type_id=credential.credential_type_id,
        credential_type_slug=credential_type.slug if credential_type else None,
        credential_type_name=credential_type.name if credential_type else None,
        username=credential.username,
        url=credential.url,
        expires_at=credential.expires_at,
        last_rotated_at=credential.last_rotated_at,
        secret_field_keys=[
            str(key) for key in credential.secret_field_keys if isinstance(key, str)
        ],
        resource_count=len(links),
        has_legacy_plaintext=_has_legacy_plaintext(credential),
        updated_at=credential.updated_at,
    )


def _detail(credential: StoredCredential) -> CredentialDetailOut:
    summary = _summary(credential)
    metadata = {
        str(key): str(value)
        for key, value in credential.metadata.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }
    return CredentialDetailOut(
        **summary.model_dump(),
        description=credential.description,
        metadata=metadata,
        fields=_field_rows(credential.credential_type),
        resource_links=[_resource_link_out(link) for link in credential.resource_links.all()],
        created_by=credential.created_by.email if credential.created_by else None,
        updated_by=credential.updated_by.email if credential.updated_by else None,
        created_at=credential.created_at,
    )


def _resolve_client(
    request: HttpRequest,
    ownership_type: str,
    client_id: int | None,
) -> tuple[Client | None, StaffProblem | None]:
    if ownership_type == OwnershipType.INTERNAL:
        if client_id is not None:
            return None, (
                400,
                {
                    "message": "Internal credentials cannot have a client.",
                    "success": False,
                    "code": "invalid_ownership",
                },
            )
        return None, None

    if client_id is None:
        return None, (
            400,
            {
                "message": "Client-owned credentials require a client.",
                "success": False,
                "code": "invalid_ownership",
            },
        )
    client = scope_clients_for_user(request.user, Client.objects.all()).filter(id=client_id).first()
    if client is None:
        return None, (
            404,
            {
                "message": "Client not found.",
                "success": False,
                "code": "not_found",
            },
        )
    return client, None


def _split_create_values(
    credential_type: CredentialType,
    values: dict[str, str],
) -> tuple[str, str, dict[str, str], dict[str, str]]:
    fields = {field.key: field for field in _field_rows(credential_type)}
    unknown = set(values).difference(fields)
    if unknown:
        raise CredentialPayloadError(f"Unknown credential field: {min(unknown)}")

    username = ""
    url = ""
    metadata: dict[str, str] = {}
    secrets: dict[str, str] = {}
    for key, field in fields.items():
        value = values.get(key, "")
        if field.required and not value:
            raise CredentialPayloadError(f"{field.label} is required.")
        if not value:
            continue
        if field.storage == "username":
            username = value.strip()
        elif field.storage == "url":
            url = value.strip()
        elif field.storage == "metadata":
            metadata[key] = value
        else:
            secrets[key] = value
    return username, url, metadata, secrets


def _apply_value_updates(
    credential: StoredCredential,
    values: dict[str, str],
    clear_secret_fields: Iterable[str],
) -> tuple[dict[str, str], list[str]]:
    fields = {field.key: field for field in _field_rows(credential.credential_type)}
    unknown = set(values).difference(fields)
    if unknown:
        raise CredentialPayloadError(f"Unknown credential field: {min(unknown)}")

    clear_fields = [field.strip() for field in clear_secret_fields if field.strip()]
    unknown_clear = set(clear_fields).difference(fields)
    if unknown_clear:
        raise CredentialPayloadError(f"Unknown credential field: {min(unknown_clear)}")

    metadata = dict(credential.metadata)
    secret_updates: dict[str, str] = {}
    for key, value in values.items():
        field = fields[key]
        if field.required and field.storage != "secret" and not value:
            raise CredentialPayloadError(f"{field.label} is required.")
        if field.storage == "username":
            credential.username = value.strip()
        elif field.storage == "url":
            credential.url = value.strip()
        elif field.storage == "metadata":
            if value:
                metadata[key] = value
            else:
                metadata.pop(key, None)
        elif value:
            secret_updates[key] = value

    for key in clear_fields:
        field = fields[key]
        if field.storage != "secret":
            raise CredentialPayloadError(f"{field.label} is not an encrypted secret field.")
        if field.required and key not in secret_updates:
            raise CredentialPayloadError(f"{field.label} cannot be cleared without replacement.")

    credential.metadata = metadata
    return secret_updates, clear_fields


def _validated_links(
    request: HttpRequest,
    credential: StoredCredential,
    link_inputs: list[CredentialResourceLinkIn],
    actor: User,
) -> list[CredentialResourceLink]:
    ids = [item.resource_id for item in link_inputs]
    if len(ids) != len(set(ids)):
        raise CredentialPayloadError("A resource can only be linked once per credential.")

    resources = {
        resource.id: resource
        for resource in scope_infrastructure_resources_for_user(
            request.user,
            InfrastructureResource.objects.select_related("client"),
        ).filter(id__in=ids)
    }
    if len(resources) != len(ids):
        raise CredentialPayloadError("One or more resource links are unavailable.")

    links: list[CredentialResourceLink] = []
    for item in link_inputs:
        link = CredentialResourceLink(
            credential=credential,
            resource=resources[item.resource_id],
            purpose=item.purpose.strip(),
            is_primary=item.is_primary,
            created_by=actor,
        )
        try:
            link.full_clean()
        except ValidationError as error:
            raise CredentialPayloadError(" ".join(error.messages)) from error
        links.append(link)
    return links


def _request_context(request: HttpRequest) -> tuple[str | None, str]:
    return request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")


def _secret_problem(error: Exception) -> StaffProblem:
    if isinstance(error, PermissionDenied):
        return 403, {
            "message": str(error),
            "success": False,
            "code": "forbidden",
        }
    if isinstance(error, CredentialSecretFieldError):
        return 404, {
            "message": str(error),
            "success": False,
            "code": "secret_field_not_found",
        }
    if isinstance(error, CredentialDecryptionError):
        return 409, {
            "message": str(error),
            "success": False,
            "code": "secret_unavailable",
        }
    return 503, {
        "message": "Credential encryption is unavailable.",
        "success": False,
        "code": "encryption_unavailable",
    }


@credential_router.get(
    "/credential-options",
    response={200: CredentialOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def credential_options(request: HttpRequest) -> CredentialOptionsOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        return problem

    clients = scope_clients_for_user(request.user, Client.objects.all()).filter(status="active")
    resources = scope_infrastructure_resources_for_user(
        request.user,
        InfrastructureResource.objects.select_related("client"),
    ).filter(lifecycle_status__in=CURRENT_RESOURCE_STATUSES)
    credential_types = CredentialType.objects.filter(is_active=True).order_by(
        "sort_order",
        "name",
    )

    return CredentialOptionsOut(
        types=[_type_out(credential_type) for credential_type in credential_types],
        clients=[
            CredentialClientOptionOut(id=client.id, name=str(client))
            for client in clients.order_by("company", "name", "id")
        ],
        resources=[
            CredentialResourceOptionOut(
                id=resource.id,
                name=resource.name,
                resource_type=resource.resource_type,
                ownership_type=resource.ownership_type,
                client_id=resource.client_id,
                client_name=str(resource.client) if resource.client else None,
            )
            for resource in resources.order_by("name", "id")[:500]
        ],
    )


@credential_router.get(
    "/credentials",
    response={200: CredentialPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def list_credentials(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    status: CredentialStatusFilter = "active",
    ownership: CredentialOwnershipFilter = "all",
    client_id: int | None = None,
    credential_type_id: int | None = None,
    resource_id: int | None = None,
    search: str | None = None,
) -> CredentialPageOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        return problem

    credentials = scope_credentials_for_user(request.user, _credential_queryset())
    if status != "all":
        credentials = credentials.filter(status=status)
    if ownership != "all":
        credentials = credentials.filter(ownership_type=ownership)
    if client_id is not None:
        credentials = credentials.filter(client_id=client_id)
    if credential_type_id is not None:
        credentials = credentials.filter(credential_type_id=credential_type_id)
    if resource_id is not None:
        credentials = credentials.filter(resource_links__resource_id=resource_id)
    if search:
        term = search.strip()
        if term:
            credentials = credentials.filter(
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(username__icontains=term)
                | Q(url__icontains=term)
                | Q(client__name__icontains=term)
                | Q(client__company__icontains=term)
                | Q(credential_type__name__icontains=term)
                | Q(resource_links__resource__name__icontains=term)
            ).distinct()

    credentials = credentials.order_by("name", "id")
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = credentials.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    items = credentials[start : start + page_size]
    return CredentialPageOut(
        items=[_summary(credential) for credential in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@credential_router.post(
    "/credentials",
    response={
        201: CredentialDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        503: ProblemDetail,
    },
)
def create_credential(
    request: HttpRequest,
    payload: CredentialCreateIn,
) -> tuple[int, CredentialDetailOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "credentials.add_storedcredential",
        "You do not have permission to create credentials.",
    )
    if problem:
        return problem
    actor = cast(User, request.user)

    credential_type = CredentialType.objects.filter(
        id=payload.credential_type_id,
        is_active=True,
    ).first()
    if credential_type is None:
        return 400, {
            "message": "Choose a valid active credential type.",
            "success": False,
            "code": "invalid_credential_type",
        }
    client, client_problem = _resolve_client(
        request,
        payload.ownership_type,
        payload.client_id,
    )
    if client_problem:
        return client_problem

    try:
        username, url, metadata, secrets = _split_create_values(
            credential_type,
            payload.values,
        )
    except CredentialPayloadError as error:
        return 400, {
            "message": str(error),
            "success": False,
            "code": "invalid_credential_fields",
        }

    try:
        with transaction.atomic():
            credential = StoredCredential(
                ownership_type=payload.ownership_type,
                client=client,
                name=payload.name.strip(),
                credential_type=credential_type,
                status=payload.status,
                description=payload.description.strip(),
                username=username,
                url=url,
                metadata=metadata,
                expires_at=payload.expires_at,
                created_by=actor,
                updated_by=actor,
            )
            credential.full_clean()
            credential.save()
            if secrets:
                store_credential_secrets(credential, secrets)
            links = _validated_links(request, credential, payload.resource_links, actor)
            CredentialResourceLink.objects.bulk_create(links)
            AuditEvent.record(
                action="credentials.created",
                actor=actor,
                target=credential,
                metadata={
                    "credential_type": credential_type.slug,
                    "resource_ids": [link.resource_id for link in links],
                },
            )
    except CredentialPayloadError as error:
        return 400, {
            "message": str(error),
            "success": False,
            "code": "invalid_resource_link",
        }
    except CredentialEncryptionError as error:
        return _secret_problem(error)
    except ValidationError as error:
        return 400, {
            "message": " ".join(error.messages),
            "success": False,
            "code": "invalid_credential",
        }

    refreshed = _visible_credential(request, credential.id)
    if refreshed is None:
        return _not_found()
    return 201, _detail(refreshed)


@credential_router.get(
    "/credentials/{credential_id}",
    response={
        200: CredentialDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_credential(
    request: HttpRequest,
    credential_id: int,
) -> CredentialDetailOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        return problem
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()
    return _detail(credential)


@credential_router.put(
    "/credentials/{credential_id}",
    response={
        200: CredentialDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        503: ProblemDetail,
    },
)
def update_credential(
    request: HttpRequest,
    credential_id: int,
    payload: CredentialUpdateIn,
) -> CredentialDetailOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.change_storedcredential",
        "You do not have permission to change credentials.",
    )
    if problem:
        return problem
    actor = cast(User, request.user)
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()

    try:
        with transaction.atomic():
            if payload.name is not None:
                credential.name = payload.name.strip()
            if payload.status is not None:
                credential.status = payload.status
            if payload.description is not None:
                credential.description = payload.description.strip()
            if payload.clear_expires_at:
                credential.expires_at = None
            elif payload.expires_at is not None:
                credential.expires_at = payload.expires_at

            secret_updates, clear_fields = _apply_value_updates(
                credential,
                payload.values,
                payload.clear_secret_fields,
            )
            credential.updated_by = actor
            credential.full_clean()
            credential.save()
            if secret_updates or clear_fields:
                merge_credential_secrets(
                    credential,
                    secret_updates,
                    clear_fields=clear_fields,
                )

            if payload.resource_links is not None:
                links = _validated_links(
                    request,
                    credential,
                    payload.resource_links,
                    actor,
                )
                credential.resource_links.all().delete()
                CredentialResourceLink.objects.bulk_create(links)

            AuditEvent.record(
                action="credentials.updated",
                actor=actor,
                target=credential,
                metadata={
                    "secret_fields_changed": sorted(secret_updates),
                    "secret_fields_cleared": sorted(clear_fields),
                    "resource_links_replaced": payload.resource_links is not None,
                },
            )
    except CredentialPayloadError as error:
        return 400, {
            "message": str(error),
            "success": False,
            "code": "invalid_credential_fields",
        }
    except CredentialEncryptionError as error:
        return _secret_problem(error)
    except ValidationError as error:
        return 400, {
            "message": " ".join(error.messages),
            "success": False,
            "code": "invalid_credential",
        }

    refreshed = _visible_credential(request, credential.id)
    if refreshed is None:
        return _not_found()
    return _detail(refreshed)


@credential_router.post(
    "/credentials/{credential_id}/archive",
    response={
        200: CredentialDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def archive_credential(
    request: HttpRequest,
    credential_id: int,
) -> CredentialDetailOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.delete_storedcredential",
        "You do not have permission to archive credentials.",
    )
    if problem:
        return problem
    actor = cast(User, request.user)
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()

    credential.status = StoredCredential.Status.ARCHIVED
    credential.updated_by = actor
    credential.save(update_fields=["status", "updated_by", "updated_at"])
    AuditEvent.record(action="credentials.archived", actor=actor, target=credential)
    return _detail(credential)


@credential_router.post(
    "/credentials/{credential_id}/reveal",
    response={
        200: CredentialSecretsOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        409: ProblemDetail,
        503: ProblemDetail,
    },
)
def reveal_credential(
    request: HttpRequest,
    credential_id: int,
    payload: CredentialSecretRevealIn,
) -> CredentialSecretsOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        return problem
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()
    ip_address, user_agent = _request_context(request)
    try:
        secrets = reveal_credential_secrets(
            credential,
            actor=request.user,
            fields=payload.fields or None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except (PermissionDenied, CredentialEncryptionError) as error:
        return _secret_problem(error)
    return CredentialSecretsOut(fields=secrets)


@credential_router.post(
    "/credentials/{credential_id}/secrets/{field_key}/copy",
    response={
        200: CredentialSecretValueOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        409: ProblemDetail,
        503: ProblemDetail,
    },
)
def copy_credential_field(
    request: HttpRequest,
    credential_id: int,
    field_key: str,
) -> CredentialSecretValueOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        return problem
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()
    ip_address, user_agent = _request_context(request)
    try:
        value = copy_credential_secret(
            credential,
            field_key,
            actor=request.user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except (PermissionDenied, CredentialEncryptionError) as error:
        return _secret_problem(error)
    return CredentialSecretValueOut(field_key=field_key, value=value)


@credential_router.post("/credentials/{credential_id}/secrets/{field_key}/download")
def download_credential_field(
    request: HttpRequest,
    credential_id: int,
    field_key: str,
) -> HttpResponse:
    problem = _permission_problem(
        request,
        "credentials.view_storedcredential",
        "You do not have permission to view credentials.",
    )
    if problem:
        status, payload = problem
        return JsonResponse(payload, status=status)
    credential = _visible_credential(request, credential_id)
    if credential is None:
        status, payload = _not_found()
        return JsonResponse(payload, status=status)

    ip_address, user_agent = _request_context(request)
    try:
        value = download_credential_secret(
            credential,
            field_key,
            actor=request.user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except (PermissionDenied, CredentialEncryptionError) as error:
        status, payload = _secret_problem(error)
        return JsonResponse(payload, status=status)

    extension = {
        "private_key": ".pem",
        "certificate": ".pem",
        "service_account_json": ".json",
    }.get(field_key, ".txt")
    credential_slug = slugify(credential.name) or "credential"
    field_slug = slugify(field_key) or "secret"
    filename = f"{credential_slug}-{field_slug}{extension}"
    response = HttpResponse(
        value.encode("utf-8"),
        content_type="application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@credential_router.post(
    "/credentials/{credential_id}/migrate-legacy-secrets",
    response={
        200: CredentialLegacyMigrationOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
        503: ProblemDetail,
    },
)
def migrate_credential_legacy_secrets(
    request: HttpRequest,
    credential_id: int,
) -> CredentialLegacyMigrationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "credentials.change_storedcredential",
        "You do not have permission to change credentials.",
    )
    if problem:
        return problem
    credential = _visible_credential(request, credential_id)
    if credential is None:
        return _not_found()
    ip_address, user_agent = _request_context(request)
    try:
        migrated = migrate_legacy_plaintext_secrets(
            credential,
            actor=request.user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except (PermissionDenied, CredentialEncryptionError) as error:
        return _secret_problem(error)
    return CredentialLegacyMigrationOut(migrated_fields=migrated)

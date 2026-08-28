from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.core.models import AuditEvent
from apps.credentials.health import evaluate_credential_health
from apps.credentials.models import StoredCredential
from apps.credentials.policies import scope_credentials_for_user
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .lifecycle_schemas import (
    CredentialHealthListOut,
    CredentialHealthOut,
    CredentialLifecycleUpdateIn,
)

credential_lifecycle_router = Router(tags=["admin-credential-lifecycle"])
StaffProblem = tuple[int, dict[str, Any]]


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _permission_problem(request: HttpRequest, permission: str) -> StaffProblem | None:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(403, "Staff access required.", "forbidden")
    if not request.user.has_perm(permission):
        return _problem(403, "You do not have permission for this action.", "forbidden")
    return None


def _visible_credentials(request: HttpRequest) -> QuerySet[StoredCredential]:
    return scope_credentials_for_user(request.user).select_related("client", "credential_type")


def _health_out(credential: StoredCredential) -> CredentialHealthOut:
    health = evaluate_credential_health(credential)
    return CredentialHealthOut(
        credential_id=credential.id,
        name=credential.name,
        status=credential.status,
        client_id=credential.client_id,
        client_name=str(credential.client) if credential.client else None,
        expires_at=credential.expires_at,
        expires_in_days=health.expires_in_days,
        last_rotated_at=credential.last_rotated_at,
        rotation_interval_days=credential.rotation_interval_days,
        rotation_due_at=health.rotation_due_at,
        rotation_due_in_days=health.rotation_due_in_days,
        health_status=health.status,
        health_severity=health.severity,
        href=f"/admin/credentials/{credential.id}",
    )


@credential_lifecycle_router.get(
    "/credential-health",
    response={200: CredentialHealthListOut, 401: ProblemDetail, 403: ProblemDetail},
)
def credential_health_list(
    request: HttpRequest,
    client_id: int | None = None,
    include_inactive: bool = False,
) -> CredentialHealthListOut | StaffProblem:
    problem = _permission_problem(request, "credentials.view_storedcredential")
    if problem:
        return problem
    credentials = _visible_credentials(request)
    if not include_inactive:
        credentials = credentials.filter(status=StoredCredential.Status.ACTIVE)
    if client_id is not None:
        credentials = credentials.filter(client_id=client_id)
    items = [_health_out(item) for item in credentials.order_by("name", "id")[:500]]
    return CredentialHealthListOut(
        items=items,
        healthy_count=sum(item.health_severity == "info" for item in items),
        warning_count=sum(item.health_severity == "warning" for item in items),
        critical_count=sum(item.health_severity == "critical" for item in items),
    )


@credential_lifecycle_router.get(
    "/credentials/{credential_id}/health",
    response={
        200: CredentialHealthOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def credential_health_detail(
    request: HttpRequest,
    credential_id: int,
) -> CredentialHealthOut | StaffProblem:
    problem = _permission_problem(request, "credentials.view_storedcredential")
    if problem:
        return problem
    credential = _visible_credentials(request).filter(id=credential_id).first()
    if credential is None:
        return _problem(404, "Credential not found.", "not_found")
    return _health_out(credential)


@credential_lifecycle_router.put(
    "/credentials/{credential_id}/lifecycle",
    response={
        200: CredentialHealthOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_credential_lifecycle(
    request: HttpRequest,
    credential_id: int,
    payload: CredentialLifecycleUpdateIn,
) -> CredentialHealthOut | StaffProblem:
    problem = _permission_problem(request, "credentials.change_storedcredential")
    if problem:
        return problem
    credential = _visible_credentials(request).filter(id=credential_id).first()
    if credential is None:
        return _problem(404, "Credential not found.", "not_found")

    changed_fields: list[str] = []
    if payload.clear_rotation_interval:
        credential.rotation_interval_days = None
        changed_fields.append("rotation_interval_days")
    elif payload.rotation_interval_days is not None:
        credential.rotation_interval_days = payload.rotation_interval_days
        changed_fields.append("rotation_interval_days")
    if payload.mark_rotated:
        credential.last_rotated_at = timezone.now()
        changed_fields.append("last_rotated_at")
    if changed_fields:
        credential.updated_by = cast(User, request.user)
        credential.save(update_fields=[*changed_fields, "updated_by", "updated_at"])
        AuditEvent.record(
            action="credentials.lifecycle_updated",
            actor=request.user,
            target=credential,
            metadata={
                "rotation_interval_days": credential.rotation_interval_days,
                "marked_rotated": payload.mark_rotated,
            },
        )
    return _health_out(credential)

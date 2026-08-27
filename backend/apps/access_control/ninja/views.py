from __future__ import annotations

from math import ceil
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.access_control.models import StaffAccessProfile
from apps.access_control.services import (
    StaffAccessWrite,
    assignable_groups_queryset,
    assignable_permissions_queryset,
    invite_staff_user,
    is_sensitive_permission,
    permission_code,
    resend_staff_invitation,
    set_staff_active,
    update_staff_access,
)
from apps.clients.models import Client
from apps.ticketing.models import TicketQueue
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .schemas import (
    CapabilityOptionOut,
    ClientAccessOptionOut,
    EffectiveCapabilityOut,
    GroupOptionOut,
    ObjectAccessScopeOut,
    StaffAccessDetailOut,
    StaffAccessOptionsOut,
    StaffAccessUpdateIn,
    StaffInviteIn,
    StaffInviteOut,
    StaffStatusOut,
    StaffUserDetailOut,
    StaffUserListOut,
    StaffUserSummaryOut,
    TicketQueueAccessOptionOut,
)

staff_access_router = Router(tags=["admin-staff-access"])
StaffProblem = tuple[int, dict[str, Any]]
MANAGE_PERMISSION = "access_control.manage_staff_access"


def _access_problem(request: HttpRequest) -> StaffProblem | None:
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
    if not request.user.has_perm(MANAGE_PERMISSION):
        return 403, {
            "message": "You do not have permission to manage staff access.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _actor(request: HttpRequest) -> User:
    return cast(User, request.user)


def _validation_problem(error: ValidationError) -> StaffProblem:
    return 400, {
        "message": "; ".join(error.messages) or "Invalid staff access configuration.",
        "success": False,
        "code": "validation_error",
    }


def _not_found_problem() -> StaffProblem:
    return 404, {
        "message": "Staff user not found.",
        "success": False,
        "code": "not_found",
    }


def _request_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def _staff_queryset() -> QuerySet[User]:
    return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).distinct()


def _get_staff_user(user_id: str) -> User | None:
    try:
        return _staff_queryset().filter(pk=user_id).first()
    except (ValidationError, ValueError):
        return None


def _summary(user: User) -> StaffUserSummaryOut:
    return StaffUserSummaryOut(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_staff=user.is_staff,
        is_superuser=user.is_superuser,
        email_verified=user.email_verified,
        setup_pending=not user.has_usable_password(),
        date_joined=user.date_joined,
        last_login=user.last_login,
        group_names=list(user.groups.order_by("name").values_list("name", flat=True)),
    )


def _effective_permissions(user: User) -> list[EffectiveCapabilityOut]:
    permissions = list(assignable_permissions_queryset())
    by_code = {permission_code(permission): permission for permission in permissions}
    effective_codes = (
        set(by_code) if user.is_superuser else set(user.get_all_permissions()) & set(by_code)
    )
    direct_codes = {
        permission_code(permission)
        for permission in user.user_permissions.select_related("content_type").all()
    }
    group_sources: dict[str, list[str]] = {}
    for group in user.groups.prefetch_related("permissions__content_type").order_by("name"):
        for permission in group.permissions.all():
            code = permission_code(permission)
            if code in by_code:
                group_sources.setdefault(code, []).append(group.name)

    result: list[EffectiveCapabilityOut] = []
    for code in sorted(effective_codes):
        permission = by_code[code]
        if user.is_superuser:
            sources = ["Superuser"]
        else:
            sources = (["Direct"] if code in direct_codes else []) + [
                f"Group: {name}" for name in group_sources.get(code, [])
            ]
        result.append(
            EffectiveCapabilityOut(
                code=code,
                name=permission.name,
                sensitive=is_sensitive_permission(code),
                sources=sources,
            )
        )
    return result


def _detail(actor: User, user: User) -> StaffUserDetailOut:
    try:
        profile = user.access_profile
    except StaffAccessProfile.DoesNotExist:
        profile = None

    direct_permission_ids = set(assignable_permissions_queryset().values_list("id", flat=True))
    selected_direct_ids = list(
        user.user_permissions.filter(id__in=direct_permission_ids)
        .order_by("id")
        .values_list("id", flat=True)
    )
    client_scope = ObjectAccessScopeOut()
    queue_scope = ObjectAccessScopeOut()
    default_queue_ids: list[int] = []
    if user.is_superuser:
        client_scope = ObjectAccessScopeOut(all=True, ids=[])
        queue_scope = ObjectAccessScopeOut(all=True, ids=[])
    elif profile is not None:
        client_scope = ObjectAccessScopeOut(
            all=profile.all_clients,
            ids=[]
            if profile.all_clients
            else list(
                profile.client_grants.order_by("client_id").values_list("client_id", flat=True)
            ),
        )
        queue_scope = ObjectAccessScopeOut(
            all=profile.all_ticket_queues,
            ids=[]
            if profile.all_ticket_queues
            else list(
                profile.ticket_queue_grants.order_by("queue_id").values_list("queue_id", flat=True)
            ),
        )
        default_queue_ids = list(
            profile.default_ticket_queues.order_by("id").values_list("id", flat=True)
        )

    summary = _summary(user)
    return StaffUserDetailOut(
        **summary.model_dump(),
        access=StaffAccessDetailOut(
            group_ids=list(user.groups.order_by("id").values_list("id", flat=True)),
            direct_permission_ids=selected_direct_ids,
            effective_permissions=_effective_permissions(user),
            clients=client_scope,
            ticket_queues=queue_scope,
            default_ticket_queue_ids=default_queue_ids,
        ),
        can_manage=actor.is_superuser or (not user.is_superuser and actor.pk != user.pk),
    )


def _write(payload: StaffAccessUpdateIn) -> StaffAccessWrite:
    return StaffAccessWrite(
        group_ids=payload.group_ids,
        direct_permission_ids=payload.direct_permission_ids,
        all_clients=payload.all_clients,
        client_ids=payload.client_ids,
        all_ticket_queues=payload.all_ticket_queues,
        ticket_queue_ids=payload.ticket_queue_ids,
        default_ticket_queue_ids=payload.default_ticket_queue_ids,
    )


@staff_access_router.get(
    "/access/users",
    response={
        200: StaffUserListOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def list_staff_users(
    request: HttpRequest,
    q: str = "",
    status: str = "active",
    page: int = 1,
    page_size: int = 25,
) -> tuple[int, StaffUserListOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    base = _staff_queryset()
    active_count = base.filter(is_active=True).count()
    inactive_count = base.filter(is_active=False).count()
    queryset = base
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif status != "all":
        return 400, {
            "message": "Status must be active, inactive or all.",
            "success": False,
            "code": "validation_error",
        }
    if q.strip():
        search = q.strip()
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    queryset = queryset.prefetch_related("groups").order_by("first_name", "last_name", "email")
    total = queryset.count()
    start = (page - 1) * page_size
    items = [_summary(user) for user in queryset[start : start + page_size]]
    return 200, StaffUserListOut(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=max(1, ceil(total / page_size)) if total else 0,
        active_count=active_count,
        inactive_count=inactive_count,
    )


@staff_access_router.get(
    "/access/options",
    response={200: StaffAccessOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def staff_access_options(
    request: HttpRequest,
) -> tuple[int, StaffAccessOptionsOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem

    assignable_ids = set(assignable_permissions_queryset().values_list("id", flat=True))
    groups = [
        GroupOptionOut(
            id=group.id,
            name=group.name,
            permission_ids=list(
                group.permissions.filter(id__in=assignable_ids)
                .order_by("id")
                .values_list("id", flat=True)
            ),
        )
        for group in assignable_groups_queryset().prefetch_related("permissions")
    ]
    capabilities = [
        CapabilityOptionOut(
            id=permission.id,
            code=permission_code(permission),
            name=permission.name,
            app_label=permission.content_type.app_label,
            model=permission.content_type.model,
            sensitive=is_sensitive_permission(permission_code(permission)),
        )
        for permission in assignable_permissions_queryset()
    ]
    clients = [
        ClientAccessOptionOut(
            id=client.id,
            name=client.name,
            company=client.company,
            status=client.status,
        )
        for client in Client.objects.order_by("company", "name")
    ]
    queues = [
        TicketQueueAccessOptionOut(
            id=queue.id,
            name=queue.name,
            key=queue.key,
            brand_name=queue.brand.name if queue.brand else None,
            enabled=queue.enabled,
        )
        for queue in TicketQueue.objects.select_related("brand").order_by("ordering", "name")
    ]
    return 200, StaffAccessOptionsOut(
        groups=groups,
        capabilities=capabilities,
        clients=clients,
        ticket_queues=queues,
    )


@staff_access_router.post(
    "/access/users/invite",
    response={
        201: StaffInviteOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def invite_staff(
    request: HttpRequest,
    payload: StaffInviteIn,
) -> tuple[int, StaffInviteOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem
    actor = _actor(request)
    try:
        user, email_sent = invite_staff_user(
            actor=actor,
            email=str(payload.email),
            first_name=payload.first_name,
            last_name=payload.last_name,
            write=_write(payload),
            ip_address=_request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except ValidationError as error:
        return _validation_problem(error)
    return 201, StaffInviteOut(
        user=_detail(actor, user),
        invitation_email_sent=email_sent,
    )


@staff_access_router.get(
    "/access/users/{user_id}",
    response={
        200: StaffUserDetailOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def get_staff_user(
    request: HttpRequest,
    user_id: str,
) -> tuple[int, StaffUserDetailOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem
    user = _get_staff_user(user_id)
    if user is None:
        return _not_found_problem()
    return 200, _detail(_actor(request), user)


@staff_access_router.put(
    "/access/users/{user_id}/access",
    response={
        200: StaffUserDetailOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def change_staff_access(
    request: HttpRequest,
    user_id: str,
    payload: StaffAccessUpdateIn,
) -> tuple[int, StaffUserDetailOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem
    user = _get_staff_user(user_id)
    if user is None:
        return _not_found_problem()
    actor = _actor(request)
    try:
        update_staff_access(
            actor=actor,
            target=user,
            write=_write(payload),
            ip_address=_request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except ValidationError as error:
        return _validation_problem(error)
    refreshed = User.objects.get(pk=user.pk)
    return 200, _detail(actor, refreshed)


def _change_status(
    request: HttpRequest,
    user_id: str,
    is_active: bool,
) -> tuple[int, StaffStatusOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem
    user = _get_staff_user(user_id)
    if user is None:
        return _not_found_problem()
    actor = _actor(request)
    try:
        set_staff_active(
            actor=actor,
            target=user,
            is_active=is_active,
            ip_address=_request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except ValidationError as error:
        return _validation_problem(error)
    refreshed = User.objects.get(pk=user.pk)
    return 200, StaffStatusOut(
        user=_detail(actor, refreshed),
        message="Staff account activated." if is_active else "Staff account deactivated.",
    )


@staff_access_router.post(
    "/access/users/{user_id}/activate",
    response={
        200: StaffStatusOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def activate_staff(
    request: HttpRequest,
    user_id: str,
) -> tuple[int, StaffStatusOut | dict[str, Any]]:
    return _change_status(request, user_id, True)


@staff_access_router.post(
    "/access/users/{user_id}/deactivate",
    response={
        200: StaffStatusOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def deactivate_staff(
    request: HttpRequest,
    user_id: str,
) -> tuple[int, StaffStatusOut | dict[str, Any]]:
    return _change_status(request, user_id, False)


@staff_access_router.post(
    "/access/users/{user_id}/resend-invitation",
    response={
        200: StaffInviteOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def resend_invitation(
    request: HttpRequest,
    user_id: str,
) -> tuple[int, StaffInviteOut | dict[str, Any]]:
    problem = _access_problem(request)
    if problem:
        return problem
    user = _get_staff_user(user_id)
    if user is None:
        return _not_found_problem()
    actor = _actor(request)
    try:
        email_sent = resend_staff_invitation(
            actor=actor,
            target=user,
            ip_address=_request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except ValidationError as error:
        return _validation_problem(error)
    refreshed = User.objects.get(pk=user.pk)
    return 200, StaffInviteOut(
        user=_detail(actor, refreshed),
        invitation_email_sent=email_sent,
    )

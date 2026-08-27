from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from apps.core.dashboard import build_dashboard_workspace, save_dashboard_layout
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .schemas import DashboardPreferencesIn, DashboardWorkspaceOut


dashboard_router = Router(tags=["admin-dashboard"])
StaffProblem = tuple[int, dict[str, Any]]


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


def _request_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


@dashboard_router.get(
    "/dashboard",
    response={200: DashboardWorkspaceOut, 401: ProblemDetail, 403: ProblemDetail},
)
def dashboard_workspace(request: HttpRequest) -> DashboardWorkspaceOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    return build_dashboard_workspace(cast(User, request.user))


@dashboard_router.put(
    "/dashboard/preferences",
    response={
        200: DashboardWorkspaceOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def update_dashboard_preferences(
    request: HttpRequest,
    payload: DashboardPreferencesIn,
) -> DashboardWorkspaceOut | StaffProblem:
    problem = _staff_problem(request)
    if problem:
        return problem
    user = cast(User, request.user)
    try:
        save_dashboard_layout(
            user=user,
            layout=[item.model_dump() for item in payload.layout],
            ip_address=_request_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except ValidationError as error:
        return 400, {
            "message": "; ".join(error.messages),
            "success": False,
            "code": "validation_error",
        }
    return build_dashboard_workspace(user)

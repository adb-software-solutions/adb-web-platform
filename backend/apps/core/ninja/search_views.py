from typing import Any, cast

from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from apps.clients.models import Client
from apps.core.operational_search import search_operational_records
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .search_schemas import OperationalSearchOut

operational_search_router = Router(tags=["admin-operational-search"])
StaffProblem = tuple[int, dict[str, Any]]


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _resolve_client(user: User, client_id: int | None) -> Client | None:
    if client_id is None:
        return None
    if not user.has_perm("clients.view_client"):
        return None
    return scope_clients_for_user(user).filter(id=client_id).first()


@operational_search_router.get(
    "/search",
    response={
        200: OperationalSearchOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def operational_search(
    request: HttpRequest,
    q: str,
    client_id: int | None = None,
    per_type: int = 5,
) -> OperationalSearchOut | StaffProblem:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(
            403,
            "You do not have permission to access operational search.",
            "forbidden",
        )

    query = q.strip()
    if len(query) < 2:
        return _problem(
            400,
            "Search queries must contain at least two characters.",
            "query_too_short",
        )
    if len(query) > 160:
        return _problem(
            400,
            "Search queries may contain at most 160 characters.",
            "query_too_long",
        )

    user = cast(User, request.user)
    client = _resolve_client(user, client_id)
    if client_id is not None and client is None:
        return _problem(404, "Client not found.", "not_found")

    groups = search_operational_records(
        user=user,
        query=query,
        client=client,
        per_type=per_type,
    )
    return OperationalSearchOut(
        query=query,
        client_id=client.id if client else None,
        client_name=str(client) if client else None,
        total_results=sum(len(group.results) for group in groups),
        groups=groups,
    )

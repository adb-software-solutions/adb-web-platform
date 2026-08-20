import math
from typing import Any

from django.db.models import Count, Q
from django.http import HttpRequest
from ninja import Router

from apps.access_control.policies import scope_clients_for_user
from authentication.ninja.schemas import ProblemDetail

from .overview_schemas import ClientOverviewItemOut, ClientOverviewOut, ClientOverviewStatsOut

client_overview_router = Router(tags=["admin-client-overview"])
StaffProblem = tuple[int, dict[str, Any]]


def _permission_problem(request: HttpRequest) -> StaffProblem | None:
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
    if not request.user.has_perm("clients.view_client"):
        return 403, {
            "message": "You do not have permission to view clients.",
            "success": False,
            "code": "forbidden",
        }
    return None


@client_overview_router.get(
    "/client-overview",
    response={200: ClientOverviewOut, 401: ProblemDetail, 403: ProblemDetail},
)
def client_overview(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    status: str | None = None,
    search: str | None = None,
) -> ClientOverviewOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    base = scope_clients_for_user(request.user)
    aggregate = base.aggregate(
        total=Count("id", distinct=True),
        active=Count("id", filter=Q(status="active"), distinct=True),
        inactive=Count("id", filter=Q(status="inactive"), distinct=True),
        archived=Count("id", filter=Q(status="archived"), distinct=True),
        contacts=Count("contacts", distinct=True),
        projects=Count("projects", distinct=True),
    )
    stats = ClientOverviewStatsOut(**aggregate)

    clients = base.annotate(
        contact_count=Count("contacts", distinct=True),
        project_count=Count("projects", distinct=True),
        active_project_count=Count(
            "projects",
            filter=Q(projects__status__in=("planning", "active", "paused")),
            distinct=True,
        ),
    )
    if status in {"active", "inactive", "archived"}:
        clients = clients.filter(status=status)
    if search:
        term = search.strip()
        if term:
            clients = clients.filter(
                Q(name__icontains=term)
                | Q(company__icontains=term)
                | Q(email__icontains=term)
                | Q(contacts__name__icontains=term)
                | Q(contacts__email__icontains=term)
            ).distinct()

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = clients.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    rows = clients.order_by("company", "name")[start : start + page_size]

    return ClientOverviewOut(
        items=[
            ClientOverviewItemOut(
                id=client.id,
                name=client.name,
                company=client.company,
                email=client.email,
                status=client.status,
                contact_count=client.contact_count,
                project_count=client.project_count,
                active_project_count=client.active_project_count,
            )
            for client in rows
        ],
        stats=stats,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )

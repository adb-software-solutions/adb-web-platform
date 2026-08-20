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
CLIENT_STATUSES = {"active", "inactive", "archived"}
CURRENT_PROJECT_STATUSES = ("planning", "active", "paused")


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

    selected_status = status if status in CLIENT_STATUSES or status == "all" else "active"
    base = scope_clients_for_user(request.user)
    scoped = base if selected_status == "all" else base.filter(status=selected_status)
    aggregate = scoped.aggregate(
        total_clients=Count("id", distinct=True),
        active_clients=Count("id", filter=Q(status="active"), distinct=True),
        inactive_clients=Count("id", filter=Q(status="inactive"), distinct=True),
        archived_clients=Count("id", filter=Q(status="archived"), distinct=True),
        active_contacts=Count("contacts", filter=Q(contacts__is_active=True), distinct=True),
        project_records=Count("projects", distinct=True),
        current_projects=Count(
            "projects",
            filter=Q(projects__status__in=CURRENT_PROJECT_STATUSES),
            distinct=True,
        ),
    )
    stats = ClientOverviewStatsOut(
        total=aggregate["total_clients"],
        active=aggregate["active_clients"],
        inactive=aggregate["inactive_clients"],
        archived=aggregate["archived_clients"],
        contacts=aggregate["active_contacts"],
        projects=aggregate["project_records"],
        active_projects=aggregate["current_projects"],
    )

    clients = scoped.annotate(
        contact_count=Count("contacts", filter=Q(contacts__is_active=True), distinct=True),
        project_count=Count("projects", distinct=True),
        active_project_count=Count(
            "projects",
            filter=Q(projects__status__in=CURRENT_PROJECT_STATUSES),
            distinct=True,
        ),
    )
    if search:
        term = search.strip()
        if term:
            clients = clients.filter(
                Q(name__icontains=term)
                | Q(company__icontains=term)
                | Q(email__icontains=term)
                | Q(contacts__name__icontains=term, contacts__is_active=True)
                | Q(contacts__email__icontains=term, contacts__is_active=True)
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

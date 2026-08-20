import math
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.db.models import Count, Q
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.crm.models import Lead
from authentication.ninja.schemas import ProblemDetail

from .overview_schemas import LeadOverviewItemOut, LeadOverviewOut, LeadOverviewStatsOut

lead_overview_router = Router(tags=["admin-lead-overview"])
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
    if not request.user.has_perm("crm.view_lead"):
        return 403, {
            "message": "You do not have permission to view leads.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _lead_queryset():
    return Lead.objects.select_related("brand", "status", "source", "assigned_to")


def _user_label(user: Any | None) -> str | None:
    if user is None:
        return None
    return user.get_full_name().strip() or user.email


@lead_overview_router.get(
    "/lead-overview",
    response={200: LeadOverviewOut, 401: ProblemDetail, 403: ProblemDetail},
)
def lead_overview(
    request: HttpRequest,
    page: int = 1,
    page_size: int = 25,
    status_id: int | None = None,
    source_id: int | None = None,
    brand_id: int | None = None,
    assigned_to_id: UUID | None = None,
    converted: bool | None = None,
    search: str | None = None,
) -> LeadOverviewOut | StaffProblem:
    problem = _permission_problem(request)
    if problem:
        return problem

    base = _lead_queryset()
    cutoff = timezone.now() - timedelta(days=30)
    aggregate = base.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(converted_at__isnull=True)),
        converted=Count("id", filter=Q(converted_at__isnull=False)),
        unassigned=Count(
            "id",
            filter=Q(converted_at__isnull=True, assigned_to__isnull=True),
        ),
        new_last_30_days=Count("id", filter=Q(created_at__gte=cutoff)),
    )
    stats = LeadOverviewStatsOut(**aggregate)

    leads = base
    if status_id is not None:
        leads = leads.filter(status_id=status_id)
    if source_id is not None:
        leads = leads.filter(source_id=source_id)
    if brand_id is not None:
        leads = leads.filter(brand_id=brand_id)
    if assigned_to_id is not None:
        leads = leads.filter(assigned_to_id=assigned_to_id)
    if converted is not None:
        leads = leads.filter(converted_at__isnull=not converted)
    if search:
        term = search.strip()
        if term:
            leads = leads.filter(
                Q(name__icontains=term)
                | Q(company__icontains=term)
                | Q(email__icontains=term)
                | Q(message__icontains=term)
            )

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = leads.count()
    total_pages = math.ceil(total / page_size) if total else 0
    start = (page - 1) * page_size
    rows = leads.order_by("-created_at")[start : start + page_size]

    return LeadOverviewOut(
        items=[
            LeadOverviewItemOut(
                id=lead.id,
                name=lead.name,
                company=lead.company,
                email=lead.email,
                status=lead.status.name if lead.status else "Unassigned",
                source=lead.source.name if lead.source else "Unknown",
                brand=lead.brand.name if lead.brand else "Unassigned",
                assigned_to_name=_user_label(lead.assigned_to),
                converted_at=lead.converted_at,
                created_at=lead.created_at,
            )
            for lead in rows
        ],
        stats=stats,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )

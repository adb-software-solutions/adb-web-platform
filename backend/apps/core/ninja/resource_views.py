from datetime import datetime
from typing import Any

from django.db.models import Q
from django.http import HttpRequest
from ninja import Router, Schema

from apps.access_control.policies import scope_clients_for_user
from apps.core.ownership import OwnershipType
from apps.knowledge_base.models import KnowledgeBaseDocument
from authentication.ninja.schemas import ProblemDetail

resource_admin_router = Router(tags=["admin-resources"])

StaffProblem = tuple[int, dict[str, Any]]


class KnowledgeDocumentSummaryOut(Schema):
    id: int
    title: str
    ownership_type: str
    client: str | None
    section: str
    is_portal_visible: bool
    updated_at: datetime
    version_count: int


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


def _permission_problem(request: HttpRequest, permission: str) -> StaffProblem | None:
    staff_problem = _staff_problem(request)
    if staff_problem:
        return staff_problem
    if not request.user.has_perm(permission):
        return 403, {
            "message": "You do not have permission to access this resource.",
            "success": False,
            "code": "forbidden",
        }
    return None


def _ownership_scope(request: HttpRequest) -> Q:
    clients = scope_clients_for_user(request.user)
    return Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients)


@resource_admin_router.get(
    "/knowledge-base",
    response={
        200: list[KnowledgeDocumentSummaryOut],
        401: ProblemDetail,
        403: ProblemDetail,
    },
)
def list_knowledge_documents(
    request: HttpRequest,
) -> list[KnowledgeDocumentSummaryOut] | StaffProblem:
    problem = _permission_problem(request, "knowledge_base.view_knowledgebasedocument")
    if problem:
        return problem

    documents = (
        KnowledgeBaseDocument.objects.filter(_ownership_scope(request))
        .select_related("client", "section")
        .prefetch_related("versions")
    )
    return [
        KnowledgeDocumentSummaryOut(
            id=document.id,
            title=document.title,
            ownership_type=document.ownership_type,
            client=document.client.company if document.client else None,
            section=document.section.name,
            is_portal_visible=document.is_portal_visible,
            updated_at=document.updated_at,
            version_count=document.versions.count(),
        )
        for document in documents
    ]

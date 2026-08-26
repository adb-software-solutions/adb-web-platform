from __future__ import annotations

from typing import Any, cast

from django.db.models import Q, QuerySet
from django.http import FileResponse, HttpRequest, JsonResponse
from ninja import File, Router
from ninja.files import UploadedFile

from apps.access_control.policies import scope_clients_for_user
from apps.core.ownership import OwnershipType
from apps.knowledge_base.attachment_security import (
    attachment_is_downloadable,
    delete_attachment,
    quarantine_attachment,
)
from apps.knowledge_base.models import KnowledgeBaseAttachment, KnowledgeBaseDocument
from authentication.models import User

knowledge_attachment_router = Router(tags=["admin-knowledge-base-attachments"])


def _problem(status: int, message: str, code: str) -> JsonResponse:
    return JsonResponse(
        {"message": message, "success": False, "code": code},
        status=status,
    )


def _staff_problem(user: Any, *permissions: str) -> JsonResponse | None:
    if not user.is_authenticated:
        return _problem(401, "Authentication required.", "not_authenticated")
    if not (user.is_staff or user.is_superuser):
        return _problem(403, "Staff access required.", "permission_denied")
    if not all(user.has_perm(permission) for permission in permissions):
        return _problem(403, "You do not have permission for this action.", "permission_denied")
    return None


def _visible_documents(user: Any) -> QuerySet[KnowledgeBaseDocument]:
    clients = scope_clients_for_user(user)
    return KnowledgeBaseDocument.objects.filter(
        Q(ownership_type=OwnershipType.INTERNAL)
        | Q(ownership_type=OwnershipType.CLIENT, client__in=clients)
    )


def _visible_attachment(user: Any, attachment_id: int) -> KnowledgeBaseAttachment | None:
    return (
        KnowledgeBaseAttachment.objects.select_related("document", "document__client")
        .filter(id=attachment_id, document__in=_visible_documents(user))
        .first()
    )


def _attachment_payload(attachment: KnowledgeBaseAttachment) -> dict[str, object]:
    return {
        "id": attachment.id,
        "original_name": attachment.original_name,
        "content_type": attachment.content_type,
        "detected_content_type": attachment.detected_content_type,
        "size_bytes": attachment.size_bytes,
        "scan_status": attachment.scan_status,
        "created_at": attachment.created_at.isoformat(),
    }


@knowledge_attachment_router.post("/knowledge-base/documents/{document_id}/attachments")
def upload_knowledge_attachment(
    request: HttpRequest,
    document_id: int,
    file: File[UploadedFile],
) -> JsonResponse:
    problem = _staff_problem(
        request.user,
        "knowledge_base.change_knowledgebasedocument",
        "knowledge_base.add_knowledgebaseattachment",
    )
    if problem:
        return problem
    document = _visible_documents(request.user).filter(id=document_id).first()
    if document is None:
        return _problem(404, "Knowledge Base document not found.", "not_found")
    if document.archived_at is not None:
        return _problem(
            409,
            "Archived Knowledge Base documents cannot receive attachments.",
            "document_archived",
        )

    try:
        attachment = quarantine_attachment(
            document=document,
            upload=file,
            uploader=cast(User, request.user),
        )
    except ValueError as exc:
        return _problem(400, str(exc), "attachment_policy_error")
    return JsonResponse(_attachment_payload(attachment), status=201)


@knowledge_attachment_router.get("/knowledge-base/attachments/{attachment_id}/download")
def download_knowledge_attachment(
    request: HttpRequest,
    attachment_id: int,
) -> FileResponse | JsonResponse:
    problem = _staff_problem(
        request.user,
        "knowledge_base.view_knowledgebasedocument",
        "knowledge_base.view_knowledgebaseattachment",
    )
    if problem:
        return problem
    attachment = _visible_attachment(request.user, attachment_id)
    if attachment is None:
        return _problem(404, "Knowledge Base attachment not found.", "not_found")
    if not attachment_is_downloadable(attachment):
        return _problem(
            409,
            "Attachment is not available under the current malware-scanning policy.",
            "attachment_not_safe",
        )
    if not attachment.file.name or not attachment.file.storage.exists(attachment.file.name):
        return _problem(404, "Attachment content is unavailable.", "content_not_found")

    file_handle = attachment.file.storage.open(attachment.file.name, "rb")
    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=attachment.original_name,
        content_type=attachment.detected_content_type or "application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@knowledge_attachment_router.delete("/knowledge-base/attachments/{attachment_id}")
def delete_knowledge_attachment(
    request: HttpRequest,
    attachment_id: int,
) -> JsonResponse:
    problem = _staff_problem(
        request.user,
        "knowledge_base.change_knowledgebasedocument",
        "knowledge_base.delete_knowledgebaseattachment",
    )
    if problem:
        return problem
    attachment = _visible_attachment(request.user, attachment_id)
    if attachment is None:
        return _problem(404, "Knowledge Base attachment not found.", "not_found")
    delete_attachment(attachment.id)
    return JsonResponse({"success": True})

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from authentication.models import User

from .models import DocumentVersion, KnowledgeBaseDocument, KnowledgeBaseSection


@dataclass(frozen=True)
class DocumentWrite:
    ownership_type: str
    client_id: int | None
    title: str
    summary: str
    section: KnowledgeBaseSection
    content: str
    is_portal_visible: bool = False
    change_summary: str = ""


def _validate_write(write: DocumentWrite) -> None:
    if (
        write.section.ownership_type != write.ownership_type
        or write.section.client_id != write.client_id
    ):
        raise ValidationError(
            {"section": "Knowledge Base documents and sections must use the same ownership scope."}
        )


def _create_version(
    document: KnowledgeBaseDocument,
    *,
    editor: User | None,
    change_summary: str = "",
) -> DocumentVersion:
    latest = (
        DocumentVersion.objects.filter(document=document).aggregate(latest=Max("version_number"))[
            "latest"
        ]
        or 0
    )
    return DocumentVersion.objects.create(
        document=document,
        version_number=latest + 1,
        title=document.title,
        content=document.content,
        section_path=document.section.path,
        change_summary=change_summary[:500],
        editor=editor,
    )


@transaction.atomic
def create_document(
    *,
    write: DocumentWrite,
    editor: User | None,
) -> KnowledgeBaseDocument:
    _validate_write(write)
    document = KnowledgeBaseDocument(
        ownership_type=write.ownership_type,
        client_id=write.client_id,
        title=write.title.strip(),
        summary=write.summary.strip(),
        section=write.section,
        content=write.content,
        is_portal_visible=write.is_portal_visible,
        created_by=editor,
        updated_by=editor,
    )
    document.full_clean()
    document.save()
    _create_version(
        document,
        editor=editor,
        change_summary=write.change_summary or "Initial version",
    )
    return document


@transaction.atomic
def update_document(
    document_id: int,
    *,
    write: DocumentWrite,
    editor: User | None,
) -> KnowledgeBaseDocument:
    document = (
        KnowledgeBaseDocument.objects.select_for_update()
        .select_related("section")
        .get(id=document_id)
    )
    if document.archived_at is not None:
        raise ValidationError("Restore an archived Knowledge Base document before editing it.")
    _validate_write(write)
    if document.ownership_type != write.ownership_type or document.client_id != write.client_id:
        raise ValidationError(
            "Moving a Knowledge Base document between ownership scopes requires an explicit migration."
        )

    versioned_fields_changed = any(
        [
            document.title != write.title.strip(),
            document.content != write.content,
            document.section_id != write.section.id,
        ]
    )
    metadata_changed = any(
        [
            document.summary != write.summary.strip(),
            document.is_portal_visible != write.is_portal_visible,
        ]
    )

    document.title = write.title.strip()
    document.summary = write.summary.strip()
    document.section = write.section
    document.content = write.content
    document.is_portal_visible = write.is_portal_visible
    document.updated_by = editor
    document.full_clean()

    if versioned_fields_changed or metadata_changed:
        document.save()
    if versioned_fields_changed:
        _create_version(document, editor=editor, change_summary=write.change_summary)
    return document


@transaction.atomic
def archive_document(
    document_id: int,
    *,
    editor: User | None,
) -> KnowledgeBaseDocument:
    document = KnowledgeBaseDocument.objects.select_for_update().get(id=document_id)
    if document.archived_at is None:
        document.archived_at = timezone.now()
        document.updated_by = editor
        document.save(update_fields=["archived_at", "updated_by", "updated_at"])
    return document


@transaction.atomic
def restore_document(
    document_id: int,
    *,
    editor: User | None,
) -> KnowledgeBaseDocument:
    document = KnowledgeBaseDocument.objects.select_for_update().get(id=document_id)
    if document.archived_at is not None:
        document.archived_at = None
        document.updated_by = editor
        document.save(update_fields=["archived_at", "updated_by", "updated_at"])
    return document

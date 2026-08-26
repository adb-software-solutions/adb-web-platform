from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from authentication.models import User

from .models import KnowledgeBaseAttachment, KnowledgeBaseDocument

DEFAULT_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ ()\-]+")


def sanitise_attachment_filename(filename: str) -> str:
    """Return a storage/display-safe basename without trusting client path data."""
    name = Path(filename).name.strip()
    name = _SAFE_FILENAME_RE.sub("_", name).strip(". ")
    return name[:180] or "attachment"


def detect_attachment_content_type(upload: UploadedFile) -> str:
    """Perform small signature-based MIME detection without trusting the declaration."""
    position = upload.tell()
    head = upload.read(16)
    upload.seek(position)
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head.startswith(b"PK\x03\x04"):
        return "application/zip"
    return "application/octet-stream"


def attachment_is_downloadable(attachment: KnowledgeBaseAttachment) -> bool:
    """Apply the platform attachment safety policy before returning file bytes."""
    from apps.ticketing.config import malware_scanning_enabled

    if attachment.scan_status == KnowledgeBaseAttachment.ScanStatus.SAFE and attachment.safe_at:
        return True
    if attachment.scan_status in {
        KnowledgeBaseAttachment.ScanStatus.BLOCKED,
        KnowledgeBaseAttachment.ScanStatus.INFECTED,
        KnowledgeBaseAttachment.ScanStatus.SCANNING,
    }:
        return False
    if malware_scanning_enabled():
        return False
    return attachment.scan_status in {
        KnowledgeBaseAttachment.ScanStatus.PENDING,
        KnowledgeBaseAttachment.ScanStatus.FAILED,
    }


@transaction.atomic
def quarantine_attachment(
    *,
    document: KnowledgeBaseDocument,
    upload: UploadedFile,
    uploader: User,
) -> KnowledgeBaseAttachment:
    """Persist a policy-checked attachment in quarantine pending any configured scan."""
    if document.archived_at is not None:
        raise ValueError("Archived Knowledge Base documents cannot receive attachments.")

    size = upload.size or 0
    if size > DEFAULT_MAX_ATTACHMENT_BYTES:
        raise ValueError("Knowledge Base attachments are limited to 25 MB.")

    original_name = sanitise_attachment_filename(upload.name or "attachment")
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    detected_content_type = detect_attachment_content_type(upload)
    upload.seek(0)

    attachment = KnowledgeBaseAttachment(
        document=document,
        original_name=original_name,
        content_type=(upload.content_type or "")[:120],
        detected_content_type=detected_content_type,
        size_bytes=size,
        sha256=digest.hexdigest(),
        scan_status=KnowledgeBaseAttachment.ScanStatus.PENDING,
        quarantined_at=timezone.now(),
        uploaded_by=uploader,
    )
    attachment.file.save(original_name, upload, save=False)
    try:
        attachment.full_clean()
        attachment.save()
    except Exception:
        if attachment.file.name:
            attachment.file.storage.delete(attachment.file.name)
        raise

    from apps.ticketing.config import malware_scanning_enabled

    if malware_scanning_enabled():
        from .tasks import scan_knowledge_base_attachment

        transaction.on_commit(lambda: scan_knowledge_base_attachment.delay(attachment.id))
    return attachment


@transaction.atomic
def delete_attachment(attachment_id: int) -> bool:
    attachment = (
        KnowledgeBaseAttachment.objects.select_for_update().filter(id=attachment_id).first()
    )
    if attachment is None:
        return False
    storage = attachment.file.storage
    storage_name = attachment.file.name
    attachment.delete()
    if storage_name:
        transaction.on_commit(lambda: storage.delete(storage_name))
    return True

from __future__ import annotations

from typing import BinaryIO, cast

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.ticketing.config import malware_scanning_enabled
from apps.ticketing.services.scanning import AttachmentScanError, clamav_scanner_from_environment

from .models import KnowledgeBaseAttachment


@shared_task(name="knowledge_base.enqueue_attachment_scans")
def enqueue_attachment_scans() -> int:
    """Backfill any quarantined KB attachments that still need a scan."""
    if not malware_scanning_enabled():
        return 0
    attachment_ids = list(
        KnowledgeBaseAttachment.objects.filter(
            scan_status=KnowledgeBaseAttachment.ScanStatus.PENDING
        )
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:100]
    )
    for attachment_id in attachment_ids:
        scan_knowledge_base_attachment.delay(attachment_id)
    return len(attachment_ids)


@shared_task(name="knowledge_base.scan_attachment")
def scan_knowledge_base_attachment(attachment_id: int) -> None:
    """Scan one quarantined KB attachment and persist only its verdict metadata."""
    if not malware_scanning_enabled():
        return

    with transaction.atomic():
        attachment = (
            KnowledgeBaseAttachment.objects.select_for_update().filter(id=attachment_id).first()
        )
        if (
            attachment is None
            or attachment.scan_status != KnowledgeBaseAttachment.ScanStatus.PENDING
        ):
            return
        attachment.scan_status = KnowledgeBaseAttachment.ScanStatus.SCANNING
        attachment.scan_engine = "clamav"
        attachment.scan_result = ""
        attachment.save(update_fields=["scan_status", "scan_engine", "scan_result"])

    try:
        scanner = clamav_scanner_from_environment()
        attachment = KnowledgeBaseAttachment.objects.get(id=attachment_id)
        with attachment.file.open("rb") as stream:
            result = scanner.scan(cast(BinaryIO, stream))
    except (
        AttachmentScanError,
        OSError,
        ValueError,
        KnowledgeBaseAttachment.DoesNotExist,
    ) as exc:
        KnowledgeBaseAttachment.objects.filter(id=attachment_id).update(
            scan_status=KnowledgeBaseAttachment.ScanStatus.FAILED,
            scan_engine="clamav",
            scan_result=str(exc)[:255],
            scanned_at=timezone.now(),
            safe_at=None,
        )
        return

    scanned_at = timezone.now()
    if result.clean:
        KnowledgeBaseAttachment.objects.filter(id=attachment_id).update(
            scan_status=KnowledgeBaseAttachment.ScanStatus.SAFE,
            scan_engine=scanner.engine_name,
            scan_result="Clean",
            scanned_at=scanned_at,
            safe_at=scanned_at,
        )
        return

    KnowledgeBaseAttachment.objects.filter(id=attachment_id).update(
        scan_status=KnowledgeBaseAttachment.ScanStatus.INFECTED,
        scan_engine=scanner.engine_name,
        scan_result=(result.signature or "Malware detected")[:255],
        scanned_at=scanned_at,
        safe_at=None,
    )

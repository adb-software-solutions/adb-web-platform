from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.ownership import OwnershipType, ownership_constraint, validate_ownership


def knowledge_attachment_upload_to(instance: KnowledgeBaseAttachment, filename: str) -> str:
    safe_name = Path(filename).name[:180] or "attachment"
    return (
        f"knowledge-base/quarantine/{instance.document_id or 'pending'}/{uuid4().hex}-{safe_name}"
    )


def _validate_same_owner(
    *,
    document: KnowledgeBaseDocument,
    ownership_type: str,
    client_id: int | None,
    field_name: str,
) -> None:
    if document.ownership_type != ownership_type or document.client_id != client_id:
        raise ValidationError(
            {field_name: "Knowledge Base links must remain inside the document ownership scope."}
        )


class KnowledgeBaseSection(models.Model):
    """Scoped hierarchical folder/section node for Knowledge Base navigation."""

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="knowledge_base_sections",
        null=True,
        blank=True,
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name", "id"]
        constraints = [ownership_constraint("knowledge_section_valid_ownership")]
        indexes = [
            models.Index(
                fields=["ownership_type", "client", "parent", "order"],
                name="kb_section_scope_tree_idx",
            )
        ]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)
        if self.parent_id is None:
            return
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({"parent": "A Knowledge Base section cannot contain itself."})

        parent = self.parent
        if parent is None:
            return
        if parent.ownership_type != self.ownership_type or parent.client_id != self.client_id:
            raise ValidationError(
                {"parent": "Nested Knowledge Base sections must use the same ownership scope."}
            )

        ancestor: KnowledgeBaseSection | None = parent
        visited: set[int] = set()
        while ancestor is not None and ancestor.pk is not None:
            if ancestor.pk in visited or (self.pk and ancestor.pk == self.pk):
                raise ValidationError({"parent": "Knowledge Base section cycles are not allowed."})
            visited.add(ancestor.pk)
            ancestor = ancestor.parent

    @property
    def path(self) -> str:
        parts = [self.name]
        ancestor = self.parent
        visited: set[int] = set()
        while ancestor is not None and ancestor.pk not in visited:
            if ancestor.pk is not None:
                visited.add(ancestor.pk)
            parts.append(ancestor.name)
            ancestor = ancestor.parent
        return " / ".join(reversed(parts))

    def __str__(self) -> str:
        return self.path


class KnowledgeBaseTag(models.Model):
    """Reusable non-secret discovery metadata for Knowledge Base documents."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class KnowledgeBaseDocument(models.Model):
    """Client-owned or internal private Markdown documentation page."""

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="knowledge_base_documents",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    section = models.ForeignKey(
        KnowledgeBaseSection,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    content = models.TextField(help_text="Markdown content")
    tags = models.ManyToManyField(
        KnowledgeBaseTag,
        related_name="documents",
        blank=True,
    )
    is_portal_visible = models.BooleanField(
        default=False,
        help_text="Reserved for future client-portal visibility. Private by default.",
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_documents_created",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_documents_updated",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [ownership_constraint("knowledge_document_valid_ownership")]
        indexes = [
            models.Index(
                fields=["ownership_type", "client", "archived_at"],
                name="kb_document_scope_state_idx",
            )
        ]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)
        if self.section_id and (
            self.section.ownership_type != self.ownership_type
            or self.section.client_id != self.client_id
        ):
            raise ValidationError(
                {
                    "section": "Knowledge Base documents and sections must use the same ownership scope."
                }
            )

    def __str__(self) -> str:
        return self.title


class DocumentVersion(models.Model):
    """Immutable historical snapshot of a Knowledge Base document."""

    document = models.ForeignKey(
        KnowledgeBaseDocument,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    content = models.TextField()
    section_path = models.CharField(max_length=500, blank=True)
    change_summary = models.CharField(max_length=500, blank=True)
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_versions",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_document_version_number",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Knowledge Base document versions are immutable.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.document} - v{self.version_number}"


class KnowledgeBaseResourceLink(models.Model):
    """Attach documentation to a structured Infrastructure Resource."""

    document = models.ForeignKey(
        KnowledgeBaseDocument,
        on_delete=models.CASCADE,
        related_name="resource_links",
    )
    resource = models.ForeignKey(
        "infrastructure.InfrastructureResource",
        on_delete=models.CASCADE,
        related_name="knowledge_base_links",
    )
    purpose = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_resource_links_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document__title", "resource__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "resource"],
                name="unique_knowledge_document_resource_link",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.resource_id:
            _validate_same_owner(
                document=self.document,
                ownership_type=self.resource.ownership_type,
                client_id=self.resource.client_id,
                field_name="resource",
            )

    def __str__(self) -> str:
        return f"{self.document} → {self.resource}"


class KnowledgeBaseCredentialLink(models.Model):
    """Attach safe Credential Vault metadata to documentation without secret duplication."""

    document = models.ForeignKey(
        KnowledgeBaseDocument,
        on_delete=models.CASCADE,
        related_name="credential_links",
    )
    credential = models.ForeignKey(
        "credentials.StoredCredential",
        on_delete=models.CASCADE,
        related_name="knowledge_base_links",
    )
    purpose = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_credential_links_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document__title", "credential__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "credential"],
                name="unique_knowledge_document_credential_link",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.document_id and self.credential_id:
            _validate_same_owner(
                document=self.document,
                ownership_type=self.credential.ownership_type,
                client_id=self.credential.client_id,
                field_name="credential",
            )

    def __str__(self) -> str:
        return f"{self.document} → {self.credential}"


class KnowledgeBaseAttachment(models.Model):
    """Quarantined private attachment linked to a Knowledge Base document."""

    class ScanStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SCANNING = "scanning", "Scanning"
        SAFE = "safe", "Safe"
        INFECTED = "infected", "Infected"
        FAILED = "failed", "Scan failed"
        BLOCKED = "blocked", "Blocked by policy"

    document = models.ForeignKey(
        KnowledgeBaseDocument,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to=knowledge_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    detected_content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    scan_status = models.CharField(
        max_length=20,
        choices=ScanStatus.choices,
        default=ScanStatus.PENDING,
    )
    scan_engine = models.CharField(max_length=80, blank=True)
    scan_result = models.CharField(max_length=255, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    safe_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="knowledge_base_attachments_uploaded",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["original_name", "id"]
        indexes = [models.Index(fields=["scan_status", "created_at"], name="kb_attach_scan_idx")]

    def __str__(self) -> str:
        return self.original_name

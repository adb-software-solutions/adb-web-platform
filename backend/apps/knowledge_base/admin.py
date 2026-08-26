from django.contrib import admin
from django.http import HttpRequest

from .models import (
    DocumentVersion,
    KnowledgeBaseAttachment,
    KnowledgeBaseCredentialLink,
    KnowledgeBaseDocument,
    KnowledgeBaseResourceLink,
    KnowledgeBaseSection,
    KnowledgeBaseTag,
)


@admin.register(KnowledgeBaseSection)
class KnowledgeBaseSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "ownership_type", "client", "parent", "order")
    list_filter = ("ownership_type",)
    search_fields = ("name", "description", "client__company")
    raw_id_fields = ("client", "parent")


@admin.register(KnowledgeBaseTag)
class KnowledgeBaseTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(KnowledgeBaseDocument)
class KnowledgeBaseDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "ownership_type",
        "client",
        "section",
        "archived_at",
        "created_at",
        "updated_at",
    )
    list_filter = ("ownership_type", "archived_at", "section", "created_at")
    search_fields = ("title", "summary", "content", "client__company")
    raw_id_fields = ("client", "section", "created_by", "updated_by")
    filter_horizontal = ("tags",)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version_number", "editor", "created_at")
    list_filter = ("created_at",)
    search_fields = ("document__title", "title", "change_summary")
    raw_id_fields = ("document", "editor")
    readonly_fields = (
        "document",
        "version_number",
        "title",
        "content",
        "section_path",
        "change_summary",
        "editor",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: DocumentVersion | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: DocumentVersion | None = None,
    ) -> bool:
        return False


@admin.register(KnowledgeBaseResourceLink)
class KnowledgeBaseResourceLinkAdmin(admin.ModelAdmin):
    list_display = ("document", "resource", "purpose", "created_at")
    raw_id_fields = ("document", "resource", "created_by")


@admin.register(KnowledgeBaseCredentialLink)
class KnowledgeBaseCredentialLinkAdmin(admin.ModelAdmin):
    list_display = ("document", "credential", "purpose", "created_at")
    raw_id_fields = ("document", "credential", "created_by")


@admin.register(KnowledgeBaseAttachment)
class KnowledgeBaseAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "document", "size_bytes", "content_type", "created_at")
    search_fields = ("original_name", "document__title")
    raw_id_fields = ("document", "uploaded_by")

from typing import Any

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import apps.knowledge_base.models


def scope_existing_sections_and_versions(apps: Any, schema_editor: Any) -> None:
    Section = apps.get_model("knowledge_base", "KnowledgeBaseSection")
    Document = apps.get_model("knowledge_base", "KnowledgeBaseDocument")
    Version = apps.get_model("knowledge_base", "DocumentVersion")

    for section in Section.objects.all().iterator():
        client_ids = list(
            Document.objects.filter(
                section_id=section.id,
                ownership_type="client",
                client_id__isnull=False,
            )
            .values_list("client_id", flat=True)
            .distinct()
        )
        for client_id in client_ids:
            scoped_section = Section.objects.create(
                ownership_type="client",
                client_id=client_id,
                name=section.name,
                description=section.description,
                order=section.order,
            )
            Document.objects.filter(
                section_id=section.id,
                ownership_type="client",
                client_id=client_id,
            ).update(section_id=scoped_section.id)

    for version in Version.objects.select_related("document__section").all().iterator():
        version.title = version.document.title
        version.section_path = version.document.section.name
        version.save(update_fields=["title", "section_path"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clients", "0004_timeentry_billable_default"),
        ("credentials", "0006_alter_storedcredential_credential_type"),
        ("infrastructure", "0007_web_domain_primary_constraints"),
        ("knowledge_base", "0002_document_ownership"),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeBaseTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddField(
            model_name="knowledgebasesection",
            name="ownership_type",
            field=models.CharField(
                choices=[("internal", "Internal"), ("client", "Client")],
                default="internal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="knowledgebasesection",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="knowledge_base_sections",
                to="clients.client",
            ),
        ),
        migrations.AddField(
            model_name="knowledgebasesection",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="knowledge_base.knowledgebasesection",
            ),
        ),
        migrations.AlterModelOptions(
            name="knowledgebasesection",
            options={"ordering": ["order", "name", "id"]},
        ),
        migrations.AlterField(
            model_name="knowledgebasedocument",
            name="section",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="documents",
                to="knowledge_base.knowledgebasesection",
            ),
        ),
        migrations.AddField(
            model_name="knowledgebasedocument",
            name="summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="knowledgebasedocument",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgebasedocument",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                related_name="documents",
                to="knowledge_base.knowledgebasetag",
            ),
        ),
        migrations.AlterModelOptions(
            name="knowledgebasedocument",
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AlterField(
            model_name="documentversion",
            name="version_number",
            field=models.PositiveIntegerField(),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="title",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="documentversion",
            name="section_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="documentversion",
            name="change_summary",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterModelOptions(
            name="documentversion",
            options={"ordering": ["-version_number", "-id"]},
        ),
        migrations.CreateModel(
            name="KnowledgeBaseAttachment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to=apps.knowledge_base.models.knowledge_attachment_upload_to
                    ),
                ),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="knowledge_base.knowledgebasedocument",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="knowledge_base_attachments_uploaded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["original_name", "id"]},
        ),
        migrations.CreateModel(
            name="KnowledgeBaseCredentialLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("purpose", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="knowledge_base_links",
                        to="credentials.storedcredential",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="knowledge_base_credential_links_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credential_links",
                        to="knowledge_base.knowledgebasedocument",
                    ),
                ),
            ],
            options={"ordering": ["document__title", "credential__name", "id"]},
        ),
        migrations.CreateModel(
            name="KnowledgeBaseResourceLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("purpose", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="knowledge_base_resource_links_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resource_links",
                        to="knowledge_base.knowledgebasedocument",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="knowledge_base_links",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["document__title", "resource__name", "id"]},
        ),
        migrations.RunPython(scope_existing_sections_and_versions, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="knowledgebasesection",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("client__isnull", True), ("ownership_type", "internal"))
                    | models.Q(("client__isnull", False), ("ownership_type", "client"))
                ),
                name="knowledge_section_valid_ownership",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgebasesection",
            index=models.Index(
                fields=["ownership_type", "client", "parent", "order"],
                name="kb_section_scope_tree_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="knowledgebasedocument",
            index=models.Index(
                fields=["ownership_type", "client", "archived_at"],
                name="kb_document_scope_state_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgebasecredentiallink",
            constraint=models.UniqueConstraint(
                fields=("document", "credential"),
                name="unique_knowledge_document_credential_link",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgebaseresourcelink",
            constraint=models.UniqueConstraint(
                fields=("document", "resource"),
                name="unique_knowledge_document_resource_link",
            ),
        ),
    ]

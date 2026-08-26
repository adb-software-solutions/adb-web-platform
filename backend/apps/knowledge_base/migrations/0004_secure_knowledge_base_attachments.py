from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def block_legacy_attachments(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    attachment_model = apps.get_model("knowledge_base", "KnowledgeBaseAttachment")
    attachment_model.objects.update(
        scan_status="blocked",
        scan_result="Legacy attachment requires re-upload under quarantine policy.",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge_base", "0003_knowledge_base_workspace_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="detected_content_type",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="quarantined_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="safe_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="scan_engine",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="scan_result",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="scan_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("scanning", "Scanning"),
                    ("safe", "Safe"),
                    ("infected", "Infected"),
                    ("failed", "Scan failed"),
                    ("blocked", "Blocked by policy"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="scanned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgebaseattachment",
            name="sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RunPython(block_legacy_attachments, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="knowledgebaseattachment",
            index=models.Index(
                fields=["scan_status", "created_at"],
                name="kb_attach_scan_idx",
            ),
        ),
    ]

from django.apps.registry import Apps
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def classify_terminal_statuses(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    lead_status = apps.get_model("crm", "LeadStatus")
    lead_status.objects.filter(name__iexact="Won").update(outcome="won")
    lead_status.objects.filter(name__iexact="Lost").update(outcome="lost")


def reset_status_outcomes(
    apps: Apps,
    _schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    lead_status = apps.get_model("crm", "LeadStatus")
    lead_status.objects.update(outcome="open")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0003_lead_assignment_conversion"),
    ]

    operations = [
        migrations.AddField(
            model_name="leadstatus",
            name="outcome",
            field=models.CharField(
                choices=[("open", "Open"), ("won", "Won"), ("lost", "Lost")],
                db_index=True,
                default="open",
                max_length=12,
            ),
        ),
        migrations.RunPython(classify_terminal_statuses, reset_status_outcomes),
    ]

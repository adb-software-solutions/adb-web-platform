# Generated manually for the task recurrence workflow.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0002_operational_tasks"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="previous_occurrence",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="next_occurrence",
                to="tasks.task",
            ),
        ),
    ]

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clients", "0002_operational_ownership"),
        ("tasks", "0003_task_recurrence_history"),
        ("ticketing", "0005_vendor_routing"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timeentry",
            name="duration_hours",
            field=models.DecimalField(
                decimal_places=4,
                help_text="Hours worked",
                max_digits=7,
            ),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="entry_type",
            field=models.CharField(
                choices=[("manual", "Manual"), ("timer", "Timer")],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="task",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="time_entries",
                to="tasks.task",
            ),
        ),
        migrations.AddField(
            model_name="timeentry",
            name="ticket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="time_entries",
                to="ticketing.ticket",
            ),
        ),
        migrations.CreateModel(
            name="RunningTimer",
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
                    "ownership_type",
                    models.CharField(
                        choices=[("internal", "Internal"), ("client", "Client")],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("description", models.TextField(blank=True)),
                ("billable", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="running_timers",
                        to="clients.client",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="running_timers",
                        to="clients.project",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="running_timers",
                        to="tasks.task",
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="running_timers",
                        to="ticketing.ticket",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="running_timer",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["started_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="runningtimer",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(ownership_type="internal", client__isnull=True)
                    | models.Q(ownership_type="client", client__isnull=False)
                ),
                name="runningtimer_valid_ownership",
            ),
        ),
    ]

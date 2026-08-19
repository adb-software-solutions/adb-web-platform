import decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0003_task_recurrence_history"),
    ]

    operations = [
        migrations.AddField(
            model_name="tasklist",
            name="sort_order",
            field=models.DecimalField(
                decimal_places=10,
                default=decimal.Decimal(1000),
                max_digits=20,
            ),
        ),
        migrations.CreateModel(
            name="TaskSection",
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
                ("name", models.CharField(max_length=200)),
                (
                    "sort_order",
                    models.DecimalField(
                        decimal_places=10,
                        default=decimal.Decimal(1000),
                        max_digits=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "task_list",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="tasks.tasklist",
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.AddField(
            model_name="task",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="sort_order",
            field=models.DecimalField(
                decimal_places=10,
                default=decimal.Decimal(1000),
                max_digits=20,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="parent_task",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subtasks",
                to="tasks.task",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="tasks.tasksection",
            ),
        ),
        migrations.CreateModel(
            name="TaskDependency",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "blocked_task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependency_links",
                        to="tasks.task",
                    ),
                ),
                (
                    "blocking_task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blocking_links",
                        to="tasks.task",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="taskdependency",
            constraint=models.UniqueConstraint(
                fields=("blocked_task", "blocking_task"),
                name="taskdependency_unique_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskdependency",
            constraint=models.CheckConstraint(
                condition=~models.Q(blocked_task=models.F("blocking_task")),
                name="taskdependency_no_self_reference",
            ),
        ),
    ]

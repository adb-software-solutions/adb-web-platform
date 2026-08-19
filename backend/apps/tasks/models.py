from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.ownership import OwnershipType, ownership_constraint, validate_ownership


class TaskStatus(models.Model):
    """Task status options."""

    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default="#808080", help_text="Hex color code")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Task Statuses"

    def __str__(self) -> str:
        return self.name


class TaskList(models.Model):
    """A first-class list of client-owned or internal tasks."""

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="task_lists",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        "clients.Project",
        on_delete=models.CASCADE,
        related_name="task_lists",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.DecimalField(max_digits=20, decimal_places=10, default=Decimal(1000))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [ownership_constraint("tasklist_valid_ownership")]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)
        if self.project_id and self.project:
            if self.project.ownership_type != self.ownership_type:
                raise ValidationError(
                    {"project": "Task-list ownership must match the selected project."}
                )
            if self.project.client_id != self.client_id:
                raise ValidationError(
                    {"client": "Task-list client must match the selected project."}
                )

    def __str__(self) -> str:
        return self.name


class TaskSection(models.Model):
    """Ordered section within a task list, shared by list and board views."""

    task_list = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=200)
    sort_order = models.DecimalField(max_digits=20, decimal_places=10, default=Decimal(1000))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.task_list}: {self.name}"


class Task(models.Model):
    """Standalone, client-owned or project-linked operational task."""

    PRIORITY_CHOICES = [
        (1, "Low"),
        (2, "Medium"),
        (3, "High"),
        (4, "Critical"),
    ]

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        "clients.Project",
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Markdown content")

    task_list = models.ForeignKey(
        TaskList,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    section = models.ForeignKey(
        TaskSection,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="subtasks",
        null=True,
        blank=True,
    )
    status = models.ForeignKey(
        TaskStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    start_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    sort_order = models.DecimalField(max_digits=20, decimal_places=10, default=Decimal(1000))
    recurrence_rule = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional iCalendar RRULE for recurring tasks.",
    )
    next_occurrence_at = models.DateTimeField(blank=True, null=True)
    previous_occurrence = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        related_name="next_occurrence",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(blank=True, null=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_tasks",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [ownership_constraint("task_valid_ownership")]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)

        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValidationError({"start_date": "Task start date cannot be after its due date."})

        if self.project_id and self.project:
            if self.project.ownership_type != self.ownership_type:
                raise ValidationError(
                    {"project": "Task ownership must match the selected project."}
                )
            if self.project.client_id != self.client_id:
                raise ValidationError({"client": "Task client must match the selected project."})

        if self.task_list_id and self.task_list:
            if self.task_list.ownership_type != self.ownership_type:
                raise ValidationError(
                    {"task_list": "Task ownership must match the selected task list."}
                )
            if self.task_list.client_id != self.client_id:
                raise ValidationError({"client": "Task client must match the selected task list."})
            if self.task_list.project_id and self.task_list.project_id != self.project_id:
                raise ValidationError(
                    {"project": "Task project must match the selected project task list."}
                )

        if self.section_id and self.section:
            if self.task_list_id != self.section.task_list_id:
                raise ValidationError(
                    {"section": "Task section must belong to the selected task list."}
                )

        if self.parent_task_id and self.parent_task:
            if self.pk and self.parent_task_id == self.pk:
                raise ValidationError({"parent_task": "A task cannot be its own parent."})
            if self.parent_task.ownership_type != self.ownership_type:
                raise ValidationError({"parent_task": "Subtask ownership must match its parent."})
            if self.parent_task.client_id != self.client_id:
                raise ValidationError({"client": "Subtask client must match its parent task."})
            if self.parent_task.project_id != self.project_id:
                raise ValidationError({"project": "Subtask project must match its parent task."})

        if self.recurrence_rule and self.due_date is None:
            raise ValidationError(
                {"due_date": "Recurring tasks require a due date for the first occurrence."}
            )

    def __str__(self) -> str:
        return self.title


class TaskDependency(models.Model):
    """A directed relationship where one task blocks another."""

    blocked_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="dependency_links",
    )
    blocking_task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="blocking_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["blocked_task", "blocking_task"],
                name="taskdependency_unique_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(blocked_task=models.F("blocking_task")),
                name="taskdependency_no_self_reference",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.blocked_task_id == self.blocking_task_id:
            raise ValidationError("A task cannot depend on itself.")
        if self.blocked_task.ownership_type != self.blocking_task.ownership_type:
            raise ValidationError("Task dependencies must stay within the same ownership context.")
        if self.blocked_task.client_id != self.blocking_task.client_id:
            raise ValidationError("Task dependencies cannot cross client boundaries.")

    def __str__(self) -> str:
        return f"{self.blocking_task} blocks {self.blocked_task}"

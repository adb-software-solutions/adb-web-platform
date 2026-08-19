from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.ownership import OwnershipType, ownership_constraint, validate_ownership


class Client(models.Model):
    """Client organisation/account."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("archived", "Archived"),
    ]

    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)

    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.company or self.name


class ClientContact(models.Model):
    """Individual contact for a client."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. CTO, Project Manager",
    )
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    is_billing = models.BooleanField(default=False)
    is_technical = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "email"],
                name="unique_client_contact_email",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.client})"


class Project(models.Model):
    """Operational project that is either client-owned or internal."""

    STATUS_CHOICES = [
        ("planning", "Planning"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.CLIENT,
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    budget = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [ownership_constraint("project_valid_ownership")]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)

    def __str__(self) -> str:
        owner = self.client if self.client_id else "Internal"
        return f"{self.name} ({owner})"


class TimeEntry(models.Model):
    """Manual or timer-recorded time against client-owned or internal work."""

    class EntryType(models.TextChoices):
        MANUAL = "manual", "Manual"
        TIMER = "timer", "Timer"

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.CLIENT,
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    ticket = models.ForeignKey(
        "ticketing.Ticket",
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    date = models.DateField()
    duration_hours = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        help_text="Hours worked",
    )
    description = models.TextField()
    billable = models.BooleanField(default=False)
    entry_type = models.CharField(
        max_length=16,
        choices=EntryType.choices,
        default=EntryType.MANUAL,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [ownership_constraint("timeentry_valid_ownership")]

    def apply_context_ownership(self) -> None:
        """Derive ownership and project from a selected first-class work context."""
        if self.task_id and self.task:
            self.ownership_type = self.task.ownership_type
            self.client_id = self.task.client_id
            self.project_id = self.task.project_id
            return
        if self.ticket_id and self.ticket:
            self.ownership_type = (
                OwnershipType.CLIENT if self.ticket.client_id else OwnershipType.INTERNAL
            )
            self.client_id = self.ticket.client_id
            self.project_id = None
            return
        if self.project_id and self.project:
            self.ownership_type = self.project.ownership_type
            self.client_id = self.project.client_id

    def clean(self) -> None:
        super().clean()
        if self.task_id and self.ticket_id:
            raise ValidationError(
                {"task": "Time cannot be assigned to a task and ticket simultaneously."}
            )
        if self.ticket_id and self.project_id:
            raise ValidationError(
                {"project": "Ticket time cannot also be assigned directly to a project."}
            )
        if (
            self.task_id
            and self.project_id
            and self.task is not None
            and self.task.project_id != self.project_id
        ):
            raise ValidationError(
                {"project": "Time-entry project must match the selected task project."}
            )

        self.apply_context_ownership()
        validate_ownership(self)
        if self.duration_hours <= 0:
            raise ValidationError({"duration_hours": "Tracked time must be greater than zero."})
        if self.ownership_type == OwnershipType.INTERNAL and self.billable:
            raise ValidationError({"billable": "Internal time cannot be marked billable."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.apply_context_ownership()
        if self.ownership_type == OwnershipType.INTERNAL:
            self.billable = False
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        context = self.task or self.ticket or self.project or self.client or "Internal"
        return f"{context} - {self.date} ({self.duration_hours}h)"


class RunningTimer(models.Model):
    """One persistent running timer per staff account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="running_timer",
    )
    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="running_timers",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="running_timers",
        null=True,
        blank=True,
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        related_name="running_timers",
        null=True,
        blank=True,
    )
    ticket = models.ForeignKey(
        "ticketing.Ticket",
        on_delete=models.SET_NULL,
        related_name="running_timers",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)
    billable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["started_at"]
        constraints = [ownership_constraint("runningtimer_valid_ownership")]

    def apply_context_ownership(self) -> None:
        if self.task_id and self.task:
            self.ownership_type = self.task.ownership_type
            self.client_id = self.task.client_id
            self.project_id = self.task.project_id
            return
        if self.ticket_id and self.ticket:
            self.ownership_type = (
                OwnershipType.CLIENT if self.ticket.client_id else OwnershipType.INTERNAL
            )
            self.client_id = self.ticket.client_id
            self.project_id = None
            return
        if self.project_id and self.project:
            self.ownership_type = self.project.ownership_type
            self.client_id = self.project.client_id

    def clean(self) -> None:
        super().clean()
        if self.task_id and self.ticket_id:
            raise ValidationError(
                {"task": "A timer cannot target a task and ticket simultaneously."}
            )
        if self.ticket_id and self.project_id:
            raise ValidationError({"project": "A ticket timer cannot also target a project."})
        if (
            self.task_id
            and self.project_id
            and self.task is not None
            and self.task.project_id != self.project_id
        ):
            raise ValidationError(
                {"project": "Timer project must match the selected task project."}
            )

        self.apply_context_ownership()
        validate_ownership(self)
        if self.ownership_type == OwnershipType.INTERNAL and self.billable:
            raise ValidationError({"billable": "Internal time cannot be marked billable."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.apply_context_ownership()
        if self.ownership_type == OwnershipType.INTERNAL:
            self.billable = False
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user} since {self.started_at}"


class ProjectNote(models.Model):
    """Internal notes on a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="project_notes",
        null=True,
        blank=True,
    )
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Note on {self.project} - {self.created_at}"

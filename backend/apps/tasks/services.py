from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Literal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tasks.models import Task, TaskStatus

TaskRecurrenceFrequency = Literal["none", "daily", "weekly", "monthly"]

_RECURRENCE_RULES: dict[TaskRecurrenceFrequency, str] = {
    "none": "",
    "daily": "FREQ=DAILY;INTERVAL=1",
    "weekly": "FREQ=WEEKLY;INTERVAL=1",
    "monthly": "FREQ=MONTHLY;INTERVAL=1",
}


def build_recurrence_rule(frequency: TaskRecurrenceFrequency) -> str:
    return _RECURRENCE_RULES[frequency]


def recurrence_frequency(rule: str) -> TaskRecurrenceFrequency:
    normalized = rule.strip().upper()
    for frequency, known_rule in _RECURRENCE_RULES.items():
        if normalized == known_rule:
            return frequency
    return "none"


def next_occurrence_date(current: date, recurrence_rule: str) -> date | None:
    frequency = recurrence_frequency(recurrence_rule)
    if frequency == "daily":
        return current + timedelta(days=1)
    if frequency == "weekly":
        return current + timedelta(days=7)
    if frequency == "monthly":
        month_index = current.month
        year = current.year + (month_index // 12)
        month = (month_index % 12) + 1
        day = min(current.day, monthrange(year, month)[1])
        return date(year, month, day)
    return None


def next_occurrence_datetime(current: date | None, recurrence_rule: str) -> datetime | None:
    if current is None:
        return None
    next_date = next_occurrence_date(current, recurrence_rule)
    if next_date is None:
        return None
    return timezone.make_aware(datetime.combine(next_date, time.min))


def _status_named(name: str) -> TaskStatus | None:
    return TaskStatus.objects.filter(name__iexact=name).order_by("order").first()


def default_open_status() -> TaskStatus | None:
    return _status_named("To do") or TaskStatus.objects.exclude(
        name__iexact="Done"
    ).order_by("order").first()


def done_status() -> TaskStatus | None:
    return _status_named("Done")


@transaction.atomic
def complete_task(task: Task) -> tuple[Task, Task | None]:
    locked = (
        Task.objects.select_for_update()
        .select_related("client", "project", "task_list", "status", "assigned_to", "created_by")
        .get(pk=task.pk)
    )
    if locked.completed_at is not None:
        next_task = getattr(locked, "next_occurrence", None)
        return locked, next_task

    locked.completed_at = timezone.now()
    completed_status = done_status()
    if completed_status is not None:
        locked.status = completed_status

    next_task = None
    next_due_date = (
        next_occurrence_date(locked.due_date, locked.recurrence_rule)
        if locked.due_date is not None
        else None
    )
    if locked.recurrence_rule and next_due_date is not None:
        existing_next = getattr(locked, "next_occurrence", None)
        if existing_next is None:
            next_task = Task(
                ownership_type=locked.ownership_type,
                client=locked.client,
                project=locked.project,
                title=locked.title,
                description=locked.description,
                task_list=locked.task_list,
                status=default_open_status(),
                priority=locked.priority,
                due_date=next_due_date,
                recurrence_rule=locked.recurrence_rule,
                next_occurrence_at=next_occurrence_datetime(
                    next_due_date, locked.recurrence_rule
                ),
                previous_occurrence=locked,
                assigned_to=locked.assigned_to,
                created_by=locked.created_by,
            )
            next_task.full_clean()
            next_task.save()
        else:
            next_task = existing_next
        locked.next_occurrence_at = timezone.make_aware(
            datetime.combine(next_due_date, time.min)
        )

    locked.full_clean()
    locked.save()
    return locked, next_task


@transaction.atomic
def reopen_task(task: Task) -> Task:
    locked = Task.objects.select_for_update().get(pk=task.pk)
    if locked.completed_at is None:
        return locked
    if hasattr(locked, "next_occurrence"):
        raise ValidationError(
            "A recurring task occurrence cannot be reopened after its next occurrence exists."
        )

    locked.completed_at = None
    locked.status = default_open_status()
    locked.full_clean()
    locked.save()
    return locked

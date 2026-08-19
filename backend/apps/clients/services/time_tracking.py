from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.access_control.policies import scope_clients_for_user, scope_ticket_queues_for_user
from apps.clients.models import Client, Project, RunningTimer, TimeEntry
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task
from apps.ticketing.models import Ticket
from authentication.models import User


class TimeTrackingError(Exception):
    def __init__(self, message: str, code: str = "validation_error") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class TimeContext:
    ownership_type: str
    client: Client | None
    project: Project | None
    task: Task | None
    ticket: Ticket | None


def visible_time_entries(user: User) -> QuerySet[TimeEntry]:
    entries = TimeEntry.objects.select_related(
        "client",
        "project",
        "task",
        "ticket",
        "ticket__queue",
        "user",
    )
    if user.is_superuser:
        return entries

    clients = scope_clients_for_user(user)
    queues = scope_ticket_queues_for_user(user)
    return entries.filter(
        Q(ticket__isnull=True, ownership_type=OwnershipType.INTERNAL)
        | Q(ticket__isnull=True, client__in=clients)
        | Q(ticket__queue__in=queues, ticket__client__isnull=True)
        | Q(ticket__queue__in=queues, ticket__client__in=clients)
    ).distinct()


def visible_projects(user: User) -> QuerySet[Project]:
    projects = Project.objects.select_related("client")
    if user.is_superuser:
        return projects
    clients = scope_clients_for_user(user)
    return projects.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


def visible_tasks(user: User) -> QuerySet[Task]:
    tasks = Task.objects.select_related("client", "project")
    if user.is_superuser:
        return tasks
    clients = scope_clients_for_user(user)
    return tasks.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


def visible_tickets(user: User) -> QuerySet[Ticket]:
    tickets = Ticket.objects.select_related("client", "queue")
    if user.is_superuser:
        return tickets
    clients = scope_clients_for_user(user)
    queues = scope_ticket_queues_for_user(user)
    return tickets.filter(
        Q(queue__in=queues) & (Q(client__isnull=True) | Q(client__in=clients))
    ).distinct()


def resolve_time_context(
    user: User,
    *,
    ownership_type: str,
    client_id: int | None,
    project_id: int | None,
    task_id: int | None,
    ticket_id: int | None,
) -> TimeContext:
    selected_contexts = sum(value is not None for value in (project_id, task_id, ticket_id))
    if selected_contexts > 1:
        if task_id is not None and project_id is not None and ticket_id is None:
            task = visible_tasks(user).filter(id=task_id).first()
            if task is None:
                raise TimeTrackingError("Task not found or outside your access scope.", "not_found")
            if task.project_id != project_id:
                raise TimeTrackingError(
                    "The selected project does not match the selected task.",
                    "context_mismatch",
                )
            return TimeContext(task.ownership_type, task.client, task.project, task, None)
        raise TimeTrackingError(
            "Time can target only one of a project, task or ticket.",
            "multiple_contexts",
        )

    if task_id is not None:
        task = visible_tasks(user).filter(id=task_id).first()
        if task is None:
            raise TimeTrackingError("Task not found or outside your access scope.", "not_found")
        return TimeContext(task.ownership_type, task.client, task.project, task, None)

    if ticket_id is not None:
        ticket = visible_tickets(user).filter(id=ticket_id).first()
        if ticket is None:
            raise TimeTrackingError("Ticket not found or outside your access scope.", "not_found")
        ticket_ownership = OwnershipType.CLIENT if ticket.client_id else OwnershipType.INTERNAL
        return TimeContext(ticket_ownership, ticket.client, None, None, ticket)

    if project_id is not None:
        project = visible_projects(user).filter(id=project_id).first()
        if project is None:
            raise TimeTrackingError("Project not found or outside your access scope.", "not_found")
        return TimeContext(project.ownership_type, project.client, project, None, None)

    if ownership_type == OwnershipType.INTERNAL:
        if client_id is not None:
            raise TimeTrackingError("Internal time cannot reference a client.", "invalid_ownership")
        return TimeContext(OwnershipType.INTERNAL, None, None, None, None)

    if ownership_type != OwnershipType.CLIENT:
        raise TimeTrackingError("Invalid time ownership type.", "invalid_ownership")
    if client_id is None:
        raise TimeTrackingError("Client time requires a client.", "invalid_ownership")
    client = scope_clients_for_user(user).filter(id=client_id).first()
    if client is None:
        raise TimeTrackingError("Client not found or outside your access scope.", "not_found")
    return TimeContext(OwnershipType.CLIENT, client, None, None, None)


def apply_time_context(entry: TimeEntry | RunningTimer, context: TimeContext) -> None:
    entry.ownership_type = context.ownership_type
    entry.client = context.client
    entry.project = context.project
    entry.task = context.task
    entry.ticket = context.ticket
    if context.ownership_type == OwnershipType.INTERNAL:
        entry.billable = False


@transaction.atomic
def start_timer(
    user: User,
    context: TimeContext,
    *,
    description: str,
    billable: bool,
) -> RunningTimer:
    if RunningTimer.objects.select_for_update().filter(user=user).exists():
        raise TimeTrackingError("You already have a running timer.", "timer_already_running")

    timer = RunningTimer(
        user=user,
        description=description.strip(),
        billable=billable,
    )
    apply_time_context(timer, context)
    try:
        timer.full_clean()
        timer.save()
    except IntegrityError as error:
        raise TimeTrackingError(
            "You already have a running timer.", "timer_already_running"
        ) from error
    return timer


@transaction.atomic
def stop_timer(user: User, *, description: str | None = None) -> TimeEntry:
    timer = (
        RunningTimer.objects.select_for_update()
        .select_related("client", "project", "task", "ticket")
        .filter(user=user)
        .first()
    )
    if timer is None:
        raise TimeTrackingError("You do not have a running timer.", "timer_not_running")

    stopped_at = timezone.now()
    elapsed_seconds = max(1, int((stopped_at - timer.started_at).total_seconds()))
    duration_hours = (Decimal(elapsed_seconds) / Decimal(3600)).quantize(Decimal("0.0001"))
    entry = TimeEntry(
        ownership_type=timer.ownership_type,
        client=timer.client,
        project=timer.project,
        task=timer.task,
        ticket=timer.ticket,
        user=user,
        date=timezone.localdate(timer.started_at),
        duration_hours=duration_hours,
        description=(description if description is not None else timer.description).strip(),
        billable=timer.billable,
        entry_type=TimeEntry.EntryType.TIMER,
    )
    entry.full_clean()
    entry.save()
    timer.delete()
    return entry


@transaction.atomic
def cancel_timer(user: User) -> None:
    deleted, _ = RunningTimer.objects.filter(user=user).delete()
    if not deleted:
        raise TimeTrackingError("You do not have a running timer.", "timer_not_running")

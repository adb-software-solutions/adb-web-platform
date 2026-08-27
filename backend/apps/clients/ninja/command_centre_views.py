from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.access_control.policies import scope_clients_for_user, scope_ticket_queues_for_user
from apps.clients.models import Client, TimeEntry
from apps.credentials.models import StoredCredential
from apps.credentials.policies import scope_credentials_for_user
from apps.infrastructure.models import InfrastructureResource
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.knowledge_base.models import KnowledgeBaseDocument
from apps.monitoring.models import MonitorIncident
from apps.tasks.models import Task
from apps.ticketing.models import Ticket
from authentication.ninja.schemas import ProblemDetail

from .command_centre_schemas import (
    ClientCommandCentreActivityOut,
    ClientCommandCentreCapabilitiesOut,
    ClientCommandCentreOut,
    ClientCommandCentreProjectOut,
    ClientCommandCentreStatsOut,
    ClientCommandCentreTaskOut,
    ClientCommandCentreTicketOut,
)

client_command_centre_router = Router(tags=["admin-client-command-centre"])
StaffProblem = tuple[int, dict[str, Any]]
CURRENT_PROJECT_STATUSES = ("planning", "active", "paused")
ACTIONABLE_TICKET_STATUSES = (
    Ticket.Status.NEW,
    Ticket.Status.OPEN,
    Ticket.Status.WAITING_INTERNAL,
)
VALID_PERIOD_DAYS = {7, 30, 90, 365}


def _problem(status: int, message: str, code: str) -> StaffProblem:
    return status, {"message": message, "success": False, "code": code}


def _visible_client(request: HttpRequest, client_id: int) -> Client | None:
    if not request.user.is_authenticated or not (
        request.user.is_staff or request.user.is_superuser
    ):
        return None
    if not request.user.has_perm("clients.view_client"):
        return None
    return scope_clients_for_user(request.user).filter(id=client_id).first()


def _user_label(user: Any | None) -> str | None:
    if user is None:
        return None
    full_name = user.get_full_name().strip()
    return full_name or user.email


def _capabilities(request: HttpRequest) -> ClientCommandCentreCapabilitiesOut:
    projects = request.user.has_perm("clients.view_project")
    tasks = request.user.has_perm("tasks.view_task")
    tickets = request.user.has_perm("ticketing.view_ticket")
    time = request.user.has_perm("clients.view_timeentry")
    infrastructure = request.user.has_perm("infrastructure.view_infrastructureresource")
    credentials = request.user.has_perm("credentials.view_storedcredential")
    knowledge_base = request.user.has_perm("knowledge_base.view_knowledgebasedocument")
    monitoring = infrastructure and request.user.has_perm("monitoring.view_monitorincident")
    contacts = request.user.has_perm("clients.view_clientcontact")
    return ClientCommandCentreCapabilitiesOut(
        contacts=contacts,
        projects=projects,
        tasks=tasks,
        tickets=tickets,
        time=time,
        infrastructure=infrastructure,
        credentials=credentials,
        knowledge_base=knowledge_base,
        monitoring=monitoring,
        activity=True,
    )


def _activity(
    request: HttpRequest,
    client: Client,
    capabilities: ClientCommandCentreCapabilitiesOut,
) -> list[ClientCommandCentreActivityOut]:
    items: list[ClientCommandCentreActivityOut] = [
        ClientCommandCentreActivityOut(
            kind="client",
            label=str(client),
            description="Client account updated",
            occurred_at=client.updated_at,
            href=f"/admin/clients/{client.id}",
        )
    ]

    if capabilities.contacts:
        items.extend(
            ClientCommandCentreActivityOut(
                kind="contact",
                label=contact.name,
                description="Contact updated",
                occurred_at=contact.updated_at,
                href=f"/admin/clients/{client.id}/contacts/{contact.id}",
            )
            for contact in client.contacts.order_by("-updated_at")[:3]
        )

    if capabilities.projects:
        items.extend(
            ClientCommandCentreActivityOut(
                kind="project",
                label=project.name,
                description=f"Project updated · {project.status}",
                occurred_at=project.updated_at,
                href=f"/admin/projects/{project.id}",
            )
            for project in client.projects.order_by("-updated_at")[:3]
        )

    if capabilities.tasks:
        items.extend(
            ClientCommandCentreActivityOut(
                kind="task",
                label=task.title,
                description="Task updated",
                occurred_at=task.updated_at,
                href=f"/admin/tasks/{task.id}",
            )
            for task in client.tasks.order_by("-updated_at")[:3]
        )

    if capabilities.tickets:
        queues = scope_ticket_queues_for_user(request.user)
        items.extend(
            ClientCommandCentreActivityOut(
                kind="ticket",
                label=ticket.reference,
                description=ticket.subject,
                occurred_at=ticket.updated_at,
                href=f"/admin/tickets/{ticket.id}",
            )
            for ticket in client.tickets.filter(queue__in=queues).order_by("-updated_at")[:3]
        )

    if capabilities.infrastructure:
        resources = scope_infrastructure_resources_for_user(request.user).filter(client=client)
        items.extend(
            ClientCommandCentreActivityOut(
                kind="infrastructure",
                label=resource.name,
                description=(f"Infrastructure updated · {resource.get_resource_type_display()}"),
                occurred_at=resource.updated_at,
                href=f"/admin/infrastructure/resources/{resource.id}",
            )
            for resource in resources.order_by("-updated_at")[:3]
        )

    if capabilities.knowledge_base:
        documents = KnowledgeBaseDocument.objects.filter(client=client).order_by("-updated_at")[:3]
        items.extend(
            ClientCommandCentreActivityOut(
                kind="knowledge",
                label=document.title,
                description="Knowledge Base document updated",
                occurred_at=document.updated_at,
                href=f"/admin/knowledge-base/documents/{document.id}",
            )
            for document in documents
        )

    if capabilities.credentials:
        credentials = scope_credentials_for_user(request.user).filter(client=client)
        items.extend(
            ClientCommandCentreActivityOut(
                kind="credential",
                label=credential.name,
                description="Credential metadata updated",
                occurred_at=credential.updated_at,
                href="/admin/credentials",
            )
            for credential in credentials.order_by("-updated_at")[:3]
        )

    return sorted(items, key=lambda item: item.occurred_at, reverse=True)[:12]


@client_command_centre_router.get(
    "/clients/{client_id}/command-centre",
    response={
        200: ClientCommandCentreOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def client_command_centre(
    request: HttpRequest,
    client_id: int,
    period_days: int = 30,
) -> ClientCommandCentreOut | StaffProblem:
    if not request.user.is_authenticated:
        return _problem(401, "User not authenticated", "unauthenticated")
    if not (request.user.is_staff or request.user.is_superuser):
        return _problem(
            403,
            "You do not have permission to access this resource.",
            "forbidden",
        )
    if not request.user.has_perm("clients.view_client"):
        return _problem(403, "You do not have permission to view clients.", "forbidden")

    client = _visible_client(request, client_id)
    if client is None:
        return _problem(404, "Client not found.", "not_found")

    period_days = period_days if period_days in VALID_PERIOD_DAYS else 30
    period_end = timezone.localdate()
    period_start = period_end - timedelta(days=period_days - 1)
    capabilities = _capabilities(request)
    stats = ClientCommandCentreStatsOut(
        active_contacts=(
            client.contacts.filter(is_active=True).count() if capabilities.contacts else 0
        )
    )

    projects: list[ClientCommandCentreProjectOut] = []
    if capabilities.projects:
        current_projects = client.projects.filter(status__in=CURRENT_PROJECT_STATUSES)
        stats.current_projects = current_projects.count()
        projects = [
            ClientCommandCentreProjectOut(
                id=project.id,
                name=project.name,
                status=project.status,
                start_date=project.start_date,
                end_date=project.end_date,
            )
            for project in current_projects.order_by("status", "-start_date")[:6]
        ]

    tasks: list[ClientCommandCentreTaskOut] = []
    if capabilities.tasks:
        open_tasks = Task.objects.select_related("status", "assigned_to", "project").filter(
            client=client,
            completed_at__isnull=True,
        )
        stats.open_tasks = open_tasks.count()
        stats.overdue_tasks = open_tasks.filter(due_date__lt=period_end).count()
        task_rows = open_tasks.order_by("due_date", "-priority", "id")[:8]
        tasks = [
            ClientCommandCentreTaskOut(
                id=task.id,
                title=task.title,
                priority=task.priority,
                due_date=task.due_date,
                status_name=task.status.name if task.status else None,
                assigned_to_name=_user_label(task.assigned_to),
                project_id=task.project_id,
                project_name=task.project.name if task.project else None,
                is_overdue=bool(task.due_date and task.due_date < period_end),
            )
            for task in task_rows
        ]

    tickets: list[ClientCommandCentreTicketOut] = []
    if capabilities.tickets:
        queues = scope_ticket_queues_for_user(request.user)
        visible_tickets = Ticket.objects.select_related("assigned_to").filter(
            client=client,
            queue__in=queues,
        )
        stats.actionable_tickets = visible_tickets.filter(
            status__in=ACTIONABLE_TICKET_STATUSES
        ).count()
        stats.waiting_customer_tickets = visible_tickets.filter(
            status=Ticket.Status.WAITING_CUSTOMER
        ).count()
        ticket_rows = visible_tickets.exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.SPAM]
        ).order_by("-last_message_at", "-created_at")[:6]
        tickets = [
            ClientCommandCentreTicketOut(
                id=ticket.id,
                reference=ticket.reference,
                subject=ticket.subject,
                status=ticket.status,
                priority=ticket.priority,
                assigned_to_name=_user_label(ticket.assigned_to),
                last_message_at=ticket.last_message_at,
                updated_at=ticket.updated_at,
            )
            for ticket in ticket_rows
        ]

    if capabilities.time:
        period_time = TimeEntry.objects.filter(
            client=client,
            date__gte=period_start,
            date__lte=period_end,
        )
        totals = period_time.aggregate(
            hours=Sum("duration_hours"),
            billable_hours=Sum("duration_hours", filter=Q(billable=True)),
        )
        stats.period_hours = totals["hours"] or Decimal(0)
        stats.period_billable_hours = totals["billable_hours"] or Decimal(0)

    if capabilities.infrastructure:
        resources = scope_infrastructure_resources_for_user(request.user).filter(client=client)
        stats.current_resources = resources.exclude(
            lifecycle_status__in=[
                InfrastructureResource.LifecycleStatus.RETIRED,
                InfrastructureResource.LifecycleStatus.ARCHIVED,
            ]
        ).count()
        if capabilities.monitoring:
            stats.active_monitor_incidents = MonitorIncident.objects.filter(
                monitor_check__resource__in=resources,
                status__in=[
                    MonitorIncident.Status.OPEN,
                    MonitorIncident.Status.ACKNOWLEDGED,
                ],
            ).count()

    if capabilities.credentials:
        stats.active_credentials = (
            scope_credentials_for_user(request.user)
            .filter(
                client=client,
                status=StoredCredential.Status.ACTIVE,
            )
            .count()
        )

    if capabilities.knowledge_base:
        stats.knowledge_documents = KnowledgeBaseDocument.objects.filter(
            client=client,
            archived_at__isnull=True,
        ).count()

    return ClientCommandCentreOut(
        client_id=client.id,
        period_days=period_days,
        period_start=period_start,
        period_end=period_end,
        capabilities=capabilities,
        stats=stats,
        projects=projects,
        tasks=tasks,
        tickets=tickets,
        activity=_activity(request, client, capabilities),
    )

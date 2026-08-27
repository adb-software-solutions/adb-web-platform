from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.access_control.models import StaffAccessProfile
from apps.access_control.policies import scope_clients_for_user, scope_ticket_queues_for_user
from apps.clients.models import Project, RunningTimer, TimeEntry
from apps.core.models import AuditEvent, DashboardPreference
from apps.core.ownership import OwnershipType
from apps.crm.models import Lead, LeadStatus
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.monitoring.models import MonitorCheck, MonitorIncident
from apps.tasks.models import Task
from apps.ticketing.models import Ticket, TicketQueue
from authentication.models import User

from .ninja.schemas import (
    DashboardActivityOut,
    DashboardAgendaOut,
    DashboardIncidentOut,
    DashboardLeadOut,
    DashboardLeadWidgetOut,
    DashboardProjectOut,
    DashboardProjectWidgetOut,
    DashboardTaskOut,
    DashboardTaskWidgetOut,
    DashboardTechnicalHealthOut,
    DashboardTicketOut,
    DashboardTicketWidgetOut,
    DashboardTimerOut,
    DashboardWidgetOptionOut,
    DashboardWidgetPreferenceOut,
    DashboardWorkspaceOut,
)


@dataclass(frozen=True)
class WidgetSpec:
    key: str
    title: str
    description: str
    default_span: int
    permissions: tuple[str, ...]


WIDGET_SPECS = (
    WidgetSpec(
        "my_tasks",
        "My tasks",
        "Your current assigned work, with today and overdue attention counts.",
        6,
        ("tasks.view_task",),
    ),
    WidgetSpec(
        "my_tickets",
        "My tickets",
        "Your actionable Ticket work inside your authorised/default Queue scope.",
        6,
        ("ticketing.view_ticket",),
    ),
    WidgetSpec(
        "active_timer",
        "Time",
        "Your running timer and personal tracked hours for the current week.",
        4,
        ("clients.view_timeentry",),
    ),
    WidgetSpec(
        "lead_follow_up",
        "Lead follow-up",
        "Open Leads currently assigned to you.",
        4,
        ("crm.view_lead",),
    ),
    WidgetSpec(
        "current_projects",
        "Current projects",
        "Planning, active and paused Projects in your access scope.",
        4,
        ("clients.view_project",),
    ),
    WidgetSpec(
        "technical_health",
        "Technical health",
        "Active Monitoring incidents and failing checks in your resource scope.",
        6,
        ("monitoring.view_monitorcheck", "monitoring.view_monitorincident"),
    ),
    WidgetSpec(
        "agenda",
        "Agenda",
        "Your dated Tasks due today and during the next seven days.",
        6,
        ("tasks.view_task",),
    ),
    WidgetSpec(
        "recent_activity",
        "Recent activity",
        "Your recent audited actions, without sensitive audit metadata.",
        12,
        ("core.view_auditevent",),
    ),
)
WIDGET_BY_KEY = {spec.key: spec for spec in WIDGET_SPECS}
VALID_SPANS = {4, 6, 8, 12}
MAX_WIDGETS = 12
ACTIONABLE_TICKET_STATUSES = (
    Ticket.Status.NEW,
    Ticket.Status.OPEN,
    Ticket.Status.WAITING_INTERNAL,
    Ticket.Status.WAITING_CUSTOMER,
)
CURRENT_PROJECT_STATUSES = ("planning", "active", "paused")


def available_widget_specs(user: User) -> list[WidgetSpec]:
    return [
        spec
        for spec in WIDGET_SPECS
        if all(user.has_perm(permission) for permission in spec.permissions)
    ]


def widget_options(user: User) -> list[DashboardWidgetOptionOut]:
    return [
        DashboardWidgetOptionOut(
            key=spec.key,
            title=spec.title,
            description=spec.description,
            default_span=spec.default_span,
        )
        for spec in available_widget_specs(user)
    ]


def _normalise_layout_entry(entry: Any) -> DashboardWidgetPreferenceOut | None:
    if not isinstance(entry, dict):
        return None
    key = entry.get("key")
    span = entry.get("span")
    if not isinstance(key, str) or key not in WIDGET_BY_KEY:
        return None
    if not isinstance(span, int) or span not in VALID_SPANS:
        span = WIDGET_BY_KEY[key].default_span
    return DashboardWidgetPreferenceOut(key=key, span=span)


def dashboard_layout(user: User) -> list[DashboardWidgetPreferenceOut]:
    available = available_widget_specs(user)
    available_keys = {spec.key for spec in available}
    preference = DashboardPreference.objects.filter(user=user).first()
    if preference is None:
        return [
            DashboardWidgetPreferenceOut(key=spec.key, span=spec.default_span) for spec in available
        ]

    result: list[DashboardWidgetPreferenceOut] = []
    seen: set[str] = set()
    for raw_entry in preference.layout:
        entry = _normalise_layout_entry(raw_entry)
        if entry is None or entry.key not in available_keys or entry.key in seen:
            continue
        result.append(entry)
        seen.add(entry.key)
    return result[:MAX_WIDGETS]


def validate_dashboard_layout(
    user: User,
    layout: list[dict[str, Any]],
) -> list[dict[str, int | str]]:
    if len(layout) > MAX_WIDGETS:
        raise ValidationError(f"A dashboard may contain at most {MAX_WIDGETS} widgets.")
    available_keys = {spec.key for spec in available_widget_specs(user)}
    normalised: list[dict[str, int | str]] = []
    seen: set[str] = set()
    for entry in layout:
        key = entry.get("key")
        span = entry.get("span")
        if not isinstance(key, str) or key not in WIDGET_BY_KEY:
            raise ValidationError("Unknown dashboard widget.")
        if key not in available_keys:
            raise ValidationError("You do not have permission to enable that dashboard widget.")
        if key in seen:
            raise ValidationError("Dashboard widgets may appear only once.")
        if not isinstance(span, int) or span not in VALID_SPANS:
            raise ValidationError("Dashboard widget span must be 4, 6, 8 or 12 columns.")
        normalised.append({"key": key, "span": span})
        seen.add(key)
    return normalised


@transaction.atomic
def save_dashboard_layout(
    *,
    user: User,
    layout: list[dict[str, Any]],
    ip_address: str | None = None,
    user_agent: str = "",
) -> list[DashboardWidgetPreferenceOut]:
    normalised = validate_dashboard_layout(user, layout)
    preference, _created = DashboardPreference.objects.select_for_update().get_or_create(user=user)
    preference.layout = normalised
    preference.save(update_fields=["layout", "updated_at"])
    AuditEvent.record(
        actor=user,
        action="dashboard.preferences_updated",
        target=preference,
        target_label="Personal dashboard",
        metadata={"widget_keys": [entry["key"] for entry in normalised]},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return dashboard_layout(user)


def _scoped_tasks(user: User) -> QuerySet[Task]:
    tasks = Task.objects.select_related("status", "client", "project")
    if user.is_superuser:
        return tasks
    clients = scope_clients_for_user(user)
    return tasks.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


def _task_out(task: Task) -> DashboardTaskOut:
    return DashboardTaskOut(
        id=task.id,
        title=task.title,
        status=task.status.name if task.status else "Unassigned",
        priority=task.priority,
        due_date=task.due_date,
        client_name=str(task.client) if task.client else None,
        project_name=task.project.name if task.project else None,
    )


def build_my_tasks(user: User) -> DashboardTaskWidgetOut:
    today = timezone.localdate()
    tasks = _scoped_tasks(user).filter(assigned_to=user, completed_at__isnull=True)
    rows = tasks.order_by("due_date", "-priority", "-created_at")[:6]
    return DashboardTaskWidgetOut(
        open_count=tasks.count(),
        overdue_count=tasks.filter(due_date__lt=today).count(),
        today_count=tasks.filter(due_date=today).count(),
        items=[_task_out(task) for task in rows],
    )


def _visible_ticket_queues(user: User) -> QuerySet[TicketQueue]:
    return scope_ticket_queues_for_user(
        user,
        TicketQueue.objects.filter(enabled=True),
    ).order_by("ordering", "name")


def _default_ticket_queue_ids(user: User, queues: QuerySet[TicketQueue]) -> list[int]:
    visible_ids = list(queues.values_list("id", flat=True))
    if not visible_ids:
        return []
    profile = StaffAccessProfile.objects.filter(user=user).first()
    if profile is None:
        return visible_ids
    stored_ids = list(
        profile.default_ticket_queues.filter(id__in=visible_ids, enabled=True)
        .order_by("ordering", "name")
        .values_list("id", flat=True)
    )
    return stored_ids or visible_ids


def _visible_tickets(user: User) -> QuerySet[Ticket]:
    tickets = Ticket.objects.select_related("queue", "client", "assigned_to")
    queue_ids = _default_ticket_queue_ids(user, _visible_ticket_queues(user))
    if user.is_superuser:
        return tickets.filter(queue_id__in=queue_ids)
    clients = scope_clients_for_user(user)
    return tickets.filter(
        Q(queue_id__in=queue_ids) & (Q(client__isnull=True) | Q(client__in=clients))
    ).distinct()


def build_my_tickets(user: User) -> DashboardTicketWidgetOut:
    active = _visible_tickets(user).filter(status__in=ACTIONABLE_TICKET_STATUSES)
    mine = active.filter(assigned_to=user)
    rows = mine.annotate(activity_at=Coalesce("last_message_at", "created_at")).order_by(
        "-activity_at",
        "-created_at",
    )[:6]
    return DashboardTicketWidgetOut(
        mine_count=mine.count(),
        unassigned_count=active.filter(assigned_to__isnull=True).count(),
        active_count=active.count(),
        items=[
            DashboardTicketOut(
                id=ticket.id,
                reference=ticket.reference,
                subject=ticket.subject,
                status=ticket.status,
                priority=ticket.priority,
                queue_name=ticket.queue.name,
                client_name=str(ticket.client) if ticket.client else None,
                last_message_at=ticket.last_message_at,
            )
            for ticket in rows
        ],
    )


def build_timer(user: User) -> DashboardTimerOut:
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    entries = TimeEntry.objects.filter(user=user, date__gte=week_start)
    if not user.is_superuser:
        clients = scope_clients_for_user(user)
        entries = entries.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))
    total = entries.aggregate(total=Sum("duration_hours"))["total"]
    timer = (
        RunningTimer.objects.filter(user=user)
        .select_related("client", "project", "task", "ticket")
        .first()
    )
    if timer is None:
        return DashboardTimerOut(running=False, hours_this_week=float(total or 0))
    context = timer.task or timer.ticket or timer.project or timer.client
    return DashboardTimerOut(
        running=True,
        started_at=timer.started_at,
        description=timer.description,
        context_label=str(context) if context else "Internal",
        hours_this_week=float(total or 0),
    )


def build_leads(user: User) -> DashboardLeadWidgetOut:
    leads = Lead.objects.select_related("status", "brand").filter(assigned_to=user)
    open_leads = leads.filter(Q(status__isnull=True) | Q(status__outcome=LeadStatus.Outcome.OPEN))
    rows = open_leads.order_by("-updated_at", "-created_at")[:5]
    return DashboardLeadWidgetOut(
        open_count=open_leads.count(),
        items=[
            DashboardLeadOut(
                id=lead.id,
                name=lead.name,
                company=lead.company,
                status=lead.status.name if lead.status else "Unassigned",
                brand=lead.brand.name if lead.brand else "Unassigned",
                created_at=lead.created_at,
            )
            for lead in rows
        ],
    )


def _scoped_projects(user: User) -> QuerySet[Project]:
    projects = Project.objects.select_related("client")
    if user.is_superuser:
        return projects
    clients = scope_clients_for_user(user)
    return projects.filter(Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients))


def build_projects(user: User) -> DashboardProjectWidgetOut:
    projects = _scoped_projects(user).filter(status__in=CURRENT_PROJECT_STATUSES)
    rows = projects.order_by("end_date", "-updated_at")[:6]
    return DashboardProjectWidgetOut(
        current_count=projects.count(),
        items=[
            DashboardProjectOut(
                id=project.id,
                name=project.name,
                status=project.status,
                client_name=str(project.client) if project.client else None,
                end_date=project.end_date,
            )
            for project in rows
        ],
    )


def build_technical_health(user: User) -> DashboardTechnicalHealthOut:
    resources = scope_infrastructure_resources_for_user(user)
    active_incidents = MonitorIncident.objects.filter(
        monitor_check__resource__in=resources,
        status__in=[MonitorIncident.Status.OPEN, MonitorIncident.Status.ACKNOWLEDGED],
    ).select_related("monitor_check", "monitor_check__resource")
    failing_checks = MonitorCheck.objects.filter(
        resource__in=resources,
        enabled=True,
        status__in=[MonitorCheck.Status.DEGRADED, MonitorCheck.Status.FAILING],
    )
    rows = active_incidents.order_by("-opened_at", "-id")[:6]
    return DashboardTechnicalHealthOut(
        active_incident_count=active_incidents.count(),
        failing_check_count=failing_checks.count(),
        items=[
            DashboardIncidentOut(
                id=incident.id,
                check_name=incident.monitor_check.name,
                resource_name=incident.monitor_check.resource.name,
                severity=incident.severity,
                status=incident.status,
                summary=incident.summary,
                opened_at=incident.opened_at,
            )
            for incident in rows
        ],
    )


def build_agenda(user: User) -> DashboardAgendaOut:
    today = timezone.localdate()
    tasks = _scoped_tasks(user).filter(
        assigned_to=user,
        completed_at__isnull=True,
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
    )
    rows = tasks.order_by("due_date", "-priority", "-created_at")[:8]
    return DashboardAgendaOut(
        today_count=tasks.filter(due_date=today).count(),
        next_seven_days_count=tasks.count(),
        items=[_task_out(task) for task in rows],
    )


def build_activity(user: User) -> list[DashboardActivityOut]:
    return [
        DashboardActivityOut(
            id=event.id,
            action=event.action,
            target_label=event.target_label,
            created_at=event.created_at,
        )
        for event in AuditEvent.objects.filter(actor=user).order_by("-created_at")[:10]
    ]


def build_dashboard_workspace(user: User) -> DashboardWorkspaceOut:
    layout = dashboard_layout(user)
    enabled = {entry.key for entry in layout}
    return DashboardWorkspaceOut(
        layout=layout,
        available_widgets=widget_options(user),
        my_tasks=build_my_tasks(user) if "my_tasks" in enabled else None,
        my_tickets=build_my_tickets(user) if "my_tickets" in enabled else None,
        active_timer=build_timer(user) if "active_timer" in enabled else None,
        lead_follow_up=build_leads(user) if "lead_follow_up" in enabled else None,
        current_projects=build_projects(user) if "current_projects" in enabled else None,
        technical_health=(build_technical_health(user) if "technical_health" in enabled else None),
        agenda=build_agenda(user) if "agenda" in enabled else None,
        recent_activity=build_activity(user) if "recent_activity" in enabled else None,
    )
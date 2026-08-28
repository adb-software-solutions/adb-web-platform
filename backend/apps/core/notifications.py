from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.access_control.policies import scope_clients_for_user
from apps.core.models import Notification
from apps.core.ownership import OwnershipType
from apps.credentials.health import evaluate_credential_health
from apps.credentials.models import StoredCredential
from apps.credentials.policies import scope_credentials_for_user
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.monitoring.models import MonitorIncident
from apps.tasks.models import Task
from authentication.models import User


@dataclass(frozen=True)
class NotificationSpec:
    source_key: str
    category: str
    severity: str
    title: str
    body: str = ""
    href: str = ""
    client_id: int | None = None
    resource_id: int | None = None


def sync_notification(user: User, spec: NotificationSpec) -> Notification:
    """Upsert one deterministic alert without reopening a dismissed unchanged alert."""
    notification, created = Notification.objects.get_or_create(
        user=user,
        source_key=spec.source_key,
        defaults={
            "category": spec.category,
            "severity": spec.severity,
            "title": spec.title,
            "body": spec.body,
            "href": spec.href,
            "client_id": spec.client_id,
            "resource_id": spec.resource_id,
        },
    )
    if created:
        return notification

    changed = any(
        [
            notification.category != spec.category,
            notification.severity != spec.severity,
            notification.title != spec.title,
            notification.body != spec.body,
            notification.href != spec.href,
            notification.client_id != spec.client_id,
            notification.resource_id != spec.resource_id,
        ]
    )
    update_fields: list[str] = []
    if changed:
        notification.category = spec.category
        notification.severity = spec.severity
        notification.title = spec.title
        notification.body = spec.body
        notification.href = spec.href
        notification.client_id = spec.client_id
        notification.resource_id = spec.resource_id
        notification.resolved_at = None
        notification.dismissed_at = None
        notification.read_at = None
        update_fields.extend(
            [
                "category",
                "severity",
                "title",
                "body",
                "href",
                "client_id",
                "resource_id",
                "resolved_at",
                "dismissed_at",
                "read_at",
            ]
        )
    elif notification.resolved_at is not None:
        notification.resolved_at = None
        notification.dismissed_at = None
        notification.read_at = None
        update_fields.extend(["resolved_at", "dismissed_at", "read_at"])

    if update_fields:
        notification.save(update_fields=[*update_fields, "updated_at"])
    return notification


def resolve_missing_notifications(user: User, prefix: str, active_keys: Iterable[str]) -> None:
    active = set(active_keys)
    unresolved = Notification.objects.filter(
        user=user,
        source_key__startswith=prefix,
        resolved_at__isnull=True,
    )
    if active:
        unresolved = unresolved.exclude(source_key__in=active)
    unresolved.update(resolved_at=timezone.now())


def _task_notifications(user: User) -> list[NotificationSpec]:
    if not user.has_perm("tasks.view_task"):
        return []
    today = timezone.localdate()
    clients = scope_clients_for_user(user)
    tasks = Task.objects.select_related("client", "project").filter(
        assigned_to=user,
        completed_at__isnull=True,
        due_date__lt=today,
    )
    if not user.is_superuser:
        tasks = tasks.filter(
            Q(ownership_type=OwnershipType.INTERNAL) | Q(client__in=clients)
        )

    specs: list[NotificationSpec] = []
    for task in tasks.distinct().order_by("due_date", "-priority", "id")[:50]:
        severity = (
            Notification.Severity.CRITICAL
            if task.priority >= 4
            else Notification.Severity.WARNING
        )
        context = (
            task.project.name
            if task.project
            else (str(task.client) if task.client else "Internal")
        )
        specs.append(
            NotificationSpec(
                source_key=f"task:overdue:{task.id}",
                category=Notification.Category.TASK,
                severity=severity,
                title=f"Overdue task: {task.title}",
                body=f"Due {task.due_date.isoformat()} · {context}",
                href=f"/admin/tasks/{task.id}",
                client_id=task.client_id,
            )
        )
    return specs


def _credential_notifications(user: User) -> list[NotificationSpec]:
    if not user.has_perm("credentials.view_storedcredential"):
        return []
    credentials = (
        scope_credentials_for_user(user)
        .select_related("client")
        .filter(status=StoredCredential.Status.ACTIVE)
    )
    specs: list[NotificationSpec] = []
    for credential in credentials.order_by("name", "id")[:500]:
        health = evaluate_credential_health(credential)
        if health.severity == "info":
            continue
        if health.status == "expired":
            title = f"Expired credential: {credential.name}"
            body = "The configured credential expiry date has passed."
        elif health.status in {"expiring", "expiring_soon"}:
            title = f"Credential expiring: {credential.name}"
            body = f"Expires in {health.expires_in_days} day(s)."
        elif health.status in {"rotation_due", "rotation_overdue"}:
            title = f"Credential rotation due: {credential.name}"
            body = (
                "Rotation is overdue."
                if health.rotation_due_in_days is not None
                and health.rotation_due_in_days < 0
                else "The configured rotation interval has been reached."
            )
        else:
            title = f"Credential rotation approaching: {credential.name}"
            body = f"Rotation due in {health.rotation_due_in_days} day(s)."
        specs.append(
            NotificationSpec(
                source_key=f"credential:health:{credential.id}",
                category=Notification.Category.CREDENTIAL,
                severity=health.severity,
                title=title,
                body=body,
                href=f"/admin/credentials/{credential.id}",
                client_id=credential.client_id,
            )
        )
    return specs


def _monitor_notifications(user: User) -> list[NotificationSpec]:
    if not (
        user.has_perm("monitoring.view_monitorincident")
        and user.has_perm("infrastructure.view_infrastructureresource")
    ):
        return []
    resources = scope_infrastructure_resources_for_user(user)
    incidents = MonitorIncident.objects.select_related(
        "monitor_check__resource__client"
    ).filter(
        monitor_check__resource__in=resources,
        status__in=[MonitorIncident.Status.OPEN, MonitorIncident.Status.ACKNOWLEDGED],
    )
    specs: list[NotificationSpec] = []
    for incident in incidents.order_by("-opened_at", "-id")[:50]:
        resource = incident.monitor_check.resource
        severity = (
            Notification.Severity.CRITICAL
            if incident.severity == "critical"
            else Notification.Severity.WARNING
        )
        specs.append(
            NotificationSpec(
                source_key=f"monitoring:incident:{incident.id}",
                category=Notification.Category.MONITORING,
                severity=severity,
                title=f"Monitoring incident: {resource.name}",
                body=incident.summary,
                href=f"/admin/monitoring/checks/{incident.monitor_check_id}",
                client_id=resource.client_id,
                resource_id=resource.id,
            )
        )
    return specs


def refresh_notifications(user: User) -> None:
    """Refresh deterministic operational alerts while preserving user read state."""
    with transaction.atomic():
        task_specs = _task_notifications(user)
        for spec in task_specs:
            sync_notification(user, spec)
        resolve_missing_notifications(
            user,
            "task:overdue:",
            (spec.source_key for spec in task_specs),
        )

        credential_specs = _credential_notifications(user)
        for spec in credential_specs:
            sync_notification(user, spec)
        resolve_missing_notifications(
            user,
            "credential:health:",
            (spec.source_key for spec in credential_specs),
        )

        monitor_specs = _monitor_notifications(user)
        for spec in monitor_specs:
            sync_notification(user, spec)
        resolve_missing_notifications(
            user,
            "monitoring:incident:",
            (spec.source_key for spec in monitor_specs),
        )

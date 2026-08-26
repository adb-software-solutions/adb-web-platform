from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router

from apps.credentials.models import StoredCredential
from apps.credentials.policies import scope_credentials_for_user
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.monitoring.models import MonitorCheck, MonitorIncident
from apps.monitoring.services import acknowledge_incident
from authentication.ninja.schemas import ProblemDetail

from .schemas import (
    MonitorCheckCreateIn,
    MonitorCheckOut,
    MonitorIncidentOut,
    MonitoringOverviewOut,
)

monitoring_router = Router(tags=["admin-monitoring"])
StaffProblem = tuple[int, dict[str, object]]


def _problem(status: int, detail: str, code: str) -> StaffProblem:
    return status, {"detail": detail, "code": code}


def _permission_problem(request: HttpRequest, *permissions: str) -> StaffProblem | None:
    user = request.user
    if not user.is_authenticated:
        return _problem(401, "Authentication required.", "not_authenticated")
    if not user.is_staff:
        return _problem(403, "Staff access required.", "permission_denied")
    if not all(user.has_perm(permission) for permission in permissions):
        return _problem(403, "You do not have permission for this action.", "permission_denied")
    return None


def _visible_checks(request: HttpRequest) -> QuerySet[MonitorCheck]:
    return MonitorCheck.objects.select_related("resource", "resource__client").filter(
        resource__in=scope_infrastructure_resources_for_user(request.user)
    )


def _check_out(check: MonitorCheck) -> MonitorCheckOut:
    resource = check.resource
    return MonitorCheckOut(
        id=check.id,
        resource_id=resource.id,
        resource_name=resource.name,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        name=check.name,
        check_type=check.check_type,
        severity=check.severity,
        enabled=check.enabled,
        target=check.target,
        port=check.port,
        status=check.status,
        consecutive_failures=check.consecutive_failures,
        consecutive_successes=check.consecutive_successes,
        last_checked_at=check.last_checked_at,
        next_run_at=check.next_run_at,
        last_duration_ms=check.last_duration_ms,
        last_message=check.last_message,
    )


def _incident_out(incident: MonitorIncident) -> MonitorIncidentOut:
    resource = incident.monitor_check.resource
    return MonitorIncidentOut(
        id=incident.id,
        check_id=incident.monitor_check_id,
        check_name=incident.monitor_check.name,
        resource_id=resource.id,
        resource_name=resource.name,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
        status=incident.status,
        severity=incident.severity,
        opened_at=incident.opened_at,
        acknowledged_at=incident.acknowledged_at,
        resolved_at=incident.resolved_at,
        failure_count=incident.failure_count,
        summary=incident.summary,
    )


@monitoring_router.get(
    "/monitoring/overview",
    response={200: MonitoringOverviewOut, 401: ProblemDetail, 403: ProblemDetail},
)
def monitoring_overview(request: HttpRequest) -> MonitoringOverviewOut | StaffProblem:
    problem = _permission_problem(
        request,
        "monitoring.view_monitorcheck",
        "monitoring.view_monitorincident",
    )
    if problem:
        return problem
    checks = _visible_checks(request)
    current_checks = list(
        checks.filter(enabled=True).order_by("status", "resource__name", "name")[:100]
    )
    incidents = list(
        MonitorIncident.objects.select_related(
            "monitor_check",
            "monitor_check__resource",
            "monitor_check__resource__client",
        )
        .filter(monitor_check__in=checks, status__in=["open", "acknowledged"])
        .order_by("status", "-opened_at")[:100]
    )
    return MonitoringOverviewOut(
        total_checks=checks.filter(enabled=True).count(),
        healthy_checks=checks.filter(enabled=True, status=MonitorCheck.Status.HEALTHY).count(),
        degraded_checks=checks.filter(enabled=True, status=MonitorCheck.Status.DEGRADED).count(),
        failing_checks=checks.filter(enabled=True, status=MonitorCheck.Status.FAILING).count(),
        pending_checks=checks.filter(enabled=True, status=MonitorCheck.Status.PENDING).count(),
        open_incidents=len(incidents),
        checks=[_check_out(check) for check in current_checks],
        incidents=[_incident_out(incident) for incident in incidents],
    )


@monitoring_router.post(
    "/monitoring/checks",
    response={
        201: MonitorCheckOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_monitor_check(
    request: HttpRequest,
    payload: MonitorCheckCreateIn,
) -> tuple[int, MonitorCheckOut | dict[str, object]]:
    problem = _permission_problem(request, "monitoring.add_monitorcheck")
    if problem:
        return problem
    resource = (
        scope_infrastructure_resources_for_user(request.user).filter(id=payload.resource_id).first()
    )
    if resource is None:
        return _problem(404, "Infrastructure resource not found.", "not_found")
    credential = None
    if payload.credential_id is not None:
        credential_problem = _permission_problem(request, "credentials.view_storedcredential")
        if credential_problem:
            return credential_problem
        credential = (
            scope_credentials_for_user(request.user)
            .filter(
                id=payload.credential_id,
                status=StoredCredential.Status.ACTIVE,
            )
            .first()
        )
        if credential is None:
            return _problem(404, "Credential not found.", "not_found")
    check = MonitorCheck(
        resource=resource,
        credential=credential,
        name=payload.name,
        check_type=payload.check_type,
        severity=payload.severity,
        target=payload.target,
        port=payload.port,
        expected_value=payload.expected_value,
        forbidden_value=payload.forbidden_value,
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        failure_threshold=payload.failure_threshold,
        recovery_threshold=payload.recovery_threshold,
        expiry_warning_days=payload.expiry_warning_days,
    )
    try:
        check.full_clean()
        check.save()
    except ValidationError as error:
        return _problem(400, "; ".join(error.messages), "validation_error")
    return 201, _check_out(check)


@monitoring_router.post(
    "/monitoring/incidents/{incident_id}/acknowledge",
    response={200: MonitorIncidentOut, 401: ProblemDetail, 403: ProblemDetail, 404: ProblemDetail},
)
def acknowledge_monitor_incident(
    request: HttpRequest,
    incident_id: int,
) -> MonitorIncidentOut | StaffProblem:
    problem = _permission_problem(
        request,
        "monitoring.view_monitorincident",
        "monitoring.change_monitorincident",
    )
    if problem:
        return problem
    incident = (
        MonitorIncident.objects.select_related(
            "monitor_check",
            "monitor_check__resource",
            "monitor_check__resource__client",
        )
        .filter(id=incident_id, monitor_check__in=_visible_checks(request))
        .first()
    )
    if incident is None:
        return _problem(404, "Monitoring incident not found.", "not_found")
    return _incident_out(acknowledge_incident(incident))

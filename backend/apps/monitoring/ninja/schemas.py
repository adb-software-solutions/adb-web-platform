import datetime

from ninja import Schema


class MonitorCheckCreateIn(Schema):
    resource_id: int
    name: str
    check_type: str
    severity: str = "error"
    target: str
    port: int | None = None
    expected_value: str = ""
    forbidden_value: str = ""
    interval_seconds: int = 300
    timeout_seconds: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    expiry_warning_days: int = 30
    credential_id: int | None = None


class MonitorCheckOut(Schema):
    id: int
    resource_id: int
    resource_name: str
    client_id: int | None
    client_name: str | None
    name: str
    check_type: str
    severity: str
    enabled: bool
    target: str
    port: int | None
    status: str
    consecutive_failures: int
    consecutive_successes: int
    last_checked_at: datetime.datetime | None
    next_run_at: datetime.datetime | None
    last_duration_ms: int | None
    last_message: str


class MonitorIncidentOut(Schema):
    id: int
    check_id: int
    check_name: str
    resource_id: int
    resource_name: str
    client_id: int | None
    client_name: str | None
    status: str
    severity: str
    opened_at: datetime.datetime
    acknowledged_at: datetime.datetime | None
    resolved_at: datetime.datetime | None
    failure_count: int
    summary: str


class MonitoringOverviewOut(Schema):
    total_checks: int
    healthy_checks: int
    degraded_checks: int
    failing_checks: int
    pending_checks: int
    open_incidents: int
    checks: list[MonitorCheckOut]
    incidents: list[MonitorIncidentOut]

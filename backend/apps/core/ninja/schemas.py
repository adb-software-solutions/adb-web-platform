from datetime import date, datetime

from ninja import Schema
from pydantic import Field


class BrandOut(Schema):
    id: int
    name: str
    slug: str
    domain: str
    is_active: bool


class DashboardWidgetPreferenceIn(Schema):
    key: str
    span: int


class DashboardWidgetPreferenceOut(DashboardWidgetPreferenceIn):
    pass


class DashboardPreferencesIn(Schema):
    layout: list[DashboardWidgetPreferenceIn] = Field(default_factory=list)


class DashboardWidgetOptionOut(Schema):
    key: str
    title: str
    description: str
    default_span: int


class DashboardTaskOut(Schema):
    id: int
    title: str
    status: str
    priority: int
    due_date: date | None
    client_name: str | None = None
    project_name: str | None = None


class DashboardTaskWidgetOut(Schema):
    open_count: int
    overdue_count: int
    today_count: int
    items: list[DashboardTaskOut] = Field(default_factory=list)


class DashboardTicketOut(Schema):
    id: int
    reference: str
    subject: str
    status: str
    priority: str
    queue_name: str
    client_name: str | None = None
    last_message_at: datetime | None = None


class DashboardTicketWidgetOut(Schema):
    mine_count: int
    unassigned_count: int
    active_count: int
    items: list[DashboardTicketOut] = Field(default_factory=list)


class DashboardTimerOut(Schema):
    running: bool
    started_at: datetime | None = None
    description: str = ""
    context_label: str = ""
    hours_this_week: float = 0.0


class DashboardLeadOut(Schema):
    id: int
    name: str
    company: str
    status: str
    brand: str
    created_at: datetime


class DashboardLeadWidgetOut(Schema):
    open_count: int
    items: list[DashboardLeadOut] = Field(default_factory=list)


class DashboardProjectOut(Schema):
    id: int
    name: str
    status: str
    client_name: str | None = None
    end_date: date | None = None


class DashboardProjectWidgetOut(Schema):
    current_count: int
    items: list[DashboardProjectOut] = Field(default_factory=list)


class DashboardIncidentOut(Schema):
    id: int
    check_name: str
    resource_name: str
    severity: str
    status: str
    summary: str
    opened_at: datetime


class DashboardTechnicalHealthOut(Schema):
    active_incident_count: int
    failing_check_count: int
    items: list[DashboardIncidentOut] = Field(default_factory=list)


class DashboardAgendaOut(Schema):
    today_count: int
    next_seven_days_count: int
    items: list[DashboardTaskOut] = Field(default_factory=list)


class DashboardActivityOut(Schema):
    id: int
    action: str
    target_label: str
    created_at: datetime


class DashboardWorkspaceOut(Schema):
    layout: list[DashboardWidgetPreferenceOut] = Field(default_factory=list)
    available_widgets: list[DashboardWidgetOptionOut] = Field(default_factory=list)
    my_tasks: DashboardTaskWidgetOut | None = None
    my_tickets: DashboardTicketWidgetOut | None = None
    active_timer: DashboardTimerOut | None = None
    lead_follow_up: DashboardLeadWidgetOut | None = None
    current_projects: DashboardProjectWidgetOut | None = None
    technical_health: DashboardTechnicalHealthOut | None = None
    agenda: DashboardAgendaOut | None = None
    recent_activity: list[DashboardActivityOut] | None = None

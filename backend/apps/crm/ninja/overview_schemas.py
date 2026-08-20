from datetime import datetime

from ninja import Schema


class LeadOverviewItemOut(Schema):
    id: int
    name: str
    company: str
    email: str
    status: str
    outcome: str
    source: str
    brand: str
    assigned_to_name: str | None
    converted_at: datetime | None
    created_at: datetime


class LeadOverviewStatsOut(Schema):
    active: int
    mine: int
    unassigned: int
    new_last_30_days: int


class LeadOverviewOut(Schema):
    items: list[LeadOverviewItemOut]
    stats: LeadOverviewStatsOut
    page: int
    page_size: int
    total: int
    total_pages: int

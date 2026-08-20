import datetime
import decimal

from ninja import Schema


class TimeReportClientOut(Schema):
    client_id: int
    client_name: str
    tracked_hours: decimal.Decimal
    billable_hours: decimal.Decimal
    non_billable_hours: decimal.Decimal
    entry_count: int
    project_count: int


class TimeReportDayOut(Schema):
    date: datetime.date
    tracked_hours: decimal.Decimal
    billable_hours: decimal.Decimal


class TimeReportEntryOut(Schema):
    id: int
    date: datetime.date
    duration_hours: decimal.Decimal
    description: str
    billable: bool
    entry_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    project_id: int | None
    project_name: str | None
    task_id: int | None
    task_title: str | None
    ticket_id: int | None
    ticket_reference: str | None
    ticket_subject: str | None
    user_name: str | None


class TimeReportEntriesOut(Schema):
    period: str
    date_from: datetime.date
    date_to: datetime.date
    tracked_hours: decimal.Decimal
    billable_hours: decimal.Decimal
    non_billable_hours: decimal.Decimal
    total: int
    page: int
    page_size: int
    items: list[TimeReportEntryOut]


class TimeReportSummaryOut(Schema):
    period: str
    date_from: datetime.date
    date_to: datetime.date
    tracked_hours: decimal.Decimal
    billable_hours: decimal.Decimal
    non_billable_hours: decimal.Decimal
    client_hours: decimal.Decimal
    internal_hours: decimal.Decimal
    entry_count: int
    clients: list[TimeReportClientOut]
    daily: list[TimeReportDayOut]

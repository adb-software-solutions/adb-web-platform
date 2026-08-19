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

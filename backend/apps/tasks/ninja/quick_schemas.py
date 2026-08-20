from datetime import date
from uuid import UUID

from ninja import Schema


class TaskQuickUpdateIn(Schema):
    title: str | None = None
    description: str | None = None
    priority: int | None = None
    start_date: date | None = None
    due_date: date | None = None
    assigned_to_id: UUID | None = None

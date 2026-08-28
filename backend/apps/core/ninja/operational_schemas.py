from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Schema

NotificationCategory = Literal[
    "task",
    "ticket",
    "credential",
    "monitoring",
    "security",
    "calendar",
    "general",
]
NotificationSeverity = Literal["info", "warning", "critical"]


class ActivityItemOut(Schema):
    id: int
    action: str
    actor_name: str
    target_type: str
    target_id: str
    target_label: str
    client_id: int | None
    resource_id: int | None
    metadata: dict[str, object]
    ip_address: str | None
    user_agent: str
    occurred_at: datetime


class ActivityPageOut(Schema):
    items: list[ActivityItemOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    metadata_visible: bool


class NotificationOut(Schema):
    id: int
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    body: str
    href: str
    client_id: int | None
    resource_id: int | None
    read_at: datetime | None
    created_at: datetime


class NotificationListOut(Schema):
    items: list[NotificationOut]
    unread_count: int


class NotificationCountOut(Schema):
    unread_count: int


class NotificationActionOut(Schema):
    id: int
    read_at: datetime | None
    dismissed: bool

from typing import Literal

from ninja import Schema

from .schemas import TicketListItemOut

TicketFocusView = Literal[
    "my",
    "unassigned",
    "active",
    "waiting_customer",
    "resolved",
    "closed",
    "all",
]
TicketSort = Literal[
    "operational",
    "updated_desc",
    "updated_asc",
    "priority_desc",
    "priority_asc",
    "created_desc",
    "created_asc",
    "subject_asc",
    "subject_desc",
]


class TicketFocusCountsOut(Schema):
    mine: int
    unassigned: int
    active: int
    waiting_customer: int


class TicketFocusQueueOut(Schema):
    id: int
    name: str
    brand_name: str | None
    active_count: int
    is_default: bool


class TicketFocusPageOut(Schema):
    view: TicketFocusView
    items: list[TicketListItemOut]
    counts: TicketFocusCountsOut
    queues: list[TicketFocusQueueOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class TicketQueuePreferencesIn(Schema):
    queue_ids: list[int]


class TicketQueuePreferencesOut(Schema):
    queue_ids: list[int]
    uses_all_accessible_queues: bool

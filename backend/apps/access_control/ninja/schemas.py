from datetime import datetime

from ninja import Schema
from pydantic import EmailStr, Field


class StaffUserSummaryOut(Schema):
    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    email_verified: bool
    date_joined: datetime
    last_login: datetime | None = None
    group_names: list[str] = Field(default_factory=list)


class StaffUserListOut(Schema):
    items: list[StaffUserSummaryOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    active_count: int
    inactive_count: int


class CapabilityOptionOut(Schema):
    id: int
    code: str
    name: str
    app_label: str
    model: str
    sensitive: bool = False


class EffectiveCapabilityOut(Schema):
    code: str
    name: str
    sensitive: bool = False
    sources: list[str] = Field(default_factory=list)


class GroupOptionOut(Schema):
    id: int
    name: str
    permission_ids: list[int] = Field(default_factory=list)


class ClientAccessOptionOut(Schema):
    id: int
    name: str
    company: str
    status: str


class TicketQueueAccessOptionOut(Schema):
    id: int
    name: str
    key: str
    brand_name: str | None = None
    enabled: bool


class StaffAccessOptionsOut(Schema):
    groups: list[GroupOptionOut]
    capabilities: list[CapabilityOptionOut]
    clients: list[ClientAccessOptionOut]
    ticket_queues: list[TicketQueueAccessOptionOut]


class ObjectAccessScopeOut(Schema):
    all: bool = False
    ids: list[int] = Field(default_factory=list)


class StaffAccessDetailOut(Schema):
    group_ids: list[int] = Field(default_factory=list)
    direct_permission_ids: list[int] = Field(default_factory=list)
    effective_permissions: list[EffectiveCapabilityOut] = Field(default_factory=list)
    clients: ObjectAccessScopeOut = Field(default_factory=ObjectAccessScopeOut)
    ticket_queues: ObjectAccessScopeOut = Field(default_factory=ObjectAccessScopeOut)
    default_ticket_queue_ids: list[int] = Field(default_factory=list)


class StaffUserDetailOut(StaffUserSummaryOut):
    access: StaffAccessDetailOut
    can_manage: bool = False


class StaffAccessUpdateIn(Schema):
    group_ids: list[int] = Field(default_factory=list)
    direct_permission_ids: list[int] = Field(default_factory=list)
    all_clients: bool = False
    client_ids: list[int] = Field(default_factory=list)
    all_ticket_queues: bool = False
    ticket_queue_ids: list[int] = Field(default_factory=list)
    default_ticket_queue_ids: list[int] = Field(default_factory=list)


class StaffInviteIn(StaffAccessUpdateIn):
    email: EmailStr
    first_name: str
    last_name: str


class StaffInviteOut(Schema):
    user: StaffUserDetailOut
    invitation_email_sent: bool


class StaffStatusOut(Schema):
    user: StaffUserDetailOut
    message: str
    success: bool = True

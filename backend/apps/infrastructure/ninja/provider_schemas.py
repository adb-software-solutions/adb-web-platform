from datetime import datetime
from typing import Literal

from ninja import Schema

ProviderActiveFilter = Literal["active", "inactive", "all"]
ProviderAccountLifecycleFilter = Literal[
    "current",
    "all",
    "planned",
    "active",
    "maintenance",
    "deprecated",
    "retired",
    "archived",
]
ProviderAccountOwnershipFilter = Literal["all", "internal", "client"]


class ProviderCategoryOut(Schema):
    value: str
    label: str


class ProviderClientOptionOut(Schema):
    id: int
    name: str


class ServiceProviderSummaryOut(Schema):
    id: int
    name: str
    slug: str
    category: str
    website_url: str
    support_url: str
    status_page_url: str
    documentation_url: str
    is_active: bool
    account_count: int
    updated_at: datetime


class ServiceProviderDetailOut(ServiceProviderSummaryOut):
    notes: str
    created_at: datetime


class ServiceProviderPageOut(Schema):
    items: list[ServiceProviderSummaryOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class ServiceProviderCreateIn(Schema):
    name: str
    category: str
    website_url: str = ""
    support_url: str = ""
    status_page_url: str = ""
    documentation_url: str = ""
    notes: str = ""


class ServiceProviderUpdateIn(Schema):
    name: str | None = None
    category: str | None = None
    website_url: str | None = None
    support_url: str | None = None
    status_page_url: str | None = None
    documentation_url: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ProviderAccountSummaryOut(Schema):
    id: int
    resource_id: int
    name: str
    provider_id: int
    provider_name: str
    provider_category: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    account_identifier: str
    tenant_id: str
    project_id: str
    portal_url: str
    default_region: str
    support_plan: str
    billing_reference: str
    updated_at: datetime


class ProviderAccountDetailOut(ProviderAccountSummaryOut):
    description: str
    is_portal_visible: bool
    created_at: datetime


class ProviderAccountPageOut(Schema):
    items: list[ProviderAccountSummaryOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class ProviderAccountCreateIn(Schema):
    name: str
    provider_id: int
    ownership_type: Literal["internal", "client"]
    client_id: int | None = None
    lifecycle_status: str = "active"
    environment: str = "not_applicable"
    criticality: str = "normal"
    description: str = ""
    account_identifier: str = ""
    tenant_id: str = ""
    project_id: str = ""
    portal_url: str = ""
    default_region: str = ""
    support_plan: str = ""
    billing_reference: str = ""


class ProviderAccountUpdateIn(Schema):
    name: str | None = None
    provider_id: int | None = None
    lifecycle_status: str | None = None
    environment: str | None = None
    criticality: str | None = None
    description: str | None = None
    account_identifier: str | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    portal_url: str | None = None
    default_region: str | None = None
    support_plan: str | None = None
    billing_reference: str | None = None


class ProviderOptionsOut(Schema):
    categories: list[ProviderCategoryOut]
    clients: list[ProviderClientOptionOut]
    providers: list[ServiceProviderSummaryOut]

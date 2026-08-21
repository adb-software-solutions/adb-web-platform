from __future__ import annotations

from typing import Literal

from ninja import Schema

LegacyResourceType = Literal[
    "server",
    "database",
    "website",
    "domain",
    "ssl_certificate",
    "licence",
    "application",
    "mobile_app",
    "api",
    "bot",
    "email_system",
]
LegacyReconciliationStatus = Literal["unlinked", "linked", "all"]
ReconciliationOwnership = Literal["internal", "client"]
ReconciliationLifecycle = Literal[
    "planned",
    "active",
    "maintenance",
    "deprecated",
    "retired",
    "archived",
]
ReconciliationEnvironment = Literal[
    "production",
    "staging",
    "development",
    "testing",
    "shared",
    "not_applicable",
]
ReconciliationCriticality = Literal["low", "normal", "high", "critical"]


class LegacyReconciliationItemOut(Schema):
    legacy_type: str
    legacy_type_label: str
    legacy_id: int
    name: str
    resource_id: int | None
    ownership_type: str | None
    client_id: int | None
    client_name: str | None
    lifecycle_status: str | None
    environment: str | None
    criticality: str | None


class LegacyReconciliationPageOut(Schema):
    items: list[LegacyReconciliationItemOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    total_legacy: int
    linked: int
    unlinked: int


class ReconciliationClientOptionOut(Schema):
    id: int
    name: str
    status: str


class LegacyReconciliationOptionsOut(Schema):
    clients: list[ReconciliationClientOptionOut]
    legacy_types: list[str]
    lifecycle_statuses: list[str]
    environments: list[str]
    criticalities: list[str]


class ReconcileLegacyResourceIn(Schema):
    ownership_type: ReconciliationOwnership
    client_id: int | None = None
    name: str | None = None
    lifecycle_status: ReconciliationLifecycle = "active"
    environment: ReconciliationEnvironment = "not_applicable"
    criticality: ReconciliationCriticality = "normal"


class ReconciledResourceOut(Schema):
    resource_id: int
    name: str
    resource_type: str
    ownership_type: str
    client_id: int | None

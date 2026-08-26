from datetime import datetime

from ninja import Schema

from .specialist_schemas import (
    ClientOptionOut,
    ProviderAccountOptionOut,
    StructuredResourceIn,
    StructuredResourceUpdateIn,
)


class ServerOptionOut(Schema):
    resource_id: int
    name: str
    hostname: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class DatabaseInstanceOptionOut(Schema):
    resource_id: int
    name: str
    engine: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class ApplicationOptionOut(Schema):
    resource_id: int
    name: str
    application_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class SourceRepositoryOptionOut(Schema):
    resource_id: int
    name: str
    repository_name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class DataApplicationSpecialistOptionsOut(Schema):
    clients: list[ClientOptionOut]
    provider_accounts: list[ProviderAccountOptionOut]
    servers: list[ServerOptionOut]
    database_instances: list[DatabaseInstanceOptionOut]
    applications: list[ApplicationOptionOut]
    source_repositories: list[SourceRepositoryOptionOut]


class DatabaseInstanceCreateIn(StructuredResourceIn):
    engine: str
    engine_version: str = ""
    hosting_type: str = "managed"
    server_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    endpoint: str = ""
    port: int | None = None
    region: str = ""
    zone: str = ""
    tls_mode: str = "unknown"
    high_availability: bool | None = None
    replica_count: int | None = None
    backup_enabled: bool | None = None
    maintenance_window: str = ""


class DatabaseInstanceUpdateIn(StructuredResourceUpdateIn):
    engine: str
    engine_version: str = ""
    hosting_type: str
    server_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    endpoint: str = ""
    port: int | None = None
    region: str = ""
    zone: str = ""
    tls_mode: str
    high_availability: bool | None = None
    replica_count: int | None = None
    backup_enabled: bool | None = None
    maintenance_window: str = ""


class DatabaseInstanceOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    engine: str
    engine_version: str
    hosting_type: str
    server_resource_id: int | None
    server_name: str | None
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    provider_resource_id: str
    endpoint: str
    port: int | None
    region: str
    zone: str
    tls_mode: str
    high_availability: bool | None
    replica_count: int | None
    backup_enabled: bool | None
    maintenance_window: str
    updated_at: datetime


class LogicalDatabaseCreateIn(StructuredResourceIn):
    instance_resource_id: int
    database_name: str
    purpose: str = ""
    default_schema: str = ""
    charset: str = ""
    collation: str = ""


class LogicalDatabaseUpdateIn(StructuredResourceUpdateIn):
    instance_resource_id: int
    database_name: str
    purpose: str = ""
    default_schema: str = ""
    charset: str = ""
    collation: str = ""


class LogicalDatabaseOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    instance_resource_id: int
    instance_name: str
    database_name: str
    purpose: str
    default_schema: str
    charset: str
    collation: str
    updated_at: datetime


class ApplicationCreateIn(StructuredResourceIn):
    application_type: str = "web_app"
    owner_team: str = ""
    primary_language: str = ""
    framework: str = ""


class ApplicationUpdateIn(StructuredResourceUpdateIn):
    application_type: str
    owner_team: str = ""
    primary_language: str = ""
    framework: str = ""


class ApplicationRepositoryLinkCreateIn(Schema):
    repository_resource_id: int
    role: str = "primary"
    path: str = ""
    notes: str = ""


class ApplicationRepositoryLinkOut(Schema):
    id: int
    repository_resource_id: int
    repository_name: str
    role: str
    path: str
    notes: str


class ApplicationOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    application_type: str
    owner_team: str
    primary_language: str
    framework: str
    repositories: list[ApplicationRepositoryLinkOut]
    updated_at: datetime


class ApplicationEnvironmentCreateIn(StructuredResourceIn):
    application_resource_id: int
    deployment_type: str = "server"
    server_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    runtime: str = ""
    runtime_version: str = ""
    release_version: str = ""
    region: str = ""
    branch_or_ref: str = ""
    automatic_deployments: bool | None = None


class ApplicationEnvironmentUpdateIn(StructuredResourceUpdateIn):
    application_resource_id: int
    deployment_type: str
    server_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    runtime: str = ""
    runtime_version: str = ""
    release_version: str = ""
    region: str = ""
    branch_or_ref: str = ""
    automatic_deployments: bool | None = None


class ApplicationEnvironmentOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    application_resource_id: int
    application_name: str
    deployment_type: str
    server_resource_id: int | None
    server_name: str | None
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    provider_resource_id: str
    runtime: str
    runtime_version: str
    release_version: str
    region: str
    branch_or_ref: str
    automatic_deployments: bool | None
    updated_at: datetime


class SourceRepositoryCreateIn(StructuredResourceIn):
    provider_account_resource_id: int | None = None
    web_url: str = ""
    clone_url: str = ""
    provider_repository_id: str = ""
    owner_name: str = ""
    repository_name: str
    default_branch: str = ""
    visibility: str = "private"
    is_fork: bool = False


class SourceRepositoryUpdateIn(StructuredResourceUpdateIn):
    provider_account_resource_id: int | None = None
    web_url: str = ""
    clone_url: str = ""
    provider_repository_id: str = ""
    owner_name: str = ""
    repository_name: str
    default_branch: str = ""
    visibility: str
    is_fork: bool = False


class SourceRepositoryOut(Schema):
    resource_id: int
    name: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    lifecycle_status: str
    environment: str
    criticality: str
    description: str
    provider_account_resource_id: int | None
    provider_account_name: str | None
    provider_name: str | None
    web_url: str
    clone_url: str
    provider_repository_id: str
    owner_name: str
    repository_name: str
    default_branch: str
    visibility: str
    is_fork: bool
    updated_at: datetime

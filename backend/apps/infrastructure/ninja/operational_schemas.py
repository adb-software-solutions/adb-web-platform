from datetime import datetime

from ninja import Schema

from .specialist_schemas import StructuredResourceIn, StructuredResourceUpdateIn


class OperationalMutationOut(Schema):
    resource_id: int


class OperationalOptionOut(Schema):
    resource_id: int
    name: str
    resource_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class OperationalOptionsOut(Schema):
    provider_accounts: list[OperationalOptionOut]
    servers: list[OperationalOptionOut]
    storages: list[OperationalOptionOut]
    clusters: list[OperationalOptionOut]
    namespaces: list[OperationalOptionOut]
    workloads: list[OperationalOptionOut]
    resources: list[OperationalOptionOut]


class StorageCreateIn(StructuredResourceIn):
    storage_type: str
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    region: str = ""
    capacity_gb: int | None = None
    filesystem: str = ""
    storage_class: str = ""
    mount_path: str = ""
    endpoint_url: str = ""
    encrypted: bool | None = None
    retention_notes: str = ""


class StorageUpdateIn(StructuredResourceUpdateIn):
    storage_type: str
    provider_account_resource_id: int | None = None
    provider_resource_id: str = ""
    region: str = ""
    capacity_gb: int | None = None
    filesystem: str = ""
    storage_class: str = ""
    mount_path: str = ""
    endpoint_url: str = ""
    encrypted: bool | None = None
    retention_notes: str = ""


class BackupPlanCreateIn(StructuredResourceIn):
    backup_type: str
    schedule: str = ""
    timezone: str = ""
    retention_days: int | None = None
    retention_copies: int | None = None
    destination_storage_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    encrypted: bool | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_restore_test_at: datetime | None = None
    source_resource_ids: list[int] = []
    recovery_notes: str = ""


class BackupPlanUpdateIn(StructuredResourceUpdateIn):
    backup_type: str
    schedule: str = ""
    timezone: str = ""
    retention_days: int | None = None
    retention_copies: int | None = None
    destination_storage_resource_id: int | None = None
    provider_account_resource_id: int | None = None
    encrypted: bool | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_restore_test_at: datetime | None = None
    source_resource_ids: list[int] = []
    recovery_notes: str = ""


class ContainerStackCreateIn(StructuredResourceIn):
    orchestrator: str
    host_resource_id: int | None = None
    project_name: str = ""
    orchestrator_version: str = ""
    compose_path: str = ""
    working_directory: str = ""
    management_url: str = ""
    notes: str = ""


class ContainerStackUpdateIn(StructuredResourceUpdateIn):
    orchestrator: str
    host_resource_id: int | None = None
    project_name: str = ""
    orchestrator_version: str = ""
    compose_path: str = ""
    working_directory: str = ""
    management_url: str = ""
    notes: str = ""


class ContainerServiceIn(Schema):
    name: str
    image: str = ""
    replicas: int | None = None
    ports: list[str] = []
    volumes: list[str] = []
    healthcheck: str = ""
    restart_policy: str = ""
    environment_notes: str = ""


class ContainerServiceOut(ContainerServiceIn):
    id: int


class KubernetesClusterCreateIn(StructuredResourceIn):
    provider_account_resource_id: int | None = None
    distribution: str = ""
    version: str = ""
    api_server_url: str = ""
    management_url: str = ""
    provider_cluster_id: str = ""
    region: str = ""
    node_count: int | None = None
    high_availability: bool | None = None
    upgrade_channel: str = ""
    notes: str = ""


class KubernetesClusterUpdateIn(StructuredResourceUpdateIn):
    provider_account_resource_id: int | None = None
    distribution: str = ""
    version: str = ""
    api_server_url: str = ""
    management_url: str = ""
    provider_cluster_id: str = ""
    region: str = ""
    node_count: int | None = None
    high_availability: bool | None = None
    upgrade_channel: str = ""
    notes: str = ""


class KubernetesNamespaceCreateIn(StructuredResourceIn):
    cluster_resource_id: int
    namespace: str
    purpose: str = ""
    resource_quota_summary: str = ""


class KubernetesNamespaceUpdateIn(StructuredResourceUpdateIn):
    cluster_resource_id: int
    namespace: str
    purpose: str = ""
    resource_quota_summary: str = ""


class KubernetesWorkloadCreateIn(StructuredResourceIn):
    namespace_resource_id: int
    workload_kind: str
    workload_name: str
    replicas_desired: int | None = None
    image_summary: str = ""
    selector_summary: str = ""
    service_account: str = ""
    notes: str = ""


class KubernetesWorkloadUpdateIn(StructuredResourceUpdateIn):
    namespace_resource_id: int
    workload_kind: str
    workload_name: str
    replicas_desired: int | None = None
    image_summary: str = ""
    selector_summary: str = ""
    service_account: str = ""
    notes: str = ""


class KubernetesServiceIn(Schema):
    name: str
    service_type: str
    workload_resource_id: int | None = None
    cluster_ip: str | None = None
    external_hostname: str = ""
    ports: list[str] = []


class KubernetesServiceOut(KubernetesServiceIn):
    id: int


class KubernetesIngressIn(Schema):
    name: str
    ingress_class: str = ""
    hosts: list[str] = []
    tls_enabled: bool = False
    target_service_id: int | None = None
    notes: str = ""


class KubernetesIngressOut(KubernetesIngressIn):
    id: int


class HelmReleaseIn(Schema):
    name: str
    chart: str
    chart_version: str = ""
    app_version: str = ""
    repository_url: str = ""
    status: str = ""
    values_summary: str = ""


class HelmReleaseOut(HelmReleaseIn):
    id: int


class KubernetesPersistentStorageIn(Schema):
    name: str
    storage_class: str = ""
    capacity_gb: int | None = None
    access_modes: list[str] = []
    volume_name: str = ""
    backing_storage_resource_id: int | None = None
    notes: str = ""


class KubernetesPersistentStorageOut(KubernetesPersistentStorageIn):
    id: int


class KubernetesNamespaceChildrenOut(Schema):
    services: list[KubernetesServiceOut]
    ingresses: list[KubernetesIngressOut]
    helm_releases: list[HelmReleaseOut]
    persistent_storage: list[KubernetesPersistentStorageOut]


class SystemServiceCreateIn(StructuredResourceIn):
    host_resource_id: int
    manager: str
    unit_name: str
    display_name: str = ""
    expected_state: str = ""
    startup_type: str = ""
    executable: str = ""
    config_path: str = ""
    working_directory: str = ""
    log_location: str = ""
    restart_policy: str = ""
    notes: str = ""


class SystemServiceUpdateIn(StructuredResourceUpdateIn):
    host_resource_id: int
    manager: str
    unit_name: str
    display_name: str = ""
    expected_state: str = ""
    startup_type: str = ""
    executable: str = ""
    config_path: str = ""
    working_directory: str = ""
    log_location: str = ""
    restart_policy: str = ""
    notes: str = ""


class ScheduledJobCreateIn(StructuredResourceIn):
    scheduler: str
    host_resource_id: int | None = None
    schedule_expression: str = ""
    timezone: str = ""
    command_summary: str = ""
    config_path: str = ""
    working_directory: str = ""
    run_as: str = ""
    enabled: bool = True
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    next_run_at: datetime | None = None
    notes: str = ""


class ScheduledJobUpdateIn(StructuredResourceUpdateIn):
    scheduler: str
    host_resource_id: int | None = None
    schedule_expression: str = ""
    timezone: str = ""
    command_summary: str = ""
    config_path: str = ""
    working_directory: str = ""
    run_as: str = ""
    enabled: bool = True
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    next_run_at: datetime | None = None
    notes: str = ""

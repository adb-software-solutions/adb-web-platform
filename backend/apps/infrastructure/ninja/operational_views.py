from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest
from ninja import Router

from apps.infrastructure.models import (
    BackupPlanProfile,
    BackupSource,
    ContainerStackProfile,
    InfrastructureResource,
    KubernetesClusterProfile,
    KubernetesNamespaceProfile,
    KubernetesWorkloadProfile,
    ProviderAccount,
    ScheduledJobProfile,
    StorageProfile,
    SystemServiceProfile,
)
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .operational_schemas import (
    BackupPlanCreateIn,
    BackupPlanUpdateIn,
    ContainerStackCreateIn,
    ContainerStackUpdateIn,
    KubernetesClusterCreateIn,
    KubernetesClusterUpdateIn,
    KubernetesNamespaceCreateIn,
    KubernetesNamespaceUpdateIn,
    KubernetesWorkloadCreateIn,
    KubernetesWorkloadUpdateIn,
    OperationalMutationOut,
    OperationalOptionOut,
    OperationalOptionsOut,
    ScheduledJobCreateIn,
    ScheduledJobUpdateIn,
    StorageCreateIn,
    StorageUpdateIn,
    SystemServiceCreateIn,
    SystemServiceUpdateIn,
)
from .specialist_views import (
    CURRENT_LIFECYCLE_STATUSES,
    StaffProblem,
    _new_resource,
    _permission_problem,
    _problem,
    _update_resource,
    _validation_problem,
)

operational_specialist_router = Router(tags=["admin-infrastructure-operations"])


def _visible_resources(request: HttpRequest) -> Any:
    return scope_infrastructure_resources_for_user(request.user)


def _visible_resource(
    request: HttpRequest,
    resource_id: int | None,
    resource_type: str | None = None,
) -> InfrastructureResource | None:
    if resource_id is None:
        return None
    resources = _visible_resources(request).filter(id=resource_id)
    if resource_type is not None:
        resources = resources.filter(resource_type=resource_type)
    return resources.select_related("client").first()


def _visible_provider_account(
    request: HttpRequest,
    resource_id: int | None,
) -> ProviderAccount | None:
    if resource_id is None:
        return None
    return (
        ProviderAccount.objects.select_related("resource", "resource__client", "provider")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _visible_storage(
    request: HttpRequest,
    resource_id: int | None,
) -> StorageProfile | None:
    if resource_id is None:
        return None
    return (
        StorageProfile.objects.select_related("resource", "resource__client")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _visible_cluster(
    request: HttpRequest,
    resource_id: int | None,
) -> KubernetesClusterProfile | None:
    if resource_id is None:
        return None
    return (
        KubernetesClusterProfile.objects.select_related("resource", "resource__client")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _visible_namespace(
    request: HttpRequest,
    resource_id: int | None,
) -> KubernetesNamespaceProfile | None:
    if resource_id is None:
        return None
    return (
        KubernetesNamespaceProfile.objects.select_related(
            "resource",
            "resource__client",
            "cluster__resource",
        )
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _option(resource: InfrastructureResource) -> OperationalOptionOut:
    return OperationalOptionOut(
        resource_id=resource.id,
        name=resource.name,
        resource_type=resource.resource_type,
        ownership_type=resource.ownership_type,
        client_id=resource.client_id,
        client_name=str(resource.client) if resource.client else None,
    )


def _same_scope(resource: InfrastructureResource, related: InfrastructureResource) -> bool:
    return (
        resource.ownership_type == related.ownership_type
        and resource.client_id == related.client_id
    )


def _populate(instance: Any, payload: Any, fields: tuple[str, ...]) -> None:
    for field in fields:
        value = getattr(payload, field)
        if isinstance(value, str):
            value = value.strip()
        setattr(instance, field, value)


def _sync_backup_sources(
    request: HttpRequest,
    plan: BackupPlanProfile,
    source_resource_ids: list[int],
) -> StaffProblem | None:
    source_ids = set(source_resource_ids)
    sources = list(
        _visible_resources(request)
        .filter(id__in=source_ids)
        .select_related("client")
        .order_by("id")
    )
    if len(sources) != len(source_ids):
        return _problem(404, "One or more backup source resources were not found.", "not_found")
    if any(not _same_scope(plan.resource, source) for source in sources):
        return _problem(
            400,
            "Backup source resources must use the same ownership scope as the backup plan.",
            "invalid_infrastructure",
        )
    plan.sources.exclude(source_resource_id__in=source_ids).delete()
    for source in sources:
        link, _ = BackupSource.objects.get_or_create(
            backup_plan=plan,
            source_resource=source,
        )
        link.full_clean()
    return None


@operational_specialist_router.get(
    "/infrastructure/operations/options",
    response={200: OperationalOptionsOut, 401: ProblemDetail, 403: ProblemDetail},
)
def operational_options(request: HttpRequest) -> OperationalOptionsOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.view_infrastructureresource")
    if problem:
        return problem
    visible = _visible_resources(request).filter(
        lifecycle_status__in=CURRENT_LIFECYCLE_STATUSES
    ).select_related("client")
    resources = list(visible.order_by("name", "id")[:2000])
    return OperationalOptionsOut(
        provider_accounts=[
            _option(item.resource)
            for item in ProviderAccount.objects.select_related("resource", "resource__client")
            .filter(resource__in=resources)
            .order_by("resource__name")
        ],
        servers=[
            _option(item)
            for item in resources
            if item.resource_type == InfrastructureResource.ResourceType.SERVER
        ],
        storages=[
            _option(item)
            for item in resources
            if item.resource_type == InfrastructureResource.ResourceType.STORAGE
        ],
        clusters=[
            _option(item)
            for item in resources
            if item.resource_type == InfrastructureResource.ResourceType.KUBERNETES_CLUSTER
        ],
        namespaces=[
            _option(item)
            for item in resources
            if item.resource_type == InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE
        ],
        workloads=[
            _option(item)
            for item in resources
            if item.resource_type == InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD
        ],
        resources=[_option(item) for item in resources],
    )


@operational_specialist_router.post(
    "/infrastructure/operations/storage",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_storage(
    request: HttpRequest,
    payload: StorageCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_storageprofile",
    )
    if problem:
        return problem
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.STORAGE,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = StorageProfile(resource=resource, provider_account=provider)
            _populate(
                profile,
                payload,
                (
                    "storage_type",
                    "provider_resource_id",
                    "region",
                    "capacity_gb",
                    "filesystem",
                    "storage_class",
                    "mount_path",
                    "endpoint_url",
                    "encrypted",
                    "retention_notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/storage/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_storage(
    request: HttpRequest,
    resource_id: int,
    payload: StorageUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_storageprofile",
    )
    if problem:
        return problem
    profile = _visible_storage(request, resource_id)
    if profile is None:
        return _problem(404, "Storage resource not found.", "not_found")
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    profile.provider_account = provider
    _populate(
        profile,
        payload,
        (
            "storage_type",
            "provider_resource_id",
            "region",
            "capacity_gb",
            "filesystem",
            "storage_class",
            "mount_path",
            "endpoint_url",
            "encrypted",
            "retention_notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/backup-plans",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_backup_plan(
    request: HttpRequest,
    payload: BackupPlanCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_backupplanprofile",
    )
    if problem:
        return problem
    destination = _visible_storage(request, payload.destination_storage_resource_id)
    if payload.destination_storage_resource_id is not None and destination is None:
        return _problem(404, "Backup destination storage not found.", "not_found")
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.BACKUP_PLAN,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = BackupPlanProfile(
                resource=resource,
                destination_storage=destination,
                provider_account=provider,
            )
            _populate(
                profile,
                payload,
                (
                    "backup_type",
                    "schedule",
                    "timezone",
                    "retention_days",
                    "retention_copies",
                    "encrypted",
                    "last_success_at",
                    "last_failure_at",
                    "last_restore_test_at",
                    "recovery_notes",
                ),
            )
            profile.full_clean()
            profile.save()
            source_problem = _sync_backup_sources(request, profile, payload.source_resource_ids)
            if source_problem:
                transaction.set_rollback(True)
                return source_problem
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/backup-plans/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_backup_plan(
    request: HttpRequest,
    resource_id: int,
    payload: BackupPlanUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_backupplanprofile",
    )
    if problem:
        return problem
    profile = (
        BackupPlanProfile.objects.select_related("resource", "destination_storage__resource")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )
    if profile is None:
        return _problem(404, "Backup plan not found.", "not_found")
    destination = _visible_storage(request, payload.destination_storage_resource_id)
    if payload.destination_storage_resource_id is not None and destination is None:
        return _problem(404, "Backup destination storage not found.", "not_found")
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    profile.destination_storage = destination
    profile.provider_account = provider
    _populate(
        profile,
        payload,
        (
            "backup_type",
            "schedule",
            "timezone",
            "retention_days",
            "retention_copies",
            "encrypted",
            "last_success_at",
            "last_failure_at",
            "last_restore_test_at",
            "recovery_notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
            source_problem = _sync_backup_sources(request, profile, payload.source_resource_ids)
            if source_problem:
                transaction.set_rollback(True)
                return source_problem
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


def _container_stack(
    request: HttpRequest,
    resource_id: int,
) -> ContainerStackProfile | None:
    return (
        ContainerStackProfile.objects.select_related("resource", "resource__client", "host_resource")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


@operational_specialist_router.post(
    "/infrastructure/operations/container-stacks",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_container_stack(
    request: HttpRequest,
    payload: ContainerStackCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_containerstackprofile",
    )
    if problem:
        return problem
    host = _visible_resource(request, payload.host_resource_id, InfrastructureResource.ResourceType.SERVER)
    if payload.host_resource_id is not None and host is None:
        return _problem(404, "Container host server not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.CONTAINER_STACK,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = ContainerStackProfile(resource=resource, host_resource=host)
            _populate(
                profile,
                payload,
                (
                    "orchestrator",
                    "project_name",
                    "orchestrator_version",
                    "compose_path",
                    "working_directory",
                    "management_url",
                    "notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/container-stacks/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_container_stack(
    request: HttpRequest,
    resource_id: int,
    payload: ContainerStackUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_containerstackprofile",
    )
    if problem:
        return problem
    profile = _container_stack(request, resource_id)
    if profile is None:
        return _problem(404, "Container stack not found.", "not_found")
    host = _visible_resource(request, payload.host_resource_id, InfrastructureResource.ResourceType.SERVER)
    if payload.host_resource_id is not None and host is None:
        return _problem(404, "Container host server not found.", "not_found")
    profile.host_resource = host
    _populate(
        profile,
        payload,
        (
            "orchestrator",
            "project_name",
            "orchestrator_version",
            "compose_path",
            "working_directory",
            "management_url",
            "notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/kubernetes/clusters",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_cluster(
    request: HttpRequest,
    payload: KubernetesClusterCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_kubernetesclusterprofile",
    )
    if problem:
        return problem
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.KUBERNETES_CLUSTER,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = KubernetesClusterProfile(resource=resource, provider_account=provider)
            _populate(
                profile,
                payload,
                (
                    "distribution",
                    "version",
                    "api_server_url",
                    "management_url",
                    "provider_cluster_id",
                    "region",
                    "node_count",
                    "high_availability",
                    "upgrade_channel",
                    "notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/kubernetes/clusters/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_cluster(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesClusterUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_kubernetesclusterprofile",
    )
    if problem:
        return problem
    profile = _visible_cluster(request, resource_id)
    if profile is None:
        return _problem(404, "Kubernetes cluster not found.", "not_found")
    provider = _visible_provider_account(request, payload.provider_account_resource_id)
    if payload.provider_account_resource_id is not None and provider is None:
        return _problem(404, "Provider account not found.", "not_found")
    profile.provider_account = provider
    _populate(
        profile,
        payload,
        (
            "distribution",
            "version",
            "api_server_url",
            "management_url",
            "provider_cluster_id",
            "region",
            "node_count",
            "high_availability",
            "upgrade_channel",
            "notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/kubernetes/namespaces",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_namespace(
    request: HttpRequest,
    payload: KubernetesNamespaceCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_kubernetesnamespaceprofile",
    )
    if problem:
        return problem
    cluster = _visible_cluster(request, payload.cluster_resource_id)
    if cluster is None:
        return _problem(404, "Kubernetes cluster not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.KUBERNETES_NAMESPACE,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = KubernetesNamespaceProfile(resource=resource, cluster=cluster)
            _populate(profile, payload, ("namespace", "purpose", "resource_quota_summary"))
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_namespace(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesNamespaceUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_kubernetesnamespaceprofile",
    )
    if problem:
        return problem
    profile = _visible_namespace(request, resource_id)
    if profile is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    cluster = _visible_cluster(request, payload.cluster_resource_id)
    if cluster is None:
        return _problem(404, "Kubernetes cluster not found.", "not_found")
    profile.cluster = cluster
    _populate(profile, payload, ("namespace", "purpose", "resource_quota_summary"))
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/kubernetes/workloads",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_workload(
    request: HttpRequest,
    payload: KubernetesWorkloadCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_kubernetesworkloadprofile",
    )
    if problem:
        return problem
    namespace = _visible_namespace(request, payload.namespace_resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.KUBERNETES_WORKLOAD,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = KubernetesWorkloadProfile(resource=resource, namespace=namespace)
            _populate(
                profile,
                payload,
                (
                    "workload_kind",
                    "workload_name",
                    "replicas_desired",
                    "image_summary",
                    "selector_summary",
                    "service_account",
                    "notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/kubernetes/workloads/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_workload(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesWorkloadUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_kubernetesworkloadprofile",
    )
    if problem:
        return problem
    profile = (
        KubernetesWorkloadProfile.objects.select_related("resource", "namespace__resource")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )
    if profile is None:
        return _problem(404, "Kubernetes workload not found.", "not_found")
    namespace = _visible_namespace(request, payload.namespace_resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    profile.namespace = namespace
    _populate(
        profile,
        payload,
        (
            "workload_kind",
            "workload_name",
            "replicas_desired",
            "image_summary",
            "selector_summary",
            "service_account",
            "notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/system-services",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_system_service(
    request: HttpRequest,
    payload: SystemServiceCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_systemserviceprofile",
    )
    if problem:
        return problem
    host = _visible_resource(request, payload.host_resource_id, InfrastructureResource.ResourceType.SERVER)
    if host is None:
        return _problem(404, "System service host server not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.SYSTEM_SERVICE,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = SystemServiceProfile(resource=resource, host_resource=host)
            _populate(
                profile,
                payload,
                (
                    "manager",
                    "unit_name",
                    "display_name",
                    "expected_state",
                    "startup_type",
                    "executable",
                    "config_path",
                    "working_directory",
                    "log_location",
                    "restart_policy",
                    "notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/system-services/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_system_service(
    request: HttpRequest,
    resource_id: int,
    payload: SystemServiceUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_systemserviceprofile",
    )
    if problem:
        return problem
    profile = (
        SystemServiceProfile.objects.select_related("resource", "host_resource")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )
    if profile is None:
        return _problem(404, "System service not found.", "not_found")
    host = _visible_resource(request, payload.host_resource_id, InfrastructureResource.ResourceType.SERVER)
    if host is None:
        return _problem(404, "System service host server not found.", "not_found")
    profile.host_resource = host
    _populate(
        profile,
        payload,
        (
            "manager",
            "unit_name",
            "display_name",
            "expected_state",
            "startup_type",
            "executable",
            "config_path",
            "working_directory",
            "log_location",
            "restart_policy",
            "notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)


@operational_specialist_router.post(
    "/infrastructure/operations/scheduled-jobs",
    response={
        201: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_scheduled_job(
    request: HttpRequest,
    payload: ScheduledJobCreateIn,
) -> tuple[int, OperationalMutationOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_infrastructureresource",
        "infrastructure.add_scheduledjobprofile",
    )
    if problem:
        return problem
    host = _visible_resource(request, payload.host_resource_id)
    if payload.host_resource_id is not None and host is None:
        return _problem(404, "Scheduled job host/context not found.", "not_found")
    try:
        with transaction.atomic():
            resource, resource_problem = _new_resource(
                request,
                payload,
                InfrastructureResource.ResourceType.SCHEDULED_JOB,
            )
            if resource_problem:
                return resource_problem
            assert resource is not None
            profile = ScheduledJobProfile(resource=resource, host_resource=host)
            _populate(
                profile,
                payload,
                (
                    "scheduler",
                    "schedule_expression",
                    "timezone",
                    "command_summary",
                    "config_path",
                    "working_directory",
                    "run_as",
                    "enabled",
                    "last_success_at",
                    "last_failure_at",
                    "next_run_at",
                    "notes",
                ),
            )
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, OperationalMutationOut(resource_id=resource.id)


@operational_specialist_router.put(
    "/infrastructure/operations/scheduled-jobs/{resource_id}",
    response={
        200: OperationalMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_scheduled_job(
    request: HttpRequest,
    resource_id: int,
    payload: ScheduledJobUpdateIn,
) -> OperationalMutationOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_scheduledjobprofile",
    )
    if problem:
        return problem
    profile = (
        ScheduledJobProfile.objects.select_related("resource", "host_resource")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )
    if profile is None:
        return _problem(404, "Scheduled job not found.", "not_found")
    host = _visible_resource(request, payload.host_resource_id)
    if payload.host_resource_id is not None and host is None:
        return _problem(404, "Scheduled job host/context not found.", "not_found")
    profile.host_resource = host
    _populate(
        profile,
        payload,
        (
            "scheduler",
            "schedule_expression",
            "timezone",
            "command_summary",
            "config_path",
            "working_directory",
            "run_as",
            "enabled",
            "last_success_at",
            "last_failure_at",
            "next_run_at",
            "notes",
        ),
    )
    try:
        with transaction.atomic():
            resource_problem = _update_resource(request, profile.resource, payload)
            if resource_problem:
                return resource_problem
            profile.full_clean()
            profile.save()
    except ValidationError as error:
        return _validation_problem(error)
    return OperationalMutationOut(resource_id=resource_id)

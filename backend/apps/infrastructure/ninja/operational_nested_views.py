from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import Router

from apps.infrastructure.models import (
    ContainerService,
    ContainerStackProfile,
    HelmRelease,
    KubernetesIngress,
    KubernetesNamespaceProfile,
    KubernetesPersistentStorage,
    KubernetesService,
    KubernetesWorkloadProfile,
    StorageProfile,
)
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from authentication.ninja.schemas import ProblemDetail

from .operational_schemas import (
    ContainerServiceIn,
    ContainerServiceOut,
    HelmReleaseIn,
    HelmReleaseOut,
    KubernetesIngressIn,
    KubernetesIngressOut,
    KubernetesNamespaceChildrenOut,
    KubernetesPersistentStorageIn,
    KubernetesPersistentStorageOut,
    KubernetesServiceIn,
    KubernetesServiceOut,
)
from .specialist_views import StaffProblem, _permission_problem, _problem, _validation_problem

operational_nested_router = Router(tags=["admin-infrastructure-operation-children"])


def _visible_resources(request: HttpRequest) -> Any:
    return scope_infrastructure_resources_for_user(request.user)


def _stack(request: HttpRequest, resource_id: int) -> ContainerStackProfile | None:
    return (
        ContainerStackProfile.objects.select_related("resource", "resource__client")
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _namespace(
    request: HttpRequest,
    resource_id: int,
) -> KubernetesNamespaceProfile | None:
    return (
        KubernetesNamespaceProfile.objects.select_related(
            "resource",
            "resource__client",
            "cluster__resource",
        )
        .filter(resource__in=_visible_resources(request), resource_id=resource_id)
        .first()
    )


def _container_service_out(service: ContainerService) -> ContainerServiceOut:
    return ContainerServiceOut(
        id=service.id,
        name=service.name,
        image=service.image,
        replicas=service.replicas,
        ports=[str(value) for value in service.ports],
        volumes=[str(value) for value in service.volumes],
        healthcheck=service.healthcheck,
        restart_policy=service.restart_policy,
        environment_notes=service.environment_notes,
    )


def _kubernetes_service_out(service: KubernetesService) -> KubernetesServiceOut:
    return KubernetesServiceOut(
        id=service.id,
        name=service.name,
        service_type=service.service_type,
        workload_resource_id=service.workload.resource_id if service.workload else None,
        cluster_ip=service.cluster_ip,
        external_hostname=service.external_hostname,
        ports=[str(value) for value in service.ports],
    )


def _ingress_out(ingress: KubernetesIngress) -> KubernetesIngressOut:
    return KubernetesIngressOut(
        id=ingress.id,
        name=ingress.name,
        ingress_class=ingress.ingress_class,
        hosts=[str(value) for value in ingress.hosts],
        tls_enabled=ingress.tls_enabled,
        target_service_id=ingress.target_service_id,
        notes=ingress.notes,
    )


def _helm_out(release: HelmRelease) -> HelmReleaseOut:
    return HelmReleaseOut(
        id=release.id,
        name=release.name,
        chart=release.chart,
        chart_version=release.chart_version,
        app_version=release.app_version,
        repository_url=release.repository_url,
        status=release.status,
        values_summary=release.values_summary,
    )


def _persistent_storage_out(
    item: KubernetesPersistentStorage,
) -> KubernetesPersistentStorageOut:
    return KubernetesPersistentStorageOut(
        id=item.id,
        name=item.name,
        storage_class=item.storage_class,
        capacity_gb=item.capacity_gb,
        access_modes=[str(value) for value in item.access_modes],
        volume_name=item.volume_name,
        backing_storage_resource_id=(
            item.backing_storage.resource_id if item.backing_storage else None
        ),
        notes=item.notes,
    )


@operational_nested_router.get(
    "/infrastructure/operations/container-stacks/{resource_id}/services",
    response={
        200: list[ContainerServiceOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_container_services(
    request: HttpRequest,
    resource_id: int,
) -> list[ContainerServiceOut] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.view_infrastructureresource",
        "infrastructure.view_containerservice",
    )
    if problem:
        return problem
    stack = _stack(request, resource_id)
    if stack is None:
        return _problem(404, "Container stack not found.", "not_found")
    return [_container_service_out(item) for item in stack.services.order_by("name", "id")]


@operational_nested_router.post(
    "/infrastructure/operations/container-stacks/{resource_id}/services",
    response={
        201: ContainerServiceOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_container_service(
    request: HttpRequest,
    resource_id: int,
    payload: ContainerServiceIn,
) -> tuple[int, ContainerServiceOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.add_containerservice",
    )
    if problem:
        return problem
    stack = _stack(request, resource_id)
    if stack is None:
        return _problem(404, "Container stack not found.", "not_found")
    service = ContainerService(
        stack=stack,
        name=payload.name.strip(),
        image=payload.image.strip(),
        replicas=payload.replicas,
        ports=payload.ports,
        volumes=payload.volumes,
        healthcheck=payload.healthcheck.strip(),
        restart_policy=payload.restart_policy.strip(),
        environment_notes=payload.environment_notes.strip(),
    )
    try:
        service.full_clean()
        service.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _container_service_out(service)


@operational_nested_router.put(
    "/infrastructure/operations/container-stacks/{resource_id}/services/{service_id}",
    response={
        200: ContainerServiceOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_container_service(
    request: HttpRequest,
    resource_id: int,
    service_id: int,
    payload: ContainerServiceIn,
) -> ContainerServiceOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.change_containerservice",
    )
    if problem:
        return problem
    stack = _stack(request, resource_id)
    if stack is None:
        return _problem(404, "Container stack not found.", "not_found")
    service = stack.services.filter(id=service_id).first()
    if service is None:
        return _problem(404, "Container service not found.", "not_found")
    service.name = payload.name.strip()
    service.image = payload.image.strip()
    service.replicas = payload.replicas
    service.ports = payload.ports
    service.volumes = payload.volumes
    service.healthcheck = payload.healthcheck.strip()
    service.restart_policy = payload.restart_policy.strip()
    service.environment_notes = payload.environment_notes.strip()
    try:
        service.full_clean()
        service.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _container_service_out(service)


@operational_nested_router.delete(
    "/infrastructure/operations/container-stacks/{resource_id}/services/{service_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def delete_container_service(
    request: HttpRequest,
    resource_id: int,
    service_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_infrastructureresource",
        "infrastructure.delete_containerservice",
    )
    if problem:
        return problem
    stack = _stack(request, resource_id)
    if stack is None:
        return _problem(404, "Container stack not found.", "not_found")
    service = stack.services.filter(id=service_id).first()
    if service is None:
        return _problem(404, "Container service not found.", "not_found")
    service.delete()
    return 204, None


@operational_nested_router.get(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/children",
    response={
        200: KubernetesNamespaceChildrenOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def kubernetes_namespace_children(
    request: HttpRequest,
    resource_id: int,
) -> KubernetesNamespaceChildrenOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.view_infrastructureresource")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    services = (
        namespace.services.select_related("workload__resource")
        if request.user.has_perm("infrastructure.view_kubernetesservice")
        else []
    )
    ingresses = (
        namespace.ingresses.select_related("target_service")
        if request.user.has_perm("infrastructure.view_kubernetesingress")
        else []
    )
    releases = (
        namespace.helm_releases.all()
        if request.user.has_perm("infrastructure.view_helmrelease")
        else []
    )
    storage = (
        namespace.persistent_storage.select_related("backing_storage__resource")
        if request.user.has_perm("infrastructure.view_kubernetespersistentstorage")
        else []
    )
    return KubernetesNamespaceChildrenOut(
        services=[_kubernetes_service_out(item) for item in services],
        ingresses=[_ingress_out(item) for item in ingresses],
        helm_releases=[_helm_out(item) for item in releases],
        persistent_storage=[_persistent_storage_out(item) for item in storage],
    )


def _visible_workload(
    request: HttpRequest,
    namespace: KubernetesNamespaceProfile,
    resource_id: int | None,
) -> KubernetesWorkloadProfile | None:
    if resource_id is None:
        return None
    return (
        KubernetesWorkloadProfile.objects.select_related("resource", "namespace")
        .filter(
            resource__in=_visible_resources(request),
            resource_id=resource_id,
            namespace=namespace,
        )
        .first()
    )


@operational_nested_router.post(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/services",
    response={
        201: KubernetesServiceOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_service(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesServiceIn,
) -> tuple[int, KubernetesServiceOut | dict[str, object]]:
    problem = _permission_problem(request, "infrastructure.add_kubernetesservice")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    workload = _visible_workload(request, namespace, payload.workload_resource_id)
    if payload.workload_resource_id is not None and workload is None:
        return _problem(
            404,
            "Kubernetes workload not found in this namespace.",
            "not_found",
        )
    service = KubernetesService(
        namespace=namespace,
        workload=workload,
        name=payload.name.strip(),
        service_type=payload.service_type,
        cluster_ip=payload.cluster_ip,
        external_hostname=payload.external_hostname.strip(),
        ports=payload.ports,
    )
    try:
        service.full_clean()
        service.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _kubernetes_service_out(service)


@operational_nested_router.put(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/services/{item_id}",
    response={
        200: KubernetesServiceOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_service(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
    payload: KubernetesServiceIn,
) -> KubernetesServiceOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.change_kubernetesservice")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    service = namespace.services.filter(id=item_id).first()
    if service is None:
        return _problem(404, "Kubernetes service not found.", "not_found")
    workload = _visible_workload(request, namespace, payload.workload_resource_id)
    if payload.workload_resource_id is not None and workload is None:
        return _problem(
            404,
            "Kubernetes workload not found in this namespace.",
            "not_found",
        )
    service.workload = workload
    service.name = payload.name.strip()
    service.service_type = payload.service_type
    service.cluster_ip = payload.cluster_ip
    service.external_hostname = payload.external_hostname.strip()
    service.ports = payload.ports
    try:
        service.full_clean()
        service.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _kubernetes_service_out(service)


@operational_nested_router.delete(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/services/{item_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def delete_kubernetes_service(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "infrastructure.delete_kubernetesservice")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    item = namespace.services.filter(id=item_id).first()
    if item is None:
        return _problem(404, "Kubernetes service not found.", "not_found")
    item.delete()
    return 204, None


@operational_nested_router.post(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/ingresses",
    response={
        201: KubernetesIngressOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_ingress(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesIngressIn,
) -> tuple[int, KubernetesIngressOut | dict[str, object]]:
    problem = _permission_problem(request, "infrastructure.add_kubernetesingress")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    target = (
        namespace.services.filter(id=payload.target_service_id).first()
        if payload.target_service_id
        else None
    )
    if payload.target_service_id is not None and target is None:
        return _problem(404, "Ingress target service not found.", "not_found")
    ingress = KubernetesIngress(
        namespace=namespace,
        name=payload.name.strip(),
        ingress_class=payload.ingress_class.strip(),
        hosts=payload.hosts,
        tls_enabled=payload.tls_enabled,
        target_service=target,
        notes=payload.notes.strip(),
    )
    try:
        ingress.full_clean()
        ingress.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _ingress_out(ingress)


@operational_nested_router.put(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/ingresses/{item_id}",
    response={
        200: KubernetesIngressOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_ingress(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
    payload: KubernetesIngressIn,
) -> KubernetesIngressOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.change_kubernetesingress")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    ingress = namespace.ingresses.filter(id=item_id).first()
    if ingress is None:
        return _problem(404, "Kubernetes ingress not found.", "not_found")
    target = (
        namespace.services.filter(id=payload.target_service_id).first()
        if payload.target_service_id
        else None
    )
    if payload.target_service_id is not None and target is None:
        return _problem(404, "Ingress target service not found.", "not_found")
    ingress.name = payload.name.strip()
    ingress.ingress_class = payload.ingress_class.strip()
    ingress.hosts = payload.hosts
    ingress.tls_enabled = payload.tls_enabled
    ingress.target_service = target
    ingress.notes = payload.notes.strip()
    try:
        ingress.full_clean()
        ingress.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _ingress_out(ingress)


@operational_nested_router.delete(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/ingresses/{item_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def delete_kubernetes_ingress(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "infrastructure.delete_kubernetesingress")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    item = namespace.ingresses.filter(id=item_id).first()
    if item is None:
        return _problem(404, "Kubernetes ingress not found.", "not_found")
    item.delete()
    return 204, None


@operational_nested_router.post(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/helm-releases",
    response={
        201: HelmReleaseOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_helm_release(
    request: HttpRequest,
    resource_id: int,
    payload: HelmReleaseIn,
) -> tuple[int, HelmReleaseOut | dict[str, object]]:
    problem = _permission_problem(request, "infrastructure.add_helmrelease")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    release = HelmRelease(
        namespace=namespace,
        name=payload.name.strip(),
        chart=payload.chart.strip(),
        chart_version=payload.chart_version.strip(),
        app_version=payload.app_version.strip(),
        repository_url=payload.repository_url.strip(),
        status=payload.status.strip(),
        values_summary=payload.values_summary.strip(),
    )
    try:
        release.full_clean()
        release.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _helm_out(release)


@operational_nested_router.put(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/helm-releases/{item_id}",
    response={
        200: HelmReleaseOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_helm_release(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
    payload: HelmReleaseIn,
) -> HelmReleaseOut | StaffProblem:
    problem = _permission_problem(request, "infrastructure.change_helmrelease")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    release = namespace.helm_releases.filter(id=item_id).first()
    if release is None:
        return _problem(404, "Helm release not found.", "not_found")
    release.name = payload.name.strip()
    release.chart = payload.chart.strip()
    release.chart_version = payload.chart_version.strip()
    release.app_version = payload.app_version.strip()
    release.repository_url = payload.repository_url.strip()
    release.status = payload.status.strip()
    release.values_summary = payload.values_summary.strip()
    try:
        release.full_clean()
        release.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _helm_out(release)


@operational_nested_router.delete(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/helm-releases/{item_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def delete_helm_release(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(request, "infrastructure.delete_helmrelease")
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    item = namespace.helm_releases.filter(id=item_id).first()
    if item is None:
        return _problem(404, "Helm release not found.", "not_found")
    item.delete()
    return 204, None


@operational_nested_router.post(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/persistent-storage",
    response={
        201: KubernetesPersistentStorageOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_kubernetes_persistent_storage(
    request: HttpRequest,
    resource_id: int,
    payload: KubernetesPersistentStorageIn,
) -> tuple[int, KubernetesPersistentStorageOut | dict[str, object]]:
    problem = _permission_problem(
        request,
        "infrastructure.add_kubernetespersistentstorage",
    )
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    backing = (
        StorageProfile.objects.select_related("resource")
        .filter(
            resource__in=_visible_resources(request),
            resource_id=payload.backing_storage_resource_id,
        )
        .first()
        if payload.backing_storage_resource_id is not None
        else None
    )
    if payload.backing_storage_resource_id is not None and backing is None:
        return _problem(404, "Backing storage not found.", "not_found")
    item = KubernetesPersistentStorage(
        namespace=namespace,
        name=payload.name.strip(),
        storage_class=payload.storage_class.strip(),
        capacity_gb=payload.capacity_gb,
        access_modes=payload.access_modes,
        volume_name=payload.volume_name.strip(),
        backing_storage=backing,
        notes=payload.notes.strip(),
    )
    try:
        item.full_clean()
        item.save()
    except ValidationError as error:
        return _validation_problem(error)
    return 201, _persistent_storage_out(item)


@operational_nested_router.put(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/persistent-storage/{item_id}",
    response={
        200: KubernetesPersistentStorageOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_kubernetes_persistent_storage(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
    payload: KubernetesPersistentStorageIn,
) -> KubernetesPersistentStorageOut | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.change_kubernetespersistentstorage",
    )
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    item = namespace.persistent_storage.filter(id=item_id).first()
    if item is None:
        return _problem(
            404,
            "Kubernetes persistent storage not found.",
            "not_found",
        )
    backing = (
        StorageProfile.objects.select_related("resource")
        .filter(
            resource__in=_visible_resources(request),
            resource_id=payload.backing_storage_resource_id,
        )
        .first()
        if payload.backing_storage_resource_id is not None
        else None
    )
    if payload.backing_storage_resource_id is not None and backing is None:
        return _problem(404, "Backing storage not found.", "not_found")
    item.name = payload.name.strip()
    item.storage_class = payload.storage_class.strip()
    item.capacity_gb = payload.capacity_gb
    item.access_modes = payload.access_modes
    item.volume_name = payload.volume_name.strip()
    item.backing_storage = backing
    item.notes = payload.notes.strip()
    try:
        item.full_clean()
        item.save()
    except ValidationError as error:
        return _validation_problem(error)
    return _persistent_storage_out(item)


@operational_nested_router.delete(
    "/infrastructure/operations/kubernetes/namespaces/{resource_id}/persistent-storage/{item_id}",
    response={
        204: None,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def delete_kubernetes_persistent_storage(
    request: HttpRequest,
    resource_id: int,
    item_id: int,
) -> tuple[int, None] | StaffProblem:
    problem = _permission_problem(
        request,
        "infrastructure.delete_kubernetespersistentstorage",
    )
    if problem:
        return problem
    namespace = _namespace(request, resource_id)
    if namespace is None:
        return _problem(404, "Kubernetes namespace not found.", "not_found")
    item = namespace.persistent_storage.filter(id=item_id).first()
    if item is None:
        return _problem(
            404,
            "Kubernetes persistent storage not found.",
            "not_found",
        )
    item.delete()
    return 204, None

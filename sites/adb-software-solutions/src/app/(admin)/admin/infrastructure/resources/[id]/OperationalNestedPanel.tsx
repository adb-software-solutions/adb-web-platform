"use client";

import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { useCallback, useEffect, useMemo, useState } from "react";

interface ResourceMeta {
    id: number;
    resource_type: string;
    ownership_type: string;
    client_id: number | null;
}

interface ContainerService {
    id: number;
    name: string;
    image: string;
    replicas: number | null;
    ports: string[];
    volumes: string[];
    healthcheck: string;
    restart_policy: string;
    environment_notes: string;
}

interface KubernetesService {
    id: number;
    name: string;
    service_type: string;
    workload_resource_id: number | null;
    cluster_ip: string | null;
    external_hostname: string;
    ports: string[];
}

interface KubernetesIngress {
    id: number;
    name: string;
    ingress_class: string;
    hosts: string[];
    tls_enabled: boolean;
    target_service_id: number | null;
    notes: string;
}

interface HelmRelease {
    id: number;
    name: string;
    chart: string;
    chart_version: string;
    app_version: string;
    repository_url: string;
    status: string;
    values_summary: string;
}

interface KubernetesPersistentStorage {
    id: number;
    name: string;
    storage_class: string;
    capacity_gb: number | null;
    access_modes: string[];
    volume_name: string;
    backing_storage_resource_id: number | null;
    notes: string;
}

interface KubernetesChildren {
    services: KubernetesService[];
    ingresses: KubernetesIngress[];
    helm_releases: HelmRelease[];
    persistent_storage: KubernetesPersistentStorage[];
}

interface OperationalOption {
    resource_id: number;
    name: string;
    resource_type: string;
    ownership_type: string;
    client_id: number | null;
}

interface OperationalOptions {
    storages: OperationalOption[];
    workloads: OperationalOption[];
}

interface SpecialistEditDetails {
    values: Record<string, string | number | boolean | string[] | number[] | null>;
}

type KubernetesKind = "service" | "ingress" | "helm" | "storage";

const OPERATIONS_BASE = `${API_URL}/api/admin/infrastructure/operations`;

function lines(value: string): string[] {
    return value
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
}

function numberOrNull(value: string): number | null {
    return value.trim() ? Number(value) : null;
}

function exactScope(option: OperationalOption, resource: ResourceMeta): boolean {
    return (
        option.ownership_type === resource.ownership_type &&
        option.client_id === resource.client_id
    );
}

function EmptyNested({ children }: { children: string }) {
    return (
        <div className="rounded-xl border border-dashed border-slate-800 p-4 text-sm text-slate-500">
            {children}
        </div>
    );
}

function ContainerServicesCard({ resourceId }: { resourceId: number }) {
    const { hasPermission } = useAuth();
    const canView =
        hasPermission("infrastructure.view_infrastructureresource") &&
        hasPermission("infrastructure.view_containerservice");
    const canAdd =
        hasPermission("infrastructure.change_infrastructureresource") &&
        hasPermission("infrastructure.add_containerservice");
    const canChange =
        hasPermission("infrastructure.change_infrastructureresource") &&
        hasPermission("infrastructure.change_containerservice");
    const canDelete =
        hasPermission("infrastructure.change_infrastructureresource") &&
        hasPermission("infrastructure.delete_containerservice");

    const [services, setServices] = useState<ContainerService[]>([]);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [name, setName] = useState("");
    const [image, setImage] = useState("");
    const [replicas, setReplicas] = useState("");
    const [ports, setPorts] = useState("");
    const [volumes, setVolumes] = useState("");
    const [healthcheck, setHealthcheck] = useState("");
    const [restartPolicy, setRestartPolicy] = useState("");
    const [environmentNotes, setEnvironmentNotes] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [deletingId, setDeletingId] = useState<number | null>(null);

    const base = `${OPERATIONS_BASE}/container-stacks/${resourceId}/services`;

    const load = useCallback(async () => {
        if (!canView) return;
        try {
            setError(null);
            setServices((await fetchAPI(base)) as ContainerService[]);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load container services.",
            );
        }
    }, [base, canView]);

    useEffect(() => {
        void load();
    }, [load]);

    function resetForm() {
        setShowForm(false);
        setEditingId(null);
        setName("");
        setImage("");
        setReplicas("");
        setPorts("");
        setVolumes("");
        setHealthcheck("");
        setRestartPolicy("");
        setEnvironmentNotes("");
        setError(null);
    }

    function edit(service: ContainerService) {
        setEditingId(service.id);
        setName(service.name);
        setImage(service.image);
        setReplicas(service.replicas === null ? "" : String(service.replicas));
        setPorts(service.ports.join("\n"));
        setVolumes(service.volumes.join("\n"));
        setHealthcheck(service.healthcheck);
        setRestartPolicy(service.restart_policy);
        setEnvironmentNotes(service.environment_notes);
        setShowForm(true);
        setError(null);
    }

    async function save() {
        if (!name.trim()) {
            setError("Enter a service name.");
            return;
        }
        try {
            setIsSaving(true);
            setError(null);
            await fetchAPI(editingId === null ? base : `${base}/${editingId}`, {
                method: editingId === null ? "POST" : "PUT",
                body: JSON.stringify({
                    name: name.trim(),
                    image: image.trim(),
                    replicas: numberOrNull(replicas),
                    ports: lines(ports),
                    volumes: lines(volumes),
                    healthcheck: healthcheck.trim(),
                    restart_policy: restartPolicy.trim(),
                    environment_notes: environmentNotes.trim(),
                }),
            });
            resetForm();
            await load();
        } catch (saveError) {
            setError(
                saveError instanceof Error
                    ? saveError.message
                    : "Unable to save the container service.",
            );
        } finally {
            setIsSaving(false);
        }
    }

    async function remove(service: ContainerService) {
        if (!window.confirm(`Delete container service ${service.name}?`)) return;
        try {
            setDeletingId(service.id);
            setError(null);
            await fetchAPI(`${base}/${service.id}`, { method: "DELETE" });
            await load();
        } catch (deleteError) {
            setError(
                deleteError instanceof Error
                    ? deleteError.message
                    : "Unable to delete the container service.",
            );
        } finally {
            setDeletingId(null);
        }
    }

    if (!canView) return null;

    return (
        <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-sm font-semibold text-white">
                        Container services
                    </h2>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                        Runtime service, image, port and volume metadata for this
                        stack. Record configuration shape only; secrets stay in
                        Credential Vault.
                    </p>
                </div>
                {canAdd ? (
                    <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                            resetForm();
                            setShowForm(true);
                        }}
                    >
                        Add service
                    </Button>
                ) : null}
            </div>

            {error ? (
                <p className="mt-4 text-sm text-red-300">{error}</p>
            ) : null}

            {showForm ? (
                <div className="mt-5 space-y-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                    <div className="grid gap-3 md:grid-cols-2">
                        <Input
                            aria-label="Service name"
                            placeholder="Service name"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
                        <Input
                            aria-label="Container image"
                            placeholder="Image, e.g. nginx:1.29"
                            value={image}
                            onChange={(event) => setImage(event.target.value)}
                        />
                        <Input
                            aria-label="Replicas"
                            type="number"
                            min="0"
                            placeholder="Replicas"
                            value={replicas}
                            onChange={(event) => setReplicas(event.target.value)}
                        />
                        <Input
                            aria-label="Restart policy"
                            placeholder="Restart policy"
                            value={restartPolicy}
                            onChange={(event) =>
                                setRestartPolicy(event.target.value)
                            }
                        />
                        <Input
                            aria-label="Healthcheck"
                            placeholder="Healthcheck summary"
                            value={healthcheck}
                            onChange={(event) =>
                                setHealthcheck(event.target.value)
                            }
                        />
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <Textarea
                            aria-label="Ports"
                            rows={4}
                            placeholder="Ports, one per line"
                            value={ports}
                            onChange={(event) => setPorts(event.target.value)}
                        />
                        <Textarea
                            aria-label="Volumes"
                            rows={4}
                            placeholder="Volumes, one per line"
                            value={volumes}
                            onChange={(event) => setVolumes(event.target.value)}
                        />
                    </div>
                    <Textarea
                        aria-label="Environment notes"
                        rows={3}
                        placeholder="Non-secret environment/configuration notes"
                        value={environmentNotes}
                        onChange={(event) =>
                            setEnvironmentNotes(event.target.value)
                        }
                    />
                    <div className="flex justify-end gap-2">
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={resetForm}
                            disabled={isSaving}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={() => void save()}
                            disabled={isSaving}
                        >
                            {isSaving
                                ? "Saving…"
                                : editingId === null
                                  ? "Add service"
                                  : "Save service"}
                        </Button>
                    </div>
                </div>
            ) : null}

            <div className="mt-5 space-y-3">
                {services.length === 0 ? (
                    <EmptyNested>No container services recorded yet.</EmptyNested>
                ) : (
                    services.map((service) => (
                        <div
                            key={service.id}
                            className="rounded-xl border border-slate-800 bg-slate-950/30 p-4"
                        >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                    <p className="font-medium text-slate-100">
                                        {service.name}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-500">
                                        {service.image || "Image not recorded"}
                                        {service.replicas !== null
                                            ? ` · ${service.replicas} replicas`
                                            : ""}
                                    </p>
                                </div>
                                <div className="flex gap-2">
                                    {canChange ? (
                                        <Button
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => edit(service)}
                                        >
                                            Edit
                                        </Button>
                                    ) : null}
                                    {canDelete ? (
                                        <Button
                                            type="button"
                                            size="sm"
                                            variant="ghost"
                                            disabled={deletingId === service.id}
                                            onClick={() => void remove(service)}
                                        >
                                            {deletingId === service.id
                                                ? "Deleting…"
                                                : "Delete"}
                                        </Button>
                                    ) : null}
                                </div>
                            </div>
                            {service.ports.length || service.volumes.length ? (
                                <div className="mt-3 grid gap-3 text-xs text-slate-400 md:grid-cols-2">
                                    <div>
                                        <span className="font-semibold text-slate-500">
                                            Ports
                                        </span>
                                        <p className="mt-1 whitespace-pre-wrap">
                                            {service.ports.join("\n") || "—"}
                                        </p>
                                    </div>
                                    <div>
                                        <span className="font-semibold text-slate-500">
                                            Volumes
                                        </span>
                                        <p className="mt-1 whitespace-pre-wrap">
                                            {service.volumes.join("\n") || "—"}
                                        </p>
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    ))
                )}
            </div>
        </Card>
    );
}

function KubernetesNamespaceCard({
    resource,
}: {
    resource: ResourceMeta;
}) {
    const { hasPermission } = useAuth();
    const [children, setChildren] = useState<KubernetesChildren | null>(null);
    const [options, setOptions] = useState<OperationalOptions | null>(null);
    const [namespaceWorkloads, setNamespaceWorkloads] = useState<
        OperationalOption[]
    >([]);
    const [kind, setKind] = useState<KubernetesKind | null>(null);
    const [editingId, setEditingId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [deletingKey, setDeletingKey] = useState<string | null>(null);

    const [name, setName] = useState("");
    const [serviceType, setServiceType] = useState("cluster_ip");
    const [workloadId, setWorkloadId] = useState("");
    const [clusterIp, setClusterIp] = useState("");
    const [externalHostname, setExternalHostname] = useState("");
    const [ports, setPorts] = useState("");
    const [ingressClass, setIngressClass] = useState("");
    const [hosts, setHosts] = useState("");
    const [tlsEnabled, setTlsEnabled] = useState(false);
    const [targetServiceId, setTargetServiceId] = useState("");
    const [chart, setChart] = useState("");
    const [chartVersion, setChartVersion] = useState("");
    const [appVersion, setAppVersion] = useState("");
    const [repositoryUrl, setRepositoryUrl] = useState("");
    const [status, setStatus] = useState("");
    const [valuesSummary, setValuesSummary] = useState("");
    const [storageClass, setStorageClass] = useState("");
    const [capacityGb, setCapacityGb] = useState("");
    const [accessModes, setAccessModes] = useState("");
    const [volumeName, setVolumeName] = useState("");
    const [backingStorageId, setBackingStorageId] = useState("");
    const [notes, setNotes] = useState("");

    const childrenBase = `${OPERATIONS_BASE}/kubernetes/namespaces/${resource.id}`;

    const load = useCallback(async () => {
        try {
            setError(null);
            const [nextChildren, nextOptions] = await Promise.all([
                fetchAPI(`${childrenBase}/children`) as Promise<KubernetesChildren>,
                fetchAPI(`${OPERATIONS_BASE}/options`) as Promise<OperationalOptions>,
            ]);
            setChildren(nextChildren);
            setOptions(nextOptions);

            const candidates = nextOptions.workloads.filter((option) =>
                exactScope(option, resource),
            );
            const resolved = await Promise.all(
                candidates.map(async (option) => {
                    try {
                        const details = (await fetchAPI(
                            `${API_URL}/api/admin/infrastructure/resources/${option.resource_id}/specialist-edit`,
                        )) as SpecialistEditDetails;
                        return details.values.namespace_resource_id === resource.id
                            ? option
                            : null;
                    } catch {
                        return null;
                    }
                }),
            );
            setNamespaceWorkloads(
                resolved.filter(
                    (option): option is OperationalOption => option !== null,
                ),
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load Kubernetes namespace operations.",
            );
        }
    }, [childrenBase, resource]);

    useEffect(() => {
        void load();
    }, [load]);

    const storages = useMemo(
        () => options?.storages.filter((option) => exactScope(option, resource)) ?? [],
        [options, resource],
    );

    function resetForm() {
        setKind(null);
        setEditingId(null);
        setName("");
        setServiceType("cluster_ip");
        setWorkloadId("");
        setClusterIp("");
        setExternalHostname("");
        setPorts("");
        setIngressClass("");
        setHosts("");
        setTlsEnabled(false);
        setTargetServiceId("");
        setChart("");
        setChartVersion("");
        setAppVersion("");
        setRepositoryUrl("");
        setStatus("");
        setValuesSummary("");
        setStorageClass("");
        setCapacityGb("");
        setAccessModes("");
        setVolumeName("");
        setBackingStorageId("");
        setNotes("");
        setError(null);
    }

    function create(nextKind: KubernetesKind) {
        resetForm();
        setKind(nextKind);
    }

    function editService(item: KubernetesService) {
        resetForm();
        setKind("service");
        setEditingId(item.id);
        setName(item.name);
        setServiceType(item.service_type);
        setWorkloadId(
            item.workload_resource_id === null
                ? ""
                : String(item.workload_resource_id),
        );
        setClusterIp(item.cluster_ip ?? "");
        setExternalHostname(item.external_hostname);
        setPorts(item.ports.join("\n"));
    }

    function editIngress(item: KubernetesIngress) {
        resetForm();
        setKind("ingress");
        setEditingId(item.id);
        setName(item.name);
        setIngressClass(item.ingress_class);
        setHosts(item.hosts.join("\n"));
        setTlsEnabled(item.tls_enabled);
        setTargetServiceId(
            item.target_service_id === null
                ? ""
                : String(item.target_service_id),
        );
        setNotes(item.notes);
    }

    function editHelm(item: HelmRelease) {
        resetForm();
        setKind("helm");
        setEditingId(item.id);
        setName(item.name);
        setChart(item.chart);
        setChartVersion(item.chart_version);
        setAppVersion(item.app_version);
        setRepositoryUrl(item.repository_url);
        setStatus(item.status);
        setValuesSummary(item.values_summary);
    }

    function editStorage(item: KubernetesPersistentStorage) {
        resetForm();
        setKind("storage");
        setEditingId(item.id);
        setName(item.name);
        setStorageClass(item.storage_class);
        setCapacityGb(item.capacity_gb === null ? "" : String(item.capacity_gb));
        setAccessModes(item.access_modes.join("\n"));
        setVolumeName(item.volume_name);
        setBackingStorageId(
            item.backing_storage_resource_id === null
                ? ""
                : String(item.backing_storage_resource_id),
        );
        setNotes(item.notes);
    }

    function endpoint(nextKind: KubernetesKind, id: number | null): string {
        const paths: Record<KubernetesKind, string> = {
            service: "services",
            ingress: "ingresses",
            helm: "helm-releases",
            storage: "persistent-storage",
        };
        const base = `${childrenBase}/${paths[nextKind]}`;
        return id === null ? base : `${base}/${id}`;
    }

    async function save() {
        if (!kind || !name.trim()) {
            setError("Enter a name for this Kubernetes record.");
            return;
        }
        if (kind === "helm" && !chart.trim()) {
            setError("Enter a Helm chart name.");
            return;
        }

        let payload: Record<string, unknown>;
        if (kind === "service") {
            payload = {
                name: name.trim(),
                service_type: serviceType,
                workload_resource_id: numberOrNull(workloadId),
                cluster_ip: clusterIp.trim() || null,
                external_hostname: externalHostname.trim(),
                ports: lines(ports),
            };
        } else if (kind === "ingress") {
            payload = {
                name: name.trim(),
                ingress_class: ingressClass.trim(),
                hosts: lines(hosts),
                tls_enabled: tlsEnabled,
                target_service_id: numberOrNull(targetServiceId),
                notes: notes.trim(),
            };
        } else if (kind === "helm") {
            payload = {
                name: name.trim(),
                chart: chart.trim(),
                chart_version: chartVersion.trim(),
                app_version: appVersion.trim(),
                repository_url: repositoryUrl.trim(),
                status: status.trim(),
                values_summary: valuesSummary.trim(),
            };
        } else {
            payload = {
                name: name.trim(),
                storage_class: storageClass.trim(),
                capacity_gb: numberOrNull(capacityGb),
                access_modes: lines(accessModes),
                volume_name: volumeName.trim(),
                backing_storage_resource_id: numberOrNull(backingStorageId),
                notes: notes.trim(),
            };
        }

        try {
            setIsSaving(true);
            setError(null);
            await fetchAPI(endpoint(kind, editingId), {
                method: editingId === null ? "POST" : "PUT",
                body: JSON.stringify(payload),
            });
            resetForm();
            await load();
        } catch (saveError) {
            setError(
                saveError instanceof Error
                    ? saveError.message
                    : "Unable to save this Kubernetes record.",
            );
        } finally {
            setIsSaving(false);
        }
    }

    async function remove(
        nextKind: KubernetesKind,
        id: number,
        itemName: string,
    ) {
        if (!window.confirm(`Delete ${itemName}?`)) return;
        const key = `${nextKind}-${id}`;
        try {
            setDeletingKey(key);
            setError(null);
            await fetchAPI(endpoint(nextKind, id), { method: "DELETE" });
            await load();
        } catch (deleteError) {
            setError(
                deleteError instanceof Error
                    ? deleteError.message
                    : "Unable to delete this Kubernetes record.",
            );
        } finally {
            setDeletingKey(null);
        }
    }

    if (!children) {
        return error ? (
            <Card className="p-5 text-sm text-red-300">{error}</Card>
        ) : null;
    }

    const addPermissions: Record<KubernetesKind, boolean> = {
        service: hasPermission("infrastructure.add_kubernetesservice"),
        ingress: hasPermission("infrastructure.add_kubernetesingress"),
        helm: hasPermission("infrastructure.add_helmrelease"),
        storage: hasPermission("infrastructure.add_kubernetespersistentstorage"),
    };
    const changePermissions: Record<KubernetesKind, boolean> = {
        service: hasPermission("infrastructure.change_kubernetesservice"),
        ingress: hasPermission("infrastructure.change_kubernetesingress"),
        helm: hasPermission("infrastructure.change_helmrelease"),
        storage: hasPermission("infrastructure.change_kubernetespersistentstorage"),
    };
    const deletePermissions: Record<KubernetesKind, boolean> = {
        service: hasPermission("infrastructure.delete_kubernetesservice"),
        ingress: hasPermission("infrastructure.delete_kubernetesingress"),
        helm: hasPermission("infrastructure.delete_helmrelease"),
        storage: hasPermission("infrastructure.delete_kubernetespersistentstorage"),
    };

    return (
        <Card className="p-5">
            <div>
                <h2 className="text-sm font-semibold text-white">
                    Kubernetes namespace runtime
                </h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                    Services, ingresses, Helm releases and persistent storage in
                    this namespace. Helm values are descriptive only; never put
                    credentials or secret values here.
                </p>
            </div>

            {error ? (
                <p className="mt-4 text-sm text-red-300">{error}</p>
            ) : null}

            {kind ? (
                <div className="mt-5 space-y-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                    <div className="grid gap-3 md:grid-cols-2">
                        <Input
                            aria-label="Record name"
                            placeholder="Name"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
                        {kind === "service" ? (
                            <Select
                                aria-label="Service type"
                                value={serviceType}
                                onChange={(event) =>
                                    setServiceType(event.target.value)
                                }
                            >
                                <option value="cluster_ip">ClusterIP</option>
                                <option value="node_port">NodePort</option>
                                <option value="load_balancer">LoadBalancer</option>
                                <option value="external_name">ExternalName</option>
                                <option value="headless">Headless</option>
                                <option value="other">Other</option>
                            </Select>
                        ) : null}
                        {kind === "service" ? (
                            <Select
                                aria-label="Workload"
                                value={workloadId}
                                onChange={(event) =>
                                    setWorkloadId(event.target.value)
                                }
                            >
                                <option value="">No workload link</option>
                                {namespaceWorkloads.map((option) => (
                                    <option
                                        key={option.resource_id}
                                        value={option.resource_id}
                                    >
                                        {option.name}
                                    </option>
                                ))}
                            </Select>
                        ) : null}
                        {kind === "service" ? (
                            <Input
                                aria-label="Cluster IP"
                                placeholder="Cluster IP"
                                value={clusterIp}
                                onChange={(event) =>
                                    setClusterIp(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "service" ? (
                            <Input
                                aria-label="External hostname"
                                placeholder="External hostname"
                                value={externalHostname}
                                onChange={(event) =>
                                    setExternalHostname(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "ingress" ? (
                            <Input
                                aria-label="Ingress class"
                                placeholder="Ingress class"
                                value={ingressClass}
                                onChange={(event) =>
                                    setIngressClass(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "ingress" ? (
                            <Select
                                aria-label="Target service"
                                value={targetServiceId}
                                onChange={(event) =>
                                    setTargetServiceId(event.target.value)
                                }
                            >
                                <option value="">No target service</option>
                                {children.services.map((service) => (
                                    <option key={service.id} value={service.id}>
                                        {service.name}
                                    </option>
                                ))}
                            </Select>
                        ) : null}
                        {kind === "helm" ? (
                            <Input
                                aria-label="Chart"
                                placeholder="Chart"
                                value={chart}
                                onChange={(event) => setChart(event.target.value)}
                            />
                        ) : null}
                        {kind === "helm" ? (
                            <Input
                                aria-label="Chart version"
                                placeholder="Chart version"
                                value={chartVersion}
                                onChange={(event) =>
                                    setChartVersion(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "helm" ? (
                            <Input
                                aria-label="App version"
                                placeholder="App version"
                                value={appVersion}
                                onChange={(event) =>
                                    setAppVersion(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "helm" ? (
                            <Input
                                aria-label="Repository URL"
                                placeholder="Repository URL"
                                value={repositoryUrl}
                                onChange={(event) =>
                                    setRepositoryUrl(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "helm" ? (
                            <Input
                                aria-label="Helm status"
                                placeholder="Status"
                                value={status}
                                onChange={(event) => setStatus(event.target.value)}
                            />
                        ) : null}
                        {kind === "storage" ? (
                            <Input
                                aria-label="Storage class"
                                placeholder="Storage class"
                                value={storageClass}
                                onChange={(event) =>
                                    setStorageClass(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "storage" ? (
                            <Input
                                aria-label="Capacity GB"
                                type="number"
                                min="0"
                                placeholder="Capacity GB"
                                value={capacityGb}
                                onChange={(event) =>
                                    setCapacityGb(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "storage" ? (
                            <Input
                                aria-label="Volume name"
                                placeholder="Volume name"
                                value={volumeName}
                                onChange={(event) =>
                                    setVolumeName(event.target.value)
                                }
                            />
                        ) : null}
                        {kind === "storage" ? (
                            <Select
                                aria-label="Backing storage"
                                value={backingStorageId}
                                onChange={(event) =>
                                    setBackingStorageId(event.target.value)
                                }
                            >
                                <option value="">No backing storage link</option>
                                {storages.map((option) => (
                                    <option
                                        key={option.resource_id}
                                        value={option.resource_id}
                                    >
                                        {option.name}
                                    </option>
                                ))}
                            </Select>
                        ) : null}
                    </div>

                    {kind === "service" ? (
                        <Textarea
                            aria-label="Service ports"
                            rows={3}
                            placeholder="Ports, one per line"
                            value={ports}
                            onChange={(event) => setPorts(event.target.value)}
                        />
                    ) : null}
                    {kind === "ingress" ? (
                        <>
                            <Textarea
                                aria-label="Ingress hosts"
                                rows={3}
                                placeholder="Hosts, one per line"
                                value={hosts}
                                onChange={(event) => setHosts(event.target.value)}
                            />
                            <label className="flex items-center gap-2 text-sm text-slate-300">
                                <input
                                    type="checkbox"
                                    checked={tlsEnabled}
                                    onChange={(event) =>
                                        setTlsEnabled(event.target.checked)
                                    }
                                />
                                TLS enabled
                            </label>
                            <Textarea
                                aria-label="Ingress notes"
                                rows={3}
                                placeholder="Ingress notes"
                                value={notes}
                                onChange={(event) => setNotes(event.target.value)}
                            />
                        </>
                    ) : null}
                    {kind === "helm" ? (
                        <Textarea
                            aria-label="Helm values summary"
                            rows={4}
                            placeholder="Non-secret Helm values/configuration summary"
                            value={valuesSummary}
                            onChange={(event) =>
                                setValuesSummary(event.target.value)
                            }
                        />
                    ) : null}
                    {kind === "storage" ? (
                        <>
                            <Textarea
                                aria-label="Access modes"
                                rows={3}
                                placeholder="Access modes, one per line"
                                value={accessModes}
                                onChange={(event) =>
                                    setAccessModes(event.target.value)
                                }
                            />
                            <Textarea
                                aria-label="Storage notes"
                                rows={3}
                                placeholder="Storage notes"
                                value={notes}
                                onChange={(event) => setNotes(event.target.value)}
                            />
                        </>
                    ) : null}

                    <div className="flex justify-end gap-2">
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={resetForm}
                            disabled={isSaving}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="button"
                            onClick={() => void save()}
                            disabled={isSaving}
                        >
                            {isSaving ? "Saving…" : "Save record"}
                        </Button>
                    </div>
                </div>
            ) : null}

            <div className="mt-6 grid gap-5 xl:grid-cols-2">
                <section className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">
                            Services
                        </h3>
                        {addPermissions.service ? (
                            <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => create("service")}
                            >
                                Add
                            </Button>
                        ) : null}
                    </div>
                    {children.services.length === 0 ? (
                        <EmptyNested>No services recorded.</EmptyNested>
                    ) : (
                        children.services.map((service) => (
                            <div
                                key={service.id}
                                className="rounded-xl border border-slate-800 p-3"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-slate-100">
                                            {service.name}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {service.service_type.replaceAll("_", " ")}
                                            {service.cluster_ip
                                                ? ` · ${service.cluster_ip}`
                                                : ""}
                                        </p>
                                    </div>
                                    <div className="flex gap-1">
                                        {changePermissions.service ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => editService(service)}
                                            >
                                                Edit
                                            </Button>
                                        ) : null}
                                        {deletePermissions.service ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                disabled={
                                                    deletingKey ===
                                                    `service-${service.id}`
                                                }
                                                onClick={() =>
                                                    void remove(
                                                        "service",
                                                        service.id,
                                                        service.name,
                                                    )
                                                }
                                            >
                                                Delete
                                            </Button>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </section>

                <section className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">
                            Ingresses
                        </h3>
                        {addPermissions.ingress ? (
                            <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => create("ingress")}
                            >
                                Add
                            </Button>
                        ) : null}
                    </div>
                    {children.ingresses.length === 0 ? (
                        <EmptyNested>No ingresses recorded.</EmptyNested>
                    ) : (
                        children.ingresses.map((ingress) => (
                            <div
                                key={ingress.id}
                                className="rounded-xl border border-slate-800 p-3"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-slate-100">
                                            {ingress.name}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {ingress.hosts.join(", ") || "No hosts"}
                                            {ingress.tls_enabled ? " · TLS" : ""}
                                        </p>
                                    </div>
                                    <div className="flex gap-1">
                                        {changePermissions.ingress ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => editIngress(ingress)}
                                            >
                                                Edit
                                            </Button>
                                        ) : null}
                                        {deletePermissions.ingress ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() =>
                                                    void remove(
                                                        "ingress",
                                                        ingress.id,
                                                        ingress.name,
                                                    )
                                                }
                                            >
                                                Delete
                                            </Button>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </section>

                <section className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">
                            Helm releases
                        </h3>
                        {addPermissions.helm ? (
                            <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => create("helm")}
                            >
                                Add
                            </Button>
                        ) : null}
                    </div>
                    {children.helm_releases.length === 0 ? (
                        <EmptyNested>No Helm releases recorded.</EmptyNested>
                    ) : (
                        children.helm_releases.map((release) => (
                            <div
                                key={release.id}
                                className="rounded-xl border border-slate-800 p-3"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-slate-100">
                                            {release.name}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {release.chart}
                                            {release.chart_version
                                                ? ` · ${release.chart_version}`
                                                : ""}
                                            {release.status
                                                ? ` · ${release.status}`
                                                : ""}
                                        </p>
                                    </div>
                                    <div className="flex gap-1">
                                        {changePermissions.helm ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => editHelm(release)}
                                            >
                                                Edit
                                            </Button>
                                        ) : null}
                                        {deletePermissions.helm ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() =>
                                                    void remove(
                                                        "helm",
                                                        release.id,
                                                        release.name,
                                                    )
                                                }
                                            >
                                                Delete
                                            </Button>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </section>

                <section className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold tracking-wide text-slate-400 uppercase">
                            Persistent storage
                        </h3>
                        {addPermissions.storage ? (
                            <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() => create("storage")}
                            >
                                Add
                            </Button>
                        ) : null}
                    </div>
                    {children.persistent_storage.length === 0 ? (
                        <EmptyNested>No persistent storage recorded.</EmptyNested>
                    ) : (
                        children.persistent_storage.map((item) => (
                            <div
                                key={item.id}
                                className="rounded-xl border border-slate-800 p-3"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <p className="text-sm font-medium text-slate-100">
                                            {item.name}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {item.storage_class ||
                                                "Storage class not recorded"}
                                            {item.capacity_gb !== null
                                                ? ` · ${item.capacity_gb} GB`
                                                : ""}
                                        </p>
                                    </div>
                                    <div className="flex gap-1">
                                        {changePermissions.storage ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => editStorage(item)}
                                            >
                                                Edit
                                            </Button>
                                        ) : null}
                                        {deletePermissions.storage ? (
                                            <Button
                                                type="button"
                                                size="sm"
                                                variant="ghost"
                                                onClick={() =>
                                                    void remove(
                                                        "storage",
                                                        item.id,
                                                        item.name,
                                                    )
                                                }
                                            >
                                                Delete
                                            </Button>
                                        ) : null}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </section>
            </div>
        </Card>
    );
}

export function OperationalNestedPanel({ resourceId }: { resourceId: number }) {
    const { hasPermission } = useAuth();
    const [resource, setResource] = useState<ResourceMeta | null>(null);

    useEffect(() => {
        let cancelled = false;
        if (!hasPermission("infrastructure.view_infrastructureresource")) return;
        void fetchAPI(`${API_URL}/api/admin/infrastructure/resources/${resourceId}`)
            .then((value) => {
                if (!cancelled) setResource(value as ResourceMeta);
            })
            .catch(() => {
                if (!cancelled) setResource(null);
            });
        return () => {
            cancelled = true;
        };
    }, [hasPermission, resourceId]);

    if (!resource) return null;
    if (resource.resource_type === "container_stack") {
        return <ContainerServicesCard resourceId={resourceId} />;
    }
    if (resource.resource_type === "kubernetes_namespace") {
        return <KubernetesNamespaceCard resource={resource} />;
    }
    return null;
}

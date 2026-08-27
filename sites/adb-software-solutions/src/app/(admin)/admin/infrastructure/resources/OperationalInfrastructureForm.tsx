"use client";

import {
    Button,
    Card,
    DataError,
    DataLoading,
    Input,
    PageHeader,
    Select,
    Textarea,
} from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { FormEvent, useEffect, useMemo, useState } from "react";

export type OperationalType =
    | "storage"
    | "backup_plan"
    | "container_stack"
    | "kubernetes_cluster"
    | "kubernetes_namespace"
    | "kubernetes_workload"
    | "system_service"
    | "scheduled_job";

type EditValue = string | number | boolean | null | string[];

interface ClientOption {
    id: number;
    name: string;
}

interface ResourceOption {
    resource_id: number;
    name: string;
    resource_type: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

interface OperationalOptions {
    provider_accounts: ResourceOption[];
    servers: ResourceOption[];
    storages: ResourceOption[];
    clusters: ResourceOption[];
    namespaces: ResourceOption[];
    workloads: ResourceOption[];
    resources: ResourceOption[];
}

interface SpecialistOptions {
    clients: ClientOption[];
}

interface EditDetails {
    resource_id: number;
    resource_type: OperationalType;
    ownership_type: "internal" | "client";
    client_id: number | null;
    client_name: string | null;
    name: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    description: string;
    values: Record<string, EditValue>;
}

interface SaveResult {
    resource_id: number;
}

interface Props {
    allowedTypes: OperationalType[];
    onCancel: () => void;
    onCreated?: (resourceId: number) => void;
    editResourceId?: number;
    onSaved?: () => void;
}

const BASE = `${API_URL}/api/admin/infrastructure/operations`;

function typeLabel(type: OperationalType): string {
    const labels: Record<OperationalType, string> = {
        storage: "Storage",
        backup_plan: "Backup plan",
        container_stack: "Container stack",
        kubernetes_cluster: "Kubernetes cluster",
        kubernetes_namespace: "Kubernetes namespace",
        kubernetes_workload: "Kubernetes workload",
        system_service: "System service",
        scheduled_job: "Scheduled job",
    };
    return labels[type];
}

function endpoint(type: OperationalType): string {
    const paths: Record<OperationalType, string> = {
        storage: "storage",
        backup_plan: "backup-plans",
        container_stack: "container-stacks",
        kubernetes_cluster: "kubernetes/clusters",
        kubernetes_namespace: "kubernetes/namespaces",
        kubernetes_workload: "kubernetes/workloads",
        system_service: "system-services",
        scheduled_job: "scheduled-jobs",
    };
    return paths[type];
}

function stringValue(value: EditValue | undefined): string {
    if (value === null || value === undefined || Array.isArray(value)) return "";
    return String(value);
}

function numberValue(value: EditValue | undefined): string {
    return typeof value === "number" ? String(value) : "";
}

function boolValue(value: EditValue | undefined): string {
    return value === true ? "yes" : value === false ? "no" : "";
}

function numberOrNull(value: string): number | null {
    return value.trim() ? Number(value) : null;
}

function dateTimeOrNull(value: string): string | null {
    return value.trim() ? new Date(value).toISOString() : null;
}

function dateTimeValue(value: EditValue | undefined): string {
    const rendered = stringValue(value);
    return rendered.includes("T") ? rendered.slice(0, 16) : rendered;
}

export function OperationalInfrastructureForm({
    allowedTypes,
    onCancel,
    onCreated,
    editResourceId,
    onSaved,
}: Props) {
    const isEditing = editResourceId !== undefined;
    const [options, setOptions] = useState<OperationalOptions | null>(null);
    const [clients, setClients] = useState<ClientOption[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [type, setType] = useState<OperationalType>(allowedTypes[0] ?? "storage");
    const [ownership, setOwnership] = useState<"internal" | "client">("internal");
    const [clientId, setClientId] = useState("");
    const [clientName, setClientName] = useState<string | null>(null);
    const [name, setName] = useState("");
    const [lifecycle, setLifecycle] = useState("active");
    const [environment, setEnvironment] = useState("production");
    const [criticality, setCriticality] = useState("normal");
    const [description, setDescription] = useState("");

    const [providerAccountId, setProviderAccountId] = useState("");
    const [providerResourceId, setProviderResourceId] = useState("");
    const [region, setRegion] = useState("");
    const [storageType, setStorageType] = useState("block");
    const [capacityGb, setCapacityGb] = useState("");
    const [filesystem, setFilesystem] = useState("");
    const [storageClass, setStorageClass] = useState("");
    const [mountPath, setMountPath] = useState("");
    const [endpointUrl, setEndpointUrl] = useState("");
    const [encrypted, setEncrypted] = useState("");
    const [retentionNotes, setRetentionNotes] = useState("");

    const [backupType, setBackupType] = useState("snapshot");
    const [schedule, setSchedule] = useState("");
    const [timezone, setTimezone] = useState("");
    const [retentionDays, setRetentionDays] = useState("");
    const [retentionCopies, setRetentionCopies] = useState("");
    const [destinationStorageId, setDestinationStorageId] = useState("");
    const [backupSources, setBackupSources] = useState<number[]>([]);
    const [lastSuccessAt, setLastSuccessAt] = useState("");
    const [lastFailureAt, setLastFailureAt] = useState("");
    const [lastRestoreTestAt, setLastRestoreTestAt] = useState("");
    const [recoveryNotes, setRecoveryNotes] = useState("");

    const [orchestrator, setOrchestrator] = useState("docker_compose");
    const [hostResourceId, setHostResourceId] = useState("");
    const [projectName, setProjectName] = useState("");
    const [orchestratorVersion, setOrchestratorVersion] = useState("");
    const [composePath, setComposePath] = useState("");
    const [workingDirectory, setWorkingDirectory] = useState("");
    const [managementUrl, setManagementUrl] = useState("");

    const [distribution, setDistribution] = useState("");
    const [kubernetesVersion, setKubernetesVersion] = useState("");
    const [apiServerUrl, setApiServerUrl] = useState("");
    const [providerClusterId, setProviderClusterId] = useState("");
    const [nodeCount, setNodeCount] = useState("");
    const [highAvailability, setHighAvailability] = useState("");
    const [upgradeChannel, setUpgradeChannel] = useState("");

    const [clusterResourceId, setClusterResourceId] = useState("");
    const [namespaceName, setNamespaceName] = useState("");
    const [purpose, setPurpose] = useState("");
    const [resourceQuotaSummary, setResourceQuotaSummary] = useState("");

    const [namespaceResourceId, setNamespaceResourceId] = useState("");
    const [workloadKind, setWorkloadKind] = useState("deployment");
    const [workloadName, setWorkloadName] = useState("");
    const [replicasDesired, setReplicasDesired] = useState("");
    const [imageSummary, setImageSummary] = useState("");
    const [selectorSummary, setSelectorSummary] = useState("");
    const [serviceAccount, setServiceAccount] = useState("");

    const [serviceManager, setServiceManager] = useState("systemd");
    const [unitName, setUnitName] = useState("");
    const [displayName, setDisplayName] = useState("");
    const [expectedState, setExpectedState] = useState("");
    const [startupType, setStartupType] = useState("");
    const [executable, setExecutable] = useState("");
    const [configPath, setConfigPath] = useState("");
    const [logLocation, setLogLocation] = useState("");
    const [restartPolicy, setRestartPolicy] = useState("");

    const [scheduler, setScheduler] = useState("cron");
    const [commandSummary, setCommandSummary] = useState("");
    const [runAs, setRunAs] = useState("");
    const [enabled, setEnabled] = useState(true);
    const [nextRunAt, setNextRunAt] = useState("");
    const [notes, setNotes] = useState("");

    useEffect(() => {
        void (async () => {
            try {
                setIsLoading(true);
                setError(null);
                const [loadedOptions, specialistOptions] = await Promise.all([
                    fetchAPI(`${BASE}/options`) as Promise<OperationalOptions>,
                    fetchAPI(`${API_URL}/api/admin/infrastructure/specialist-options`) as Promise<SpecialistOptions>,
                ]);
                setOptions(loadedOptions);
                setClients(specialistOptions.clients);

                if (editResourceId !== undefined) {
                    const details = (await fetchAPI(
                        `${API_URL}/api/admin/infrastructure/resources/${editResourceId}/specialist-edit`,
                    )) as EditDetails;
                    setType(details.resource_type);
                    setOwnership(details.ownership_type);
                    setClientId(details.client_id ? String(details.client_id) : "");
                    setClientName(details.client_name);
                    setName(details.name);
                    setLifecycle(details.lifecycle_status);
                    setEnvironment(details.environment);
                    setCriticality(details.criticality);
                    setDescription(details.description);
                    const values = details.values;
                    setProviderAccountId(stringValue(values.provider_account_resource_id));
                    setProviderResourceId(stringValue(values.provider_resource_id));
                    setRegion(stringValue(values.region));
                    setStorageType(stringValue(values.storage_type) || "block");
                    setCapacityGb(numberValue(values.capacity_gb));
                    setFilesystem(stringValue(values.filesystem));
                    setStorageClass(stringValue(values.storage_class));
                    setMountPath(stringValue(values.mount_path));
                    setEndpointUrl(stringValue(values.endpoint_url));
                    setEncrypted(boolValue(values.encrypted));
                    setRetentionNotes(stringValue(values.retention_notes));
                    setBackupType(stringValue(values.backup_type) || "snapshot");
                    setSchedule(stringValue(values.schedule));
                    setTimezone(stringValue(values.timezone));
                    setRetentionDays(numberValue(values.retention_days));
                    setRetentionCopies(numberValue(values.retention_copies));
                    setDestinationStorageId(stringValue(values.destination_storage_resource_id));
                    setBackupSources(
                        Array.isArray(values.source_resource_ids)
                            ? values.source_resource_ids.map(Number)
                            : [],
                    );
                    setLastSuccessAt(dateTimeValue(values.last_success_at));
                    setLastFailureAt(dateTimeValue(values.last_failure_at));
                    setLastRestoreTestAt(dateTimeValue(values.last_restore_test_at));
                    setRecoveryNotes(stringValue(values.recovery_notes));
                    setOrchestrator(stringValue(values.orchestrator) || "docker_compose");
                    setHostResourceId(stringValue(values.host_resource_id));
                    setProjectName(stringValue(values.project_name));
                    setOrchestratorVersion(stringValue(values.orchestrator_version));
                    setComposePath(stringValue(values.compose_path));
                    setWorkingDirectory(stringValue(values.working_directory));
                    setManagementUrl(stringValue(values.management_url));
                    setDistribution(stringValue(values.distribution));
                    setKubernetesVersion(stringValue(values.version));
                    setApiServerUrl(stringValue(values.api_server_url));
                    setProviderClusterId(stringValue(values.provider_cluster_id));
                    setNodeCount(numberValue(values.node_count));
                    setHighAvailability(boolValue(values.high_availability));
                    setUpgradeChannel(stringValue(values.upgrade_channel));
                    setClusterResourceId(stringValue(values.cluster_resource_id));
                    setNamespaceName(stringValue(values.namespace));
                    setPurpose(stringValue(values.purpose));
                    setResourceQuotaSummary(stringValue(values.resource_quota_summary));
                    setNamespaceResourceId(stringValue(values.namespace_resource_id));
                    setWorkloadKind(stringValue(values.workload_kind) || "deployment");
                    setWorkloadName(stringValue(values.workload_name));
                    setReplicasDesired(numberValue(values.replicas_desired));
                    setImageSummary(stringValue(values.image_summary));
                    setSelectorSummary(stringValue(values.selector_summary));
                    setServiceAccount(stringValue(values.service_account));
                    setServiceManager(stringValue(values.manager) || "systemd");
                    setUnitName(stringValue(values.unit_name));
                    setDisplayName(stringValue(values.display_name));
                    setExpectedState(stringValue(values.expected_state));
                    setStartupType(stringValue(values.startup_type));
                    setExecutable(stringValue(values.executable));
                    setConfigPath(stringValue(values.config_path));
                    setLogLocation(stringValue(values.log_location));
                    setRestartPolicy(stringValue(values.restart_policy));
                    setScheduler(stringValue(values.scheduler) || "cron");
                    setCommandSummary(stringValue(values.command_summary));
                    setRunAs(stringValue(values.run_as));
                    setEnabled(values.enabled !== false);
                    setNextRunAt(dateTimeValue(values.next_run_at));
                    setNotes(stringValue(values.notes));
                }
            } catch (loadError) {
                setError(
                    loadError instanceof Error
                        ? loadError.message
                        : "Unable to load specialist operations form.",
                );
            } finally {
                setIsLoading(false);
            }
        })();
    }, [editResourceId]);

    const scopeClientId = ownership === "client" && clientId ? Number(clientId) : null;
    const scoped = useMemo(
        () => (items: ResourceOption[]) =>
            items.filter(
                (item) =>
                    item.ownership_type === ownership && item.client_id === scopeClientId,
            ),
        [ownership, scopeClientId],
    );

    const providers = scoped(options?.provider_accounts ?? []);
    const servers = scoped(options?.servers ?? []);
    const storages = scoped(options?.storages ?? []);
    const clusters = scoped(options?.clusters ?? []);
    const namespaces = scoped(options?.namespaces ?? []);
    const allResources = scoped(options?.resources ?? []).filter(
        (item) => item.resource_id !== editResourceId,
    );

    function commonPayload() {
        return {
            ...(isEditing
                ? {}
                : {
                      ownership_type: ownership,
                      client_id: ownership === "client" ? Number(clientId) : null,
                  }),
            name: name.trim(),
            lifecycle_status: lifecycle,
            environment,
            criticality,
            description: description.trim(),
        };
    }

    function typePayload(): Record<string, unknown> {
        if (type === "storage") {
            return {
                storage_type: storageType,
                provider_account_resource_id: numberOrNull(providerAccountId),
                provider_resource_id: providerResourceId.trim(),
                region: region.trim(),
                capacity_gb: numberOrNull(capacityGb),
                filesystem: filesystem.trim(),
                storage_class: storageClass.trim(),
                mount_path: mountPath.trim(),
                endpoint_url: endpointUrl.trim(),
                encrypted: encrypted === "yes" ? true : encrypted === "no" ? false : null,
                retention_notes: retentionNotes.trim(),
            };
        }
        if (type === "backup_plan") {
            return {
                backup_type: backupType,
                schedule: schedule.trim(),
                timezone: timezone.trim(),
                retention_days: numberOrNull(retentionDays),
                retention_copies: numberOrNull(retentionCopies),
                destination_storage_resource_id: numberOrNull(destinationStorageId),
                provider_account_resource_id: numberOrNull(providerAccountId),
                encrypted: encrypted === "yes" ? true : encrypted === "no" ? false : null,
                last_success_at: dateTimeOrNull(lastSuccessAt),
                last_failure_at: dateTimeOrNull(lastFailureAt),
                last_restore_test_at: dateTimeOrNull(lastRestoreTestAt),
                source_resource_ids: backupSources,
                recovery_notes: recoveryNotes.trim(),
            };
        }
        if (type === "container_stack") {
            return {
                orchestrator,
                host_resource_id: numberOrNull(hostResourceId),
                project_name: projectName.trim(),
                orchestrator_version: orchestratorVersion.trim(),
                compose_path: composePath.trim(),
                working_directory: workingDirectory.trim(),
                management_url: managementUrl.trim(),
                notes: notes.trim(),
            };
        }
        if (type === "kubernetes_cluster") {
            return {
                provider_account_resource_id: numberOrNull(providerAccountId),
                distribution: distribution.trim(),
                version: kubernetesVersion.trim(),
                api_server_url: apiServerUrl.trim(),
                management_url: managementUrl.trim(),
                provider_cluster_id: providerClusterId.trim(),
                region: region.trim(),
                node_count: numberOrNull(nodeCount),
                high_availability:
                    highAvailability === "yes"
                        ? true
                        : highAvailability === "no"
                          ? false
                          : null,
                upgrade_channel: upgradeChannel.trim(),
                notes: notes.trim(),
            };
        }
        if (type === "kubernetes_namespace") {
            return {
                cluster_resource_id: Number(clusterResourceId),
                namespace: namespaceName.trim(),
                purpose: purpose.trim(),
                resource_quota_summary: resourceQuotaSummary.trim(),
            };
        }
        if (type === "kubernetes_workload") {
            return {
                namespace_resource_id: Number(namespaceResourceId),
                workload_kind: workloadKind,
                workload_name: workloadName.trim(),
                replicas_desired: numberOrNull(replicasDesired),
                image_summary: imageSummary.trim(),
                selector_summary: selectorSummary.trim(),
                service_account: serviceAccount.trim(),
                notes: notes.trim(),
            };
        }
        if (type === "system_service") {
            return {
                host_resource_id: Number(hostResourceId),
                manager: serviceManager,
                unit_name: unitName.trim(),
                display_name: displayName.trim(),
                expected_state: expectedState.trim(),
                startup_type: startupType.trim(),
                executable: executable.trim(),
                config_path: configPath.trim(),
                working_directory: workingDirectory.trim(),
                log_location: logLocation.trim(),
                restart_policy: restartPolicy.trim(),
                notes: notes.trim(),
            };
        }
        return {
            scheduler,
            host_resource_id: numberOrNull(hostResourceId),
            schedule_expression: schedule.trim(),
            timezone: timezone.trim(),
            command_summary: commandSummary.trim(),
            config_path: configPath.trim(),
            working_directory: workingDirectory.trim(),
            run_as: runAs.trim(),
            enabled,
            last_success_at: dateTimeOrNull(lastSuccessAt),
            last_failure_at: dateTimeOrNull(lastFailureAt),
            next_run_at: dateTimeOrNull(nextRunAt),
            notes: notes.trim(),
        };
    }

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!name.trim()) {
            setError("Resource name is required.");
            return;
        }
        if (!isEditing && ownership === "client" && !clientId) {
            setError("Choose a client for client-owned infrastructure.");
            return;
        }
        try {
            setIsSaving(true);
            setError(null);
            const result = (await fetchAPI(
                isEditing ? `${BASE}/${endpoint(type)}/${editResourceId}` : `${BASE}/${endpoint(type)}`,
                {
                    method: isEditing ? "PUT" : "POST",
                    body: JSON.stringify({ ...commonPayload(), ...typePayload() }),
                },
            )) as SaveResult;
            if (isEditing) onSaved?.();
            else onCreated?.(result.resource_id);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to save resource.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading) return <DataLoading label="Loading specialist operations…" />;

    const selectOption = (item: ResourceOption) => (
        <option key={item.resource_id} value={item.resource_id}>
            {item.name}
        </option>
    );

    return (
        <form className="space-y-5" onSubmit={save}>
            <PageHeader
                eyebrow="Specialist operations"
                title={isEditing ? `Edit ${typeLabel(type)}` : "Add operational resource"}
                description="Track operational configuration and relationships without duplicating credentials or secret values."
            />
            {error ? <DataError message={error} /> : null}

            <Card className="space-y-4 p-5">
                {!isEditing ? (
                    <label className="block text-sm text-slate-300">
                        Resource type
                        <Select
                            className="mt-1.5"
                            value={type}
                            onChange={(event) => setType(event.target.value as OperationalType)}
                        >
                            {allowedTypes.map((item) => (
                                <option key={item} value={item}>
                                    {typeLabel(item)}
                                </option>
                            ))}
                        </Select>
                    </label>
                ) : null}
                <div className="grid gap-4 md:grid-cols-2">
                    <label className="block text-sm text-slate-300">
                        Ownership
                        <Select
                            className="mt-1.5"
                            value={ownership}
                            disabled={isEditing}
                            onChange={(event) => {
                                const value = event.target.value as "internal" | "client";
                                setOwnership(value);
                                if (value === "internal") setClientId("");
                            }}
                        >
                            <option value="internal">ADB Internal</option>
                            <option value="client">Client</option>
                        </Select>
                    </label>
                    <label className="block text-sm text-slate-300">
                        Client
                        <Select
                            className="mt-1.5"
                            value={clientId}
                            disabled={isEditing || ownership === "internal"}
                            onChange={(event) => setClientId(event.target.value)}
                        >
                            <option value="">Select client</option>
                            {clients.map((client) => (
                                <option key={client.id} value={client.id}>
                                    {client.name}
                                </option>
                            ))}
                        </Select>
                        {isEditing && clientName ? (
                            <span className="mt-1 block text-xs text-slate-500">{clientName}</span>
                        ) : null}
                    </label>
                </div>
                <label className="block text-sm text-slate-300">
                    Name
                    <Input className="mt-1.5" value={name} onChange={(event) => setName(event.target.value)} required />
                </label>
                <div className="grid gap-4 md:grid-cols-3">
                    <label className="block text-sm text-slate-300">
                        Lifecycle
                        <Select className="mt-1.5" value={lifecycle} onChange={(event) => setLifecycle(event.target.value)}>
                            {[
                                "planned",
                                "active",
                                "maintenance",
                                "deprecated",
                                "retired",
                                "archived",
                            ].map((value) => (
                                <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
                            ))}
                        </Select>
                    </label>
                    <label className="block text-sm text-slate-300">
                        Environment
                        <Select className="mt-1.5" value={environment} onChange={(event) => setEnvironment(event.target.value)}>
                            {["production", "staging", "development", "testing", "shared", "not_applicable"].map((value) => (
                                <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
                            ))}
                        </Select>
                    </label>
                    <label className="block text-sm text-slate-300">
                        Criticality
                        <Select className="mt-1.5" value={criticality} onChange={(event) => setCriticality(event.target.value)}>
                            {["low", "normal", "high", "critical"].map((value) => (
                                <option key={value} value={value}>{value}</option>
                            ))}
                        </Select>
                    </label>
                </div>
                <label className="block text-sm text-slate-300">
                    Description
                    <Textarea className="mt-1.5" value={description} onChange={(event) => setDescription(event.target.value)} rows={3} />
                </label>
            </Card>

            <Card className="space-y-4 p-5">
                <h2 className="font-semibold text-slate-100">{typeLabel(type)} details</h2>

                {(type === "storage" || type === "kubernetes_cluster" || type === "backup_plan") ? (
                    <label className="block text-sm text-slate-300">
                        Provider account
                        <Select className="mt-1.5" value={providerAccountId} onChange={(event) => setProviderAccountId(event.target.value)}>
                            <option value="">None</option>
                            {providers.map(selectOption)}
                        </Select>
                    </label>
                ) : null}

                {type === "storage" ? (
                    <>
                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="block text-sm text-slate-300">Storage type<Select className="mt-1.5" value={storageType} onChange={(event) => setStorageType(event.target.value)}>{["block", "object", "file", "volume", "disk", "bucket", "nas", "other"].map((value) => <option key={value} value={value}>{value}</option>)}</Select></label>
                            <label className="block text-sm text-slate-300">Capacity GB<Input className="mt-1.5" type="number" min="0" value={capacityGb} onChange={(event) => setCapacityGb(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Provider resource ID<Input className="mt-1.5" value={providerResourceId} onChange={(event) => setProviderResourceId(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Region<Input className="mt-1.5" value={region} onChange={(event) => setRegion(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Filesystem<Input className="mt-1.5" value={filesystem} onChange={(event) => setFilesystem(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Storage class<Input className="mt-1.5" value={storageClass} onChange={(event) => setStorageClass(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Mount path<Input className="mt-1.5" value={mountPath} onChange={(event) => setMountPath(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Endpoint URL<Input className="mt-1.5" value={endpointUrl} onChange={(event) => setEndpointUrl(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Encrypted<Select className="mt-1.5" value={encrypted} onChange={(event) => setEncrypted(event.target.value)}><option value="">Unknown</option><option value="yes">Yes</option><option value="no">No</option></Select></label>
                        </div>
                        <label className="block text-sm text-slate-300">Retention notes<Textarea className="mt-1.5" rows={3} value={retentionNotes} onChange={(event) => setRetentionNotes(event.target.value)} /></label>
                    </>
                ) : null}

                {type === "backup_plan" ? (
                    <>
                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="block text-sm text-slate-300">Backup type<Select className="mt-1.5" value={backupType} onChange={(event) => setBackupType(event.target.value)}>{["snapshot", "file", "database", "image", "volume", "object", "other"].map((value) => <option key={value} value={value}>{value}</option>)}</Select></label>
                            <label className="block text-sm text-slate-300">Schedule<Input className="mt-1.5" value={schedule} onChange={(event) => setSchedule(event.target.value)} placeholder="0 2 * * * / daily at 02:00" /></label>
                            <label className="block text-sm text-slate-300">Timezone<Input className="mt-1.5" value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Destination storage<Select className="mt-1.5" value={destinationStorageId} onChange={(event) => setDestinationStorageId(event.target.value)}><option value="">None</option>{storages.map(selectOption)}</Select></label>
                            <label className="block text-sm text-slate-300">Retention days<Input className="mt-1.5" type="number" min="0" value={retentionDays} onChange={(event) => setRetentionDays(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Retention copies<Input className="mt-1.5" type="number" min="0" value={retentionCopies} onChange={(event) => setRetentionCopies(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Last success<Input className="mt-1.5" type="datetime-local" value={lastSuccessAt} onChange={(event) => setLastSuccessAt(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Last failure<Input className="mt-1.5" type="datetime-local" value={lastFailureAt} onChange={(event) => setLastFailureAt(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Last restore test<Input className="mt-1.5" type="datetime-local" value={lastRestoreTestAt} onChange={(event) => setLastRestoreTestAt(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Encrypted<Select className="mt-1.5" value={encrypted} onChange={(event) => setEncrypted(event.target.value)}><option value="">Unknown</option><option value="yes">Yes</option><option value="no">No</option></Select></label>
                        </div>
                        <div>
                            <p className="text-sm text-slate-300">Protected resources</p>
                            <div className="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-lg border border-slate-800 p-2">
                                {allResources.map((item) => (
                                    <label key={item.resource_id} className="flex items-center gap-2 rounded px-2 py-1.5 text-sm text-slate-400 hover:bg-slate-900">
                                        <input type="checkbox" checked={backupSources.includes(item.resource_id)} onChange={() => setBackupSources((current) => current.includes(item.resource_id) ? current.filter((id) => id !== item.resource_id) : [...current, item.resource_id])} />
                                        {item.name} <span className="text-xs text-slate-600">{item.resource_type.replaceAll("_", " ")}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                        <label className="block text-sm text-slate-300">Recovery notes<Textarea className="mt-1.5" rows={4} value={recoveryNotes} onChange={(event) => setRecoveryNotes(event.target.value)} /></label>
                    </>
                ) : null}

                {type === "container_stack" ? (
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="block text-sm text-slate-300">Orchestrator<Select className="mt-1.5" value={orchestrator} onChange={(event) => setOrchestrator(event.target.value)}>{["docker_compose", "docker_swarm", "nomad", "other"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</Select></label>
                        <label className="block text-sm text-slate-300">Host server<Select className="mt-1.5" value={hostResourceId} onChange={(event) => setHostResourceId(event.target.value)}><option value="">None</option>{servers.map(selectOption)}</Select></label>
                        <label className="block text-sm text-slate-300">Project name<Input className="mt-1.5" value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Orchestrator version<Input className="mt-1.5" value={orchestratorVersion} onChange={(event) => setOrchestratorVersion(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Compose/config path<Input className="mt-1.5" value={composePath} onChange={(event) => setComposePath(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Working directory<Input className="mt-1.5" value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Management URL<Input className="mt-1.5" value={managementUrl} onChange={(event) => setManagementUrl(event.target.value)} /></label>
                    </div>
                ) : null}

                {type === "kubernetes_cluster" ? (
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="block text-sm text-slate-300">Distribution<Input className="mt-1.5" value={distribution} onChange={(event) => setDistribution(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Kubernetes version<Input className="mt-1.5" value={kubernetesVersion} onChange={(event) => setKubernetesVersion(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">API server URL<Input className="mt-1.5" value={apiServerUrl} onChange={(event) => setApiServerUrl(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Management URL<Input className="mt-1.5" value={managementUrl} onChange={(event) => setManagementUrl(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Provider cluster ID<Input className="mt-1.5" value={providerClusterId} onChange={(event) => setProviderClusterId(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Region<Input className="mt-1.5" value={region} onChange={(event) => setRegion(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Node count<Input className="mt-1.5" type="number" min="0" value={nodeCount} onChange={(event) => setNodeCount(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">High availability<Select className="mt-1.5" value={highAvailability} onChange={(event) => setHighAvailability(event.target.value)}><option value="">Unknown</option><option value="yes">Yes</option><option value="no">No</option></Select></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Upgrade channel<Input className="mt-1.5" value={upgradeChannel} onChange={(event) => setUpgradeChannel(event.target.value)} /></label>
                    </div>
                ) : null}

                {type === "kubernetes_namespace" ? (
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="block text-sm text-slate-300">Cluster<Select className="mt-1.5" value={clusterResourceId} onChange={(event) => setClusterResourceId(event.target.value)} required><option value="">Select cluster</option>{clusters.map(selectOption)}</Select></label>
                        <label className="block text-sm text-slate-300">Namespace<Input className="mt-1.5" value={namespaceName} onChange={(event) => setNamespaceName(event.target.value)} required /></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Purpose<Input className="mt-1.5" value={purpose} onChange={(event) => setPurpose(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Resource quota summary<Textarea className="mt-1.5" rows={3} value={resourceQuotaSummary} onChange={(event) => setResourceQuotaSummary(event.target.value)} /></label>
                    </div>
                ) : null}

                {type === "kubernetes_workload" ? (
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="block text-sm text-slate-300">Namespace<Select className="mt-1.5" value={namespaceResourceId} onChange={(event) => setNamespaceResourceId(event.target.value)} required><option value="">Select namespace</option>{namespaces.map(selectOption)}</Select></label>
                        <label className="block text-sm text-slate-300">Workload kind<Select className="mt-1.5" value={workloadKind} onChange={(event) => setWorkloadKind(event.target.value)}>{["deployment", "stateful_set", "daemon_set", "job", "cron_job", "replica_set", "other"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</Select></label>
                        <label className="block text-sm text-slate-300">Workload name<Input className="mt-1.5" value={workloadName} onChange={(event) => setWorkloadName(event.target.value)} required /></label>
                        <label className="block text-sm text-slate-300">Desired replicas<Input className="mt-1.5" type="number" min="0" value={replicasDesired} onChange={(event) => setReplicasDesired(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Images<Textarea className="mt-1.5" rows={3} value={imageSummary} onChange={(event) => setImageSummary(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Selector<Input className="mt-1.5" value={selectorSummary} onChange={(event) => setSelectorSummary(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Service account<Input className="mt-1.5" value={serviceAccount} onChange={(event) => setServiceAccount(event.target.value)} /></label>
                    </div>
                ) : null}

                {type === "system_service" ? (
                    <div className="grid gap-4 md:grid-cols-2">
                        <label className="block text-sm text-slate-300">Host server<Select className="mt-1.5" value={hostResourceId} onChange={(event) => setHostResourceId(event.target.value)} required><option value="">Select server</option>{servers.map(selectOption)}</Select></label>
                        <label className="block text-sm text-slate-300">Service manager<Select className="mt-1.5" value={serviceManager} onChange={(event) => setServiceManager(event.target.value)}>{["systemd", "supervisor", "windows_service", "launchd", "other"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</Select></label>
                        <label className="block text-sm text-slate-300">Unit/service name<Input className="mt-1.5" value={unitName} onChange={(event) => setUnitName(event.target.value)} required /></label>
                        <label className="block text-sm text-slate-300">Display name<Input className="mt-1.5" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Expected state<Input className="mt-1.5" value={expectedState} onChange={(event) => setExpectedState(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Startup type<Input className="mt-1.5" value={startupType} onChange={(event) => setStartupType(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Executable<Input className="mt-1.5" value={executable} onChange={(event) => setExecutable(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Config path<Input className="mt-1.5" value={configPath} onChange={(event) => setConfigPath(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Working directory<Input className="mt-1.5" value={workingDirectory} onChange={(event) => setWorkingDirectory(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300">Log location<Input className="mt-1.5" value={logLocation} onChange={(event) => setLogLocation(event.target.value)} /></label>
                        <label className="block text-sm text-slate-300 md:col-span-2">Restart policy<Input className="mt-1.5" value={restartPolicy} onChange={(event) => setRestartPolicy(event.target.value)} /></label>
                    </div>
                ) : null}

                {type === "scheduled_job" ? (
                    <>
                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="block text-sm text-slate-300">Scheduler<Select className="mt-1.5" value={scheduler} onChange={(event) => setScheduler(event.target.value)}>{["cron", "systemd_timer", "celery_beat", "kubernetes_cron_job", "windows_task", "other"].map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</Select></label>
                            <label className="block text-sm text-slate-300">Host/context<Select className="mt-1.5" value={hostResourceId} onChange={(event) => setHostResourceId(event.target.value)}><option value="">None</option>{allResources.map(selectOption)}</Select></label>
                            <label className="block text-sm text-slate-300">Schedule expression<Input className="mt-1.5" value={schedule} onChange={(event) => setSchedule(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Timezone<Input className="mt-1.5" value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Run as<Input className="mt-1.5" value={runAs} onChange={(event) => setRunAs(event.target.value)} /></label>
                            <label className="flex items-center gap-2 pt-7 text-sm text-slate-300"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />Enabled</label>
                            <label className="block text-sm text-slate-300">Last success<Input className="mt-1.5" type="datetime-local" value={lastSuccessAt} onChange={(event) => setLastSuccessAt(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300">Last failure<Input className="mt-1.5" type="datetime-local" value={lastFailureAt} onChange={(event) => setLastFailureAt(event.target.value)} /></label>
                            <label className="block text-sm text-slate-300 md:col-span-2">Next run<Input className="mt-1.5" type="datetime-local" value={nextRunAt} onChange={(event) => setNextRunAt(event.target.value)} /></label>
                        </div>
                        <label className="block text-sm text-slate-300">Command/job summary<Textarea className="mt-1.5" rows={3} value={commandSummary} onChange={(event) => setCommandSummary(event.target.value)} /></label>
                    </>
                ) : null}

                {(type === "container_stack" || type === "kubernetes_cluster" || type === "kubernetes_workload" || type === "system_service" || type === "scheduled_job") ? (
                    <label className="block text-sm text-slate-300">Notes<Textarea className="mt-1.5" rows={3} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
                ) : null}

                {(type === "container_stack" || type === "kubernetes_cluster" || type === "kubernetes_workload" || type === "system_service" || type === "scheduled_job") ? (
                    <p className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 text-xs leading-5 text-amber-200/80">
                        Store only non-secret operational summaries here. Passwords, tokens, private keys and certificate material belong in Credential Vault and should be linked to the resource there.
                    </p>
                ) : null}
            </Card>

            <div className="flex justify-end gap-3">
                <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
                <Button type="submit" disabled={isSaving}>{isSaving ? "Saving…" : isEditing ? "Save changes" : "Create resource"}</Button>
            </div>
        </form>
    );
}

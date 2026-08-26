"use client";

import { RecordDrawer } from "@/components/admin/RecordDrawer";
import {
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    PageHeader,
    Pagination,
    Select,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { useCallback, useEffect, useMemo, useState } from "react";
import { InfrastructureResourceWorkspace } from "./[id]/InfrastructureResourceWorkspace";
import {
    DataApplicationInfrastructureForm,
    DataApplicationType,
} from "./DataApplicationInfrastructureForm";
import { StructuredInfrastructureForm } from "./StructuredInfrastructureForm";
import {
    WebDomainInfrastructureForm,
    WebDomainType,
} from "./WebDomainInfrastructureForm";

type ComputeNetworkType = "server" | "network" | "subnet";

interface ResourceSummary {
    id: number;
    name: string;
    resource_type: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    tags: { id: number; name: string; slug: string; colour: string }[];
    updated_at: string;
}

interface ResourcePage {
    items: ResourceSummary[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

const PAGE_SIZE = 25;

const RESOURCE_TYPES = [
    "server",
    "network",
    "subnet",
    "database_instance",
    "logical_database",
    "application",
    "application_environment",
    "source_repository",
    "website",
    "website_endpoint",
    "domain",
    "dns_zone",
    "tls_certificate",
    "provider_account",
    "storage",
    "backup_plan",
    "container_stack",
    "kubernetes_cluster",
    "kubernetes_namespace",
    "kubernetes_workload",
    "system_service",
    "scheduled_job",
    "api",
    "bot",
    "mobile_app",
    "licence",
    "email_system",
    "network_device",
    "other",
] as const;

const LIFECYCLE = [
    "current",
    "all",
    "planned",
    "active",
    "maintenance",
    "deprecated",
    "retired",
    "archived",
] as const;

const ENVIRONMENTS = [
    "production",
    "staging",
    "development",
    "testing",
    "shared",
    "not_applicable",
] as const;

function label(value: string): string {
    const special: Record<string, string> = {
        all: "All",
        current: "Current",
        not_applicable: "Not applicable",
        database_instance: "Database instance",
        logical_database: "Logical database",
        application_environment: "Application environment",
        source_repository: "Source repository",
        website_endpoint: "Website endpoint",
        dns_zone: "DNS zone",
        tls_certificate: "TLS certificate",
        provider_account: "Provider account",
        backup_plan: "Backup plan",
        container_stack: "Container stack",
        kubernetes_cluster: "Kubernetes cluster",
        kubernetes_namespace: "Kubernetes namespace",
        kubernetes_workload: "Kubernetes workload",
        system_service: "System service",
        scheduled_job: "Scheduled job",
        mobile_app: "Mobile app",
        email_system: "Email system",
        network_device: "Network device",
    };
    return (
        special[value] ??
        `${value.charAt(0).toUpperCase()}${value.slice(1).replaceAll("_", " ")}`
    );
}

export function InfrastructureResourcesWorkspace() {
    const { hasPermission } = useAuth();
    const [data, setData] = useState<ResourcePage | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [ownership, setOwnership] = useState("all");
    const [lifecycle, setLifecycle] = useState("current");
    const [resourceType, setResourceType] = useState("all");
    const [environment, setEnvironment] = useState("all");
    const [selectedResourceId, setSelectedResourceId] = useState<number | null>(
        null,
    );
    const [showComputeCreate, setShowComputeCreate] = useState(false);
    const [showDataCreate, setShowDataCreate] = useState(false);
    const [showWebCreate, setShowWebCreate] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const computeTypes: ComputeNetworkType[] = [];
    const dataTypes: DataApplicationType[] = [];
    const webTypes: WebDomainType[] = [];
    if (hasPermission("infrastructure.add_infrastructureresource")) {
        if (hasPermission("infrastructure.add_serverprofile"))
            computeTypes.push("server");
        if (hasPermission("infrastructure.add_network"))
            computeTypes.push("network");
        if (hasPermission("infrastructure.add_subnet"))
            computeTypes.push("subnet");
        if (hasPermission("infrastructure.add_databaseinstance")) {
            dataTypes.push("database_instance");
        }
        if (hasPermission("infrastructure.add_logicaldatabase")) {
            dataTypes.push("logical_database");
        }
        if (hasPermission("infrastructure.add_applicationprofile")) {
            dataTypes.push("application");
        }
        if (hasPermission("infrastructure.add_applicationenvironment")) {
            dataTypes.push("application_environment");
        }
        if (hasPermission("infrastructure.add_sourcerepository")) {
            dataTypes.push("source_repository");
        }
        if (hasPermission("infrastructure.add_websiteprofile"))
            webTypes.push("website");
        if (hasPermission("infrastructure.add_websiteendpoint")) {
            webTypes.push("website_endpoint");
        }
        if (hasPermission("infrastructure.add_domainprofile"))
            webTypes.push("domain");
        if (hasPermission("infrastructure.add_dnszone"))
            webTypes.push("dns_zone");
        if (hasPermission("infrastructure.add_tlscertificate")) {
            webTypes.push("tls_certificate");
        }
    }

    const url = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
            ownership,
            lifecycle,
        });
        if (search.trim()) params.set("search", search.trim());
        if (resourceType !== "all") params.set("resource_type", resourceType);
        if (environment !== "all") params.set("environment", environment);
        return `${API_URL}/api/admin/infrastructure/resources?${params.toString()}`;
    }, [environment, lifecycle, ownership, page, resourceType, search]);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            setData((await fetchAPI(url)) as ResourcePage);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load structured infrastructure resources.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [url]);

    useEffect(() => {
        void load();
    }, [load]);

    function resetPage() {
        setPage(1);
    }

    function openCreatedResource(resourceId: number) {
        setShowComputeCreate(false);
        setShowDataCreate(false);
        setShowWebCreate(false);
        setSelectedResourceId(resourceId);
        void load();
    }

    if (isLoading && !data) {
        return <DataLoading label="Loading structured infrastructure..." />;
    }
    if (error || !data) {
        return (
            <DataError
                message={error || "Structured infrastructure is unavailable."}
                onRetry={() => void load()}
            />
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                eyebrow="Technical operations"
                title="Structured resources"
                description="The shared operational resource graph across ADB Internal and Client infrastructure. Open a resource to see its technical details, credentials and relationships in context."
                actions={
                    <>
                        {computeTypes.length > 0 ? (
                            <Button
                                type="button"
                                onClick={() => {
                                    setSelectedResourceId(null);
                                    setShowDataCreate(false);
                                    setShowWebCreate(false);
                                    setShowComputeCreate(true);
                                }}
                            >
                                Add compute / network
                            </Button>
                        ) : null}
                        {dataTypes.length > 0 ? (
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => {
                                    setSelectedResourceId(null);
                                    setShowComputeCreate(false);
                                    setShowWebCreate(false);
                                    setShowDataCreate(true);
                                }}
                            >
                                Add data / application
                            </Button>
                        ) : null}
                        {webTypes.length > 0 ? (
                            <Button
                                type="button"
                                variant="secondary"
                                onClick={() => {
                                    setSelectedResourceId(null);
                                    setShowComputeCreate(false);
                                    setShowDataCreate(false);
                                    setShowWebCreate(true);
                                }}
                            >
                                Add web / domain
                            </Button>
                        ) : null}
                        <ButtonLink
                            href="/admin/infrastructure"
                            variant="secondary"
                        >
                            Infrastructure overview
                        </ButtonLink>
                        <ButtonLink
                            href="/admin/infrastructure/reconciliation"
                            variant="secondary"
                        >
                            Reconcile legacy records
                        </ButtonLink>
                    </>
                }
            />

            <Card className="p-4">
                <div className="grid gap-3 lg:grid-cols-[minmax(14rem,2fr)_repeat(4,minmax(10rem,1fr))]">
                    <Input
                        aria-label="Search resources"
                        placeholder="Search name, description, client or tag..."
                        value={search}
                        onChange={(event) => {
                            setSearch(event.target.value);
                            resetPage();
                        }}
                    />
                    <Select
                        aria-label="Ownership"
                        value={ownership}
                        onChange={(event) => {
                            setOwnership(event.target.value);
                            resetPage();
                        }}
                    >
                        <option value="all">All ownership</option>
                        <option value="internal">ADB Internal</option>
                        <option value="client">Client-owned</option>
                    </Select>
                    <Select
                        aria-label="Lifecycle"
                        value={lifecycle}
                        onChange={(event) => {
                            setLifecycle(event.target.value);
                            resetPage();
                        }}
                    >
                        {LIFECYCLE.map((value) => (
                            <option key={value} value={value}>
                                {label(value)} lifecycle
                            </option>
                        ))}
                    </Select>
                    <Select
                        aria-label="Resource type"
                        value={resourceType}
                        onChange={(event) => {
                            setResourceType(event.target.value);
                            resetPage();
                        }}
                    >
                        <option value="all">All resource types</option>
                        {RESOURCE_TYPES.map((value) => (
                            <option key={value} value={value}>
                                {label(value)}
                            </option>
                        ))}
                    </Select>
                    <Select
                        aria-label="Environment"
                        value={environment}
                        onChange={(event) => {
                            setEnvironment(event.target.value);
                            resetPage();
                        }}
                    >
                        <option value="all">All environments</option>
                        {ENVIRONMENTS.map((value) => (
                            <option key={value} value={value}>
                                {label(value)}
                            </option>
                        ))}
                    </Select>
                </div>
            </Card>

            <Card className="overflow-hidden">
                <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                    <div>
                        <h2 className="text-sm font-semibold text-white">
                            Resource register
                        </h2>
                        <p className="mt-0.5 text-xs text-slate-500">
                            {data.total.toLocaleString("en-GB")} resources match
                            this view.
                        </p>
                    </div>
                    {isLoading ? (
                        <span className="text-xs text-slate-600">
                            Refreshing…
                        </span>
                    ) : null}
                </div>

                {data.items.length === 0 ? (
                    <div className="p-5">
                        <EmptyState
                            title="No resources match this view"
                            description="Try changing the filters, create a native structured resource, or reconcile an existing infrastructure record into the graph."
                        />
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-800 text-sm">
                            <thead className="bg-slate-950/60 text-left text-[11px] font-semibold tracking-wide text-slate-500 uppercase">
                                <tr>
                                    <th className="px-4 py-3">Resource</th>
                                    <th className="px-4 py-3">Type</th>
                                    <th className="px-4 py-3">Owner</th>
                                    <th className="px-4 py-3">Environment</th>
                                    <th className="px-4 py-3">Lifecycle</th>
                                    <th className="px-4 py-3">Criticality</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/80">
                                {data.items.map((resource) => (
                                    <tr
                                        key={resource.id}
                                        className="bg-slate-900/20 hover:bg-slate-900/55"
                                    >
                                        <td className="px-4 py-3">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    setSelectedResourceId(
                                                        resource.id,
                                                    )
                                                }
                                                className="hover:text-adb-cyan-300 text-left font-medium text-slate-100"
                                            >
                                                {resource.name}
                                            </button>
                                            {resource.tags.length > 0 ? (
                                                <div className="mt-1 flex flex-wrap gap-1">
                                                    {resource.tags.map(
                                                        (tag) => (
                                                            <span
                                                                key={tag.id}
                                                                className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400"
                                                            >
                                                                {tag.name}
                                                            </span>
                                                        ),
                                                    )}
                                                </div>
                                            ) : null}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {label(resource.resource_type)}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {resource.client_name ||
                                                "ADB Internal"}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {label(resource.environment)}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {label(resource.lifecycle_status)}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span
                                                className={
                                                    resource.criticality ===
                                                    "critical"
                                                        ? "text-red-300"
                                                        : resource.criticality ===
                                                            "high"
                                                          ? "text-amber-300"
                                                          : "text-slate-400"
                                                }
                                            >
                                                {label(resource.criticality)}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <Pagination
                    page={data.page}
                    pageSize={data.page_size}
                    totalItems={data.total}
                    onPageChange={setPage}
                    disabled={isLoading}
                />
            </Card>

            {showComputeCreate ? (
                <RecordDrawer onClose={() => setShowComputeCreate(false)}>
                    <StructuredInfrastructureForm
                        allowedTypes={computeTypes}
                        onCancel={() => setShowComputeCreate(false)}
                        onCreated={openCreatedResource}
                    />
                </RecordDrawer>
            ) : null}

            {showDataCreate ? (
                <RecordDrawer onClose={() => setShowDataCreate(false)}>
                    <DataApplicationInfrastructureForm
                        allowedTypes={dataTypes}
                        onCancel={() => setShowDataCreate(false)}
                        onCreated={openCreatedResource}
                    />
                </RecordDrawer>
            ) : null}

            {showWebCreate ? (
                <RecordDrawer onClose={() => setShowWebCreate(false)}>
                    <WebDomainInfrastructureForm
                        allowedTypes={webTypes}
                        onCancel={() => setShowWebCreate(false)}
                        onCreated={openCreatedResource}
                    />
                </RecordDrawer>
            ) : null}

            {selectedResourceId !== null ? (
                <RecordDrawer
                    onClose={() => {
                        setSelectedResourceId(null);
                        void load();
                    }}
                    fullPageHref={`/admin/infrastructure/resources/${selectedResourceId}`}
                >
                    <InfrastructureResourceWorkspace
                        resourceId={selectedResourceId}
                        presentation="drawer"
                    />
                </RecordDrawer>
            ) : null}
        </div>
    );
}

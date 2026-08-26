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
import { StructuredInfrastructureForm } from "./StructuredInfrastructureForm";

type SpecialistType = "server" | "network" | "subnet";

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
    return special[value] ?? `${value.charAt(0).toUpperCase()}${value.slice(1).replaceAll("_", " ")}`;
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
    const [selectedResourceId, setSelectedResourceId] = useState<number | null>(null);
    const [showCreate, setShowCreate] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const allowedTypes: SpecialistType[] = [];
    if (hasPermission("infrastructure.add_infrastructureresource")) {
        if (hasPermission("infrastructure.add_serverprofile")) allowedTypes.push("server");
        if (hasPermission("infrastructure.add_network")) allowedTypes.push("network");
        if (hasPermission("infrastructure.add_subnet")) allowedTypes.push("subnet");
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
                        {allowedTypes.length > 0 ? (
                            <Button
                                type="button"
                                onClick={() => {
                                    setSelectedResourceId(null);
                                    setShowCreate(true);
                                }}
                            >
                                Add structured resource
                            </Button>
                        ) : null}
                        <ButtonLink href="/admin/infrastructure" variant="secondary">
                            Infrastructure overview
                        </ButtonLink>
                        <ButtonLink href="/admin/infrastructure/reconciliation" variant="secondary">
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
                        <h2 className="text-sm font-semibold text-white">Resource register</h2>
                        <p className="mt-0.5 text-xs text-slate-500">
                            {data.total.toLocaleString("en-GB")} resources match this view.
                        </p>
                    </div>
                    {isLoading ? <span className="text-xs text-slate-600">Refreshing…</span> : null}
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
                                    <tr key={resource.id} className="bg-slate-900/20 hover:bg-slate-900/55">
                                        <td className="px-4 py-3">
                                            <button
                                                type="button"
                                                onClick={() => setSelectedResourceId(resource.id)}
                                                className="text-left font-medium text-slate-100 hover:text-adb-cyan-300"
                                            >
                                                {resource.name}
                                            </button>
                                            {resource.tags.length > 0 ? (
                                                <div className="mt-1 flex flex-wrap gap-1">
                                                    {resource.tags.map((tag) => (
                                                        <span
                                                            key={tag.id}
                                                            className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400"
                                                        >
                                                            {tag.name}
                                                        </span>
                                                    ))}
                                                </div>
                                            ) : null}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">{label(resource.resource_type)}</td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {resource.client_name || "ADB Internal"}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">{label(resource.environment)}</td>
                                        <td className="px-4 py-3 text-slate-400">{label(resource.lifecycle_status)}</td>
                                        <td className="px-4 py-3">
                                            <span
                                                className={
                                                    resource.criticality === "critical"
                                                        ? "text-red-300"
                                                        : resource.criticality === "high"
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

            {showCreate ? (
                <RecordDrawer onClose={() => setShowCreate(false)}>
                    <StructuredInfrastructureForm
                        allowedTypes={allowedTypes}
                        onCancel={() => setShowCreate(false)}
                        onCreated={(resourceId) => {
                            setShowCreate(false);
                            setSelectedResourceId(resourceId);
                            void load();
                        }}
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

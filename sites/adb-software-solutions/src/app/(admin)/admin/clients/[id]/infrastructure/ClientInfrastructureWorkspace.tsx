"use client";

import {
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
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

interface ResourceSummary {
    id: number;
    name: string;
    resource_type: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    client_name: string | null;
    tags: { id: number; name: string }[];
}

interface ResourcePage {
    items: ResourceSummary[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

const PAGE_SIZE = 20;

const RESOURCE_TYPES = [
    "server",
    "database_instance",
    "application",
    "website",
    "domain",
    "tls_certificate",
    "api",
    "bot",
    "mobile_app",
    "licence",
    "email_system",
    "provider_account",
    "network",
    "storage",
    "backup_plan",
    "other",
] as const;

function label(value: string): string {
    const special: Record<string, string> = {
        not_applicable: "Not applicable",
        database_instance: "Database instance",
        tls_certificate: "TLS certificate",
        mobile_app: "Mobile app",
        email_system: "Email system",
        provider_account: "Provider account",
        backup_plan: "Backup plan",
    };
    return special[value] ?? `${value.charAt(0).toUpperCase()}${value.slice(1).replaceAll("_", " ")}`;
}

export function ClientInfrastructureWorkspace({ clientId }: { clientId: number }) {
    const [data, setData] = useState<ResourcePage | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [lifecycle, setLifecycle] = useState("current");
    const [resourceType, setResourceType] = useState("all");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const url = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
            ownership: "client",
            client_id: String(clientId),
            lifecycle,
        });
        if (search.trim()) params.set("search", search.trim());
        if (resourceType !== "all") params.set("resource_type", resourceType);
        return `${API_URL}/api/admin/infrastructure/resources?${params.toString()}`;
    }, [clientId, lifecycle, page, resourceType, search]);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            setData((await fetchAPI(url)) as ResourcePage);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load client infrastructure.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [url]);

    useEffect(() => {
        void load();
    }, [load]);

    if (isLoading && !data) {
        return <DataLoading label="Loading client infrastructure..." />;
    }
    if (error || !data) {
        return (
            <DataError
                message={error || "Client infrastructure is unavailable."}
                onRetry={() => void load()}
            />
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                eyebrow="Client workspace"
                title={data.items[0]?.client_name ? `${data.items[0].client_name} infrastructure` : "Client infrastructure"}
                description="Structured technical resources owned by this client, using the same access scope and resource graph as the global Infrastructure workspace."
                actions={
                    <>
                        <ButtonLink href={`/admin/clients/${clientId}`} variant="secondary">
                            Back to client
                        </ButtonLink>
                        <ButtonLink href="/admin/infrastructure/resources" variant="ghost">
                            Global resources
                        </ButtonLink>
                    </>
                }
            />

            <Card className="p-4">
                <div className="grid gap-3 md:grid-cols-[minmax(14rem,2fr)_minmax(10rem,1fr)_minmax(12rem,1fr)]">
                    <Input
                        aria-label="Search client infrastructure"
                        placeholder="Search this client's resources..."
                        value={search}
                        onChange={(event) => {
                            setSearch(event.target.value);
                            setPage(1);
                        }}
                    />
                    <Select
                        aria-label="Lifecycle"
                        value={lifecycle}
                        onChange={(event) => {
                            setLifecycle(event.target.value);
                            setPage(1);
                        }}
                    >
                        <option value="current">Current resources</option>
                        <option value="all">All lifecycle states</option>
                        <option value="planned">Planned</option>
                        <option value="active">Active</option>
                        <option value="maintenance">Maintenance</option>
                        <option value="deprecated">Deprecated</option>
                        <option value="retired">Retired</option>
                        <option value="archived">Archived</option>
                    </Select>
                    <Select
                        aria-label="Resource type"
                        value={resourceType}
                        onChange={(event) => {
                            setResourceType(event.target.value);
                            setPage(1);
                        }}
                    >
                        <option value="all">All resource types</option>
                        {RESOURCE_TYPES.map((value) => (
                            <option key={value} value={value}>
                                {label(value)}
                            </option>
                        ))}
                    </Select>
                </div>
            </Card>

            <Card className="overflow-hidden">
                <div className="border-b border-slate-800 px-4 py-3">
                    <h2 className="text-sm font-semibold text-white">Technical resources</h2>
                    <p className="mt-0.5 text-xs text-slate-500">
                        {data.total.toLocaleString("en-GB")} resources match this view.
                    </p>
                </div>
                {data.items.length === 0 ? (
                    <div className="p-5">
                        <EmptyState
                            title="No client infrastructure in this view"
                            description="Reconcile existing technical records as Client-owned resources, or change the current filters."
                        />
                    </div>
                ) : (
                    <div className="divide-y divide-slate-800/80">
                        {data.items.map((resource) => (
                            <Link
                                key={resource.id}
                                href={`/admin/infrastructure/resources/${resource.id}`}
                                className="flex flex-col gap-3 px-4 py-4 transition hover:bg-slate-900/60 sm:flex-row sm:items-center sm:justify-between"
                            >
                                <div className="min-w-0">
                                    <div className="font-medium text-slate-100">{resource.name}</div>
                                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                                        <span>{label(resource.resource_type)}</span>
                                        <span>·</span>
                                        <span>{label(resource.environment)}</span>
                                        {resource.tags.map((tag) => (
                                            <span key={tag.id} className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                                                {tag.name}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex shrink-0 items-center gap-3 text-xs">
                                    <span className="text-slate-500">{label(resource.lifecycle_status)}</span>
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
                                </div>
                            </Link>
                        ))}
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
        </div>
    );
}

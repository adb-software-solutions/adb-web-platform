"use client";

import { RecordDrawer } from "@/components/admin/RecordDrawer";
import {
    Badge,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    Pagination,
    Select,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeaderCell,
    TableRow,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { OverviewAPI } from "@/lib/api/overview";
import { useCallback, useEffect, useMemo, useState } from "react";
import { LeadWorkspace } from "./[id]/LeadWorkspace";
import { LeadEmailPanel } from "./LeadEmailPanel";

interface Lookup {
    id: number;
    name: string;
}

interface Assignee {
    id: string;
    name: string;
    email: string;
}

interface LeadOptions {
    statuses: Lookup[];
    sources: Lookup[];
    assignees: Assignee[];
}

interface Brand {
    id: number;
    name: string;
    is_active: boolean;
}

interface LeadOverviewItem {
    id: number;
    name: string;
    company: string;
    email: string;
    status: string;
    source: string;
    brand: string;
    assigned_to_name: string | null;
    converted_at: string | null;
    created_at: string;
}

interface LeadStats {
    total: number;
    open: number;
    converted: number;
    unassigned: number;
    new_last_30_days: number;
}

interface LeadOverviewResponse {
    items: LeadOverviewItem[];
    stats: LeadStats;
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

function statusClasses(status: string) {
    const normalised = status.toLowerCase();
    if (normalised === "won") {
        return "border-emerald-900/70 bg-emerald-950/50 text-emerald-300";
    }
    if (normalised === "lost") {
        return "border-red-950 bg-red-950/30 text-red-300";
    }
    if (normalised === "proposal" || normalised === "qualified") {
        return "border-cyan-900/70 bg-cyan-950/40 text-cyan-300";
    }
    return "border-amber-900/70 bg-amber-950/40 text-amber-300";
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(value));
}

function StatCard({
    label,
    value,
    detail,
    active = false,
    onClick,
}: {
    label: string;
    value: number;
    detail: string;
    active?: boolean;
    onClick?: () => void;
}) {
    const content = (
        <>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                {label}
            </div>
            <div className="mt-2 text-2xl font-semibold tabular-nums text-white">{value}</div>
            <div className="mt-1 text-xs text-slate-500">{detail}</div>
        </>
    );

    if (!onClick) return <Card className="p-4">{content}</Card>;

    return (
        <button
            type="button"
            onClick={onClick}
            className={`rounded-xl border p-4 text-left transition ${
                active
                    ? "border-adb-cyan-500/60 bg-adb-cyan-950/20"
                    : "border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/60"
            }`}
        >
            {content}
        </button>
    );
}

export function LeadList() {
    const [data, setData] = useState<LeadOverviewResponse | null>(null);
    const [options, setOptions] = useState<LeadOptions>({
        statuses: [],
        sources: [],
        assignees: [],
    });
    const [brands, setBrands] = useState<Brand[]>([]);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [statusId, setStatusId] = useState("");
    const [sourceId, setSourceId] = useState("");
    const [brandId, setBrandId] = useState("");
    const [assignedToId, setAssignedToId] = useState("");
    const [pipelineState, setPipelineState] = useState<"" | "open" | "converted">("");
    const [selectedLeadId, setSelectedLeadId] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const query = useMemo(() => {
        const params = new URLSearchParams({ page: String(page), page_size: "25" });
        if (search.trim()) params.set("search", search.trim());
        if (statusId) params.set("status_id", statusId);
        if (sourceId) params.set("source_id", sourceId);
        if (brandId) params.set("brand_id", brandId);
        if (assignedToId) params.set("assigned_to_id", assignedToId);
        if (pipelineState === "open") params.set("converted", "false");
        if (pipelineState === "converted") params.set("converted", "true");
        return params.toString();
    }, [assignedToId, brandId, page, pipelineState, search, sourceId, statusId]);

    const loadLeads = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [overview, leadOptions, brandRows] = await Promise.all([
                fetchAPI(OverviewAPI.leads(query)) as Promise<LeadOverviewResponse>,
                fetchAPI(AdminAPI.leads.options()) as Promise<LeadOptions>,
                fetchAPI(AdminAPI.brands.list()) as Promise<Brand[]>,
            ]);
            setData(overview);
            setOptions(leadOptions);
            setBrands(brandRows);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "An unexpected error occurred while loading leads.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [query]);

    useEffect(() => {
        const timeout = window.setTimeout(() => void loadLeads(), 180);
        return () => window.clearTimeout(timeout);
    }, [loadLeads]);

    useEffect(() => {
        setPage(1);
    }, [assignedToId, brandId, pipelineState, search, sourceId, statusId]);

    if (isLoading && !data) return <DataLoading label="Loading sales pipeline..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void loadLeads()} />;

    const leads = data?.items ?? [];
    const stats = data?.stats;

    return (
        <div className="space-y-5">
            {stats ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                    <StatCard
                        label="All leads"
                        value={stats.total}
                        detail="Visible CRM opportunities"
                        active={!pipelineState}
                        onClick={() => setPipelineState("")}
                    />
                    <StatCard
                        label="Open"
                        value={stats.open}
                        detail="Not yet converted"
                        active={pipelineState === "open"}
                        onClick={() => setPipelineState(pipelineState === "open" ? "" : "open")}
                    />
                    <StatCard
                        label="New · 30 days"
                        value={stats.new_last_30_days}
                        detail="Recently captured opportunities"
                    />
                    <StatCard
                        label="Unassigned"
                        value={stats.unassigned}
                        detail="Open leads needing an owner"
                    />
                    <StatCard
                        label="Converted"
                        value={stats.converted}
                        detail="Converted into client accounts"
                        active={pipelineState === "converted"}
                        onClick={() =>
                            setPipelineState(pipelineState === "converted" ? "" : "converted")
                        }
                    />
                </div>
            ) : null}

            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                <div className="grid gap-3 border-b border-slate-800 p-4 xl:grid-cols-[minmax(240px,1.5fr)_repeat(5,minmax(150px,1fr))]">
                    <Input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search name, company, email or enquiry..."
                        aria-label="Search leads"
                    />
                    <Select
                        value={pipelineState}
                        onChange={(event) =>
                            setPipelineState(event.target.value as "" | "open" | "converted")
                        }
                    >
                        <option value="">All pipeline states</option>
                        <option value="open">Open</option>
                        <option value="converted">Converted</option>
                    </Select>
                    <Select value={statusId} onChange={(event) => setStatusId(event.target.value)}>
                        <option value="">All statuses</option>
                        {options.statuses.map((status) => (
                            <option key={status.id} value={status.id}>
                                {status.name}
                            </option>
                        ))}
                    </Select>
                    <Select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
                        <option value="">All sources</option>
                        {options.sources.map((source) => (
                            <option key={source.id} value={source.id}>
                                {source.name}
                            </option>
                        ))}
                    </Select>
                    <Select value={brandId} onChange={(event) => setBrandId(event.target.value)}>
                        <option value="">All brands</option>
                        {brands.map((brand) => (
                            <option key={brand.id} value={brand.id}>
                                {brand.name}
                            </option>
                        ))}
                    </Select>
                    <Select
                        value={assignedToId}
                        onChange={(event) => setAssignedToId(event.target.value)}
                    >
                        <option value="">All owners</option>
                        {options.assignees.map((assignee) => (
                            <option key={assignee.id} value={assignee.id}>
                                {assignee.name}
                            </option>
                        ))}
                    </Select>
                </div>

                {error ? (
                    <div className="border-b border-slate-800 p-4">
                        <DataError message={error} onRetry={() => void loadLeads()} />
                    </div>
                ) : null}

                {leads.length === 0 ? (
                    <EmptyState
                        title="No leads match this view"
                        description="Try changing the search or pipeline filters."
                    />
                ) : (
                    <Table>
                        <TableHead>
                            <tr>
                                <TableHeaderCell>Lead</TableHeaderCell>
                                <TableHeaderCell>Status</TableHeaderCell>
                                <TableHeaderCell>Owner</TableHeaderCell>
                                <TableHeaderCell>Brand</TableHeaderCell>
                                <TableHeaderCell>Source</TableHeaderCell>
                                <TableHeaderCell>Received</TableHeaderCell>
                            </tr>
                        </TableHead>
                        <TableBody>
                            {leads.map((lead) => (
                                <TableRow key={lead.id}>
                                    <TableCell>
                                        <button
                                            type="button"
                                            onClick={() => setSelectedLeadId(lead.id)}
                                            className="text-left font-medium text-slate-100 transition hover:text-cyan-300"
                                        >
                                            {lead.company || lead.name}
                                        </button>
                                        <div className="mt-1 text-xs text-slate-500">
                                            {lead.name} · {lead.email}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Badge className={statusClasses(lead.status)}>{lead.status}</Badge>
                                        {lead.converted_at ? (
                                            <div className="mt-1 text-xs text-emerald-500">Converted</div>
                                        ) : null}
                                    </TableCell>
                                    <TableCell className="text-slate-400">
                                        {lead.assigned_to_name || "Unassigned"}
                                    </TableCell>
                                    <TableCell className="text-slate-400">{lead.brand}</TableCell>
                                    <TableCell className="text-slate-400">{lead.source}</TableCell>
                                    <TableCell className="text-slate-400">
                                        {formatDate(lead.created_at)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}

                <Pagination
                    page={data?.page ?? page}
                    pageSize={data?.page_size ?? 25}
                    totalItems={data?.total ?? 0}
                    onPageChange={setPage}
                    disabled={isLoading}
                />
            </div>

            {selectedLeadId ? (
                <RecordDrawer
                    fullPageHref={`/admin/leads/${selectedLeadId}`}
                    onClose={() => {
                        setSelectedLeadId(null);
                        void loadLeads();
                    }}
                >
                    <div className="space-y-6">
                        <LeadWorkspace leadId={selectedLeadId} />
                        <LeadEmailPanel leadId={selectedLeadId} />
                    </div>
                </RecordDrawer>
            ) : null}
        </div>
    );
}

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
import { OverviewAPI } from "@/lib/api/overview";
import { fetchAPI } from "@/lib/api/fetch";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ClientWorkspace } from "./[id]/ClientWorkspace";

interface ClientOverviewItem {
    id: number;
    name: string;
    company: string;
    email: string;
    status: string;
    contact_count: number;
    project_count: number;
    active_project_count: number;
}

interface ClientStats {
    total: number;
    active: number;
    inactive: number;
    archived: number;
    contacts: number;
    projects: number;
}

interface ClientOverviewResponse {
    items: ClientOverviewItem[];
    stats: ClientStats;
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

function statusClasses(status: string) {
    if (status === "active") {
        return "border-emerald-900/70 bg-emerald-950/50 text-emerald-300";
    }
    if (status === "archived") {
        return "border-slate-700 bg-slate-900 text-slate-500";
    }
    return "border-amber-900/70 bg-amber-950/40 text-amber-300";
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

export function ClientList() {
    const [data, setData] = useState<ClientOverviewResponse | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("");
    const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const query = useMemo(() => {
        const params = new URLSearchParams({ page: String(page), page_size: "25" });
        if (search.trim()) params.set("search", search.trim());
        if (status) params.set("status", status);
        return params.toString();
    }, [page, search, status]);

    const loadClients = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            setData((await fetchAPI(OverviewAPI.clients(query))) as ClientOverviewResponse);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "An unexpected error occurred while loading clients.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [query]);

    useEffect(() => {
        const timeout = window.setTimeout(() => void loadClients(), 180);
        return () => window.clearTimeout(timeout);
    }, [loadClients]);

    useEffect(() => {
        setPage(1);
    }, [search, status]);

    if (isLoading && !data) return <DataLoading label="Loading client accounts..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void loadClients()} />;

    const clients = data?.items ?? [];
    const stats = data?.stats;

    return (
        <div className="space-y-5">
            {stats ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <StatCard
                        label="Clients"
                        value={stats.total}
                        detail={`${stats.inactive} inactive · ${stats.archived} archived`}
                        active={!status}
                        onClick={() => setStatus("")}
                    />
                    <StatCard
                        label="Active"
                        value={stats.active}
                        detail="Current client accounts"
                        active={status === "active"}
                        onClick={() => setStatus(status === "active" ? "" : "active")}
                    />
                    <StatCard
                        label="Contacts"
                        value={stats.contacts}
                        detail="People across visible accounts"
                    />
                    <StatCard
                        label="Projects"
                        value={stats.projects}
                        detail="Current and historical delivery"
                    />
                </div>
            ) : null}

            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                <div className="grid gap-3 border-b border-slate-800 p-4 md:grid-cols-[minmax(0,1fr)_220px]">
                    <Input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search company, contact or email..."
                        aria-label="Search clients"
                    />
                    <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                        <option value="">All statuses</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="archived">Archived</option>
                    </Select>
                </div>

                {error ? (
                    <div className="border-b border-slate-800 p-4">
                        <DataError message={error} onRetry={() => void loadClients()} />
                    </div>
                ) : null}

                {clients.length === 0 ? (
                    <EmptyState
                        title="No clients match this view"
                        description="Try changing the search or status filter."
                    />
                ) : (
                    <Table>
                        <TableHead>
                            <tr>
                                <TableHeaderCell>Client</TableHeaderCell>
                                <TableHeaderCell>Status</TableHeaderCell>
                                <TableHeaderCell>Active work</TableHeaderCell>
                                <TableHeaderCell>Contacts</TableHeaderCell>
                                <TableHeaderCell>Projects</TableHeaderCell>
                                <TableHeaderCell>Primary email</TableHeaderCell>
                            </tr>
                        </TableHead>
                        <TableBody>
                            {clients.map((client) => (
                                <TableRow key={client.id}>
                                    <TableCell>
                                        <button
                                            type="button"
                                            onClick={() => setSelectedClientId(client.id)}
                                            className="text-left font-medium text-slate-100 transition hover:text-cyan-300"
                                        >
                                            {client.company || client.name}
                                        </button>
                                        {client.company && client.name ? (
                                            <div className="mt-1 text-xs text-slate-500">
                                                {client.name}
                                            </div>
                                        ) : null}
                                    </TableCell>
                                    <TableCell>
                                        <Badge className={statusClasses(client.status)}>
                                            {client.status}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <div className="font-medium tabular-nums text-slate-200">
                                            {client.active_project_count}
                                        </div>
                                        <div className="mt-1 text-xs text-slate-600">active projects</div>
                                    </TableCell>
                                    <TableCell className="tabular-nums text-slate-400">
                                        {client.contact_count}
                                    </TableCell>
                                    <TableCell className="tabular-nums text-slate-400">
                                        {client.project_count}
                                    </TableCell>
                                    <TableCell className="text-slate-400">{client.email}</TableCell>
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

            {selectedClientId ? (
                <RecordDrawer
                    fullPageHref={`/admin/clients/${selectedClientId}`}
                    onClose={() => {
                        setSelectedClientId(null);
                        void loadClients();
                    }}
                >
                    <ClientWorkspace clientId={selectedClientId} />
                </RecordDrawer>
            ) : null}
        </div>
    );
}

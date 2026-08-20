"use client";

import {
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Pagination,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface ProjectTimeEntry {
    id: number;
    date: string;
    duration_hours: string;
    description: string;
    billable: boolean;
    entry_type: string;
    task_id: number | null;
    task_title: string | null;
    ticket_id: number | null;
    ticket_reference: string | null;
    ticket_subject: string | null;
    user_name: string | null;
}

interface ProjectTimePage {
    items: ProjectTimeEntry[];
    total: number;
    page: number;
    page_size: number;
    tracked_hours: string;
    billable_hours: string;
}

const PAGE_SIZE = 20;

function hours(value: string | number) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

export function ProjectTimeWorkspace({ projectId }: { projectId: number }) {
    const [data, setData] = useState<ProjectTimePage | null>(null);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const query = new URLSearchParams({
                project_id: String(projectId),
                page: String(page),
                page_size: String(PAGE_SIZE),
            });
            setData(
                (await fetchAPI(AdminAPI.timeEntries.list(query.toString()))) as ProjectTimePage,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load project time.",
            );
        } finally {
            setLoading(false);
        }
    }, [page, projectId]);

    useEffect(() => {
        void load();
    }, [load]);

    if (loading && !data) return <DataLoading label="Loading project time..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    const tracked = Number(data?.tracked_hours ?? 0);
    const billable = Number(data?.billable_hours ?? 0);

    return (
        <section className="space-y-5">
            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">Project time</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Review delivery effort without leaving the project workspace.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <ButtonLink
                        href={`/admin/time-tracking?project_id=${projectId}&mode=timer#record-time`}
                    >
                        Start timer
                    </ButtonLink>
                    <ButtonLink
                        href={`/admin/time-tracking?project_id=${projectId}&mode=manual#record-time`}
                        variant="outline"
                    >
                        Manual entry
                    </ButtonLink>
                </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Tracked</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{hours(tracked)}</div>
                    <div className="mt-1 text-xs text-slate-600">{data?.total ?? 0} entries</div>
                </Card>
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Billable</div>
                    <div className="mt-2 text-2xl font-semibold text-white">{hours(billable)}</div>
                    <div className="mt-1 text-xs text-slate-600">Client-billable delivery</div>
                </Card>
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Non-billable</div>
                    <div className="mt-2 text-2xl font-semibold text-white">
                        {hours(Math.max(0, tracked - billable))}
                    </div>
                    <div className="mt-1 text-xs text-slate-600">Internal/project overhead</div>
                </Card>
            </div>

            {!data || data.items.length === 0 ? (
                <EmptyState
                    title="No time recorded for this project"
                    description="Stopped timers and manual entries linked to this project will appear here."
                />
            ) : (
                <Card className="overflow-hidden">
                    <div className="border-b border-slate-800 px-5 py-4">
                        <h3 className="text-sm font-semibold text-white">Time entries</h3>
                    </div>
                    <div className="divide-y divide-slate-800">
                        {data.items.map((entry) => (
                            <div
                                key={entry.id}
                                className="grid gap-3 px-5 py-4 md:grid-cols-[7rem_minmax(0,1fr)_9rem_7rem] md:items-center"
                            >
                                <div className="text-xs text-slate-500">{formatDate(entry.date)}</div>
                                <div className="min-w-0">
                                    <div className="truncate text-sm font-medium text-slate-200">
                                        {entry.description || entry.task_title || entry.ticket_subject || "Project work"}
                                    </div>
                                    <div className="mt-1 flex flex-wrap gap-x-2 text-xs text-slate-600">
                                        <span>{entry.user_name || "Unknown staff"}</span>
                                        <span className="capitalize">· {entry.entry_type}</span>
                                        {entry.task_id ? (
                                            <Link
                                                href={`/admin/tasks/${entry.task_id}`}
                                                className="hover:text-adb-cyan-300"
                                            >
                                                · {entry.task_title || "Task"}
                                            </Link>
                                        ) : null}
                                        {entry.ticket_id ? (
                                            <Link
                                                href={`/admin/tickets/${entry.ticket_id}`}
                                                className="hover:text-adb-cyan-300"
                                            >
                                                · {entry.ticket_reference || "Ticket"}
                                            </Link>
                                        ) : null}
                                    </div>
                                </div>
                                <div className="text-sm text-slate-500">
                                    {entry.billable ? "Billable" : "Non-billable"}
                                </div>
                                <div className="text-right font-semibold tabular-nums text-slate-200">
                                    {hours(entry.duration_hours)}
                                </div>
                            </div>
                        ))}
                    </div>
                    <Pagination
                        page={data.page}
                        pageSize={data.page_size}
                        totalItems={data.total}
                        onPageChange={setPage}
                        disabled={loading}
                    />
                </Card>
            )}
        </section>
    );
}

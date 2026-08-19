"use client";

import { Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type Period = "7d" | "30d" | "this_month" | "last_month" | "this_year";

interface ClientSummary {
    client_id: number;
    client_name: string;
    tracked_hours: string;
    billable_hours: string;
    non_billable_hours: string;
    entry_count: number;
    project_count: number;
}

interface DailySummary {
    date: string;
    tracked_hours: string;
    billable_hours: string;
}

interface TimeReport {
    period: string;
    date_from: string;
    date_to: string;
    tracked_hours: string;
    billable_hours: string;
    non_billable_hours: string;
    client_hours: string;
    internal_hours: string;
    entry_count: number;
    clients: ClientSummary[];
    daily: DailySummary[];
}

const periods: { value: Period; label: string }[] = [
    { value: "7d", label: "7 days" },
    { value: "30d", label: "30 days" },
    { value: "this_month", label: "This month" },
    { value: "last_month", label: "Last month" },
    { value: "this_year", label: "This year" },
];

function hours(value: string | number) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

function dateLabel(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

export function TimeReportOverview() {
    const [period, setPeriod] = useState<Period>("this_month");
    const [report, setReport] = useState<TimeReport | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const params = new URLSearchParams({ period });
            setReport(
                (await fetchAPI(AdminAPI.timeEntries.report(params.toString()))) as TimeReport,
            );
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load time reporting.");
        } finally {
            setLoading(false);
        }
    }, [period]);

    useEffect(() => {
        void load();
    }, [load]);

    const maxDailyHours = useMemo(
        () => Math.max(0, ...(report?.daily.map((day) => Number(day.tracked_hours)) ?? [])),
        [report],
    );

    return (
        <section className="space-y-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">Time overview</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        See where delivery time is going across the business and by client.
                    </p>
                </div>
                <div className="flex flex-wrap gap-1 rounded-lg border border-slate-800 bg-slate-900 p-1">
                    {periods.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            onClick={() => setPeriod(option.value)}
                            className={`rounded-md px-3 py-2 text-xs font-medium transition ${
                                period === option.value
                                    ? "bg-slate-700 text-white"
                                    : "text-slate-400 hover:text-slate-200"
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>

            {loading && !report ? <DataLoading label="Loading time overview..." /> : null}
            {error ? <DataError message={error} onRetry={() => void load()} /> : null}

            {report ? (
                <>
                    <div className="text-xs text-slate-600">
                        {dateLabel(report.date_from)} – {dateLabel(report.date_to)} · {report.entry_count} entries
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-5">
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Tracked</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {hours(report.tracked_hours)}
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Billable</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {hours(report.billable_hours)}
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Non-billable</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {hours(report.non_billable_hours)}
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Client work</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {hours(report.client_hours)}
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Internal</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {hours(report.internal_hours)}
                            </div>
                        </Card>
                    </div>

                    <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.4fr)_minmax(22rem,0.6fr)]">
                        <Card className="overflow-hidden">
                            <div className="border-b border-slate-800 px-5 py-4">
                                <h3 className="text-sm font-semibold text-white">Client breakdown</h3>
                                <p className="mt-1 text-xs text-slate-500">
                                    Monthly and rolling-period workload across every client in your scope.
                                </p>
                            </div>
                            {report.clients.length ? (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-sm">
                                        <thead className="border-b border-slate-800 bg-slate-950/40 text-xs uppercase tracking-wide text-slate-600">
                                            <tr>
                                                <th className="px-5 py-3 font-medium">Client</th>
                                                <th className="px-4 py-3 font-medium">Projects</th>
                                                <th className="px-4 py-3 text-right font-medium">Tracked</th>
                                                <th className="px-4 py-3 text-right font-medium">Billable</th>
                                                <th className="px-5 py-3 text-right font-medium">Non-billable</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800">
                                            {report.clients.map((client) => (
                                                <tr key={client.client_id} className="hover:bg-slate-900/60">
                                                    <td className="px-5 py-4">
                                                        <Link
                                                            href={`/admin/clients/${client.client_id}`}
                                                            className="font-medium text-slate-200 hover:text-adb-cyan-300"
                                                        >
                                                            {client.client_name}
                                                        </Link>
                                                        <div className="mt-1 text-xs text-slate-600">
                                                            {client.entry_count} entries
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-4 text-slate-400">{client.project_count}</td>
                                                    <td className="px-4 py-4 text-right font-medium tabular-nums text-slate-200">
                                                        {hours(client.tracked_hours)}
                                                    </td>
                                                    <td className="px-4 py-4 text-right tabular-nums text-slate-400">
                                                        {hours(client.billable_hours)}
                                                    </td>
                                                    <td className="px-5 py-4 text-right tabular-nums text-slate-500">
                                                        {hours(client.non_billable_hours)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <EmptyState
                                    title="No client time in this period"
                                    description="Client work recorded in the selected period will appear here."
                                />
                            )}
                        </Card>

                        <Card className="p-5">
                            <h3 className="text-sm font-semibold text-white">Daily activity</h3>
                            <p className="mt-1 text-xs text-slate-500">Tracked hours across the selected period.</p>
                            {report.daily.length ? (
                                <div className="mt-5 space-y-3">
                                    {report.daily.slice(-14).map((day) => {
                                        const tracked = Number(day.tracked_hours);
                                        const width = maxDailyHours ? (tracked / maxDailyHours) * 100 : 0;
                                        return (
                                            <div key={day.date} className="grid grid-cols-[4.5rem_1fr_3rem] items-center gap-3 text-xs">
                                                <span className="text-slate-500">
                                                    {new Intl.DateTimeFormat("en-GB", {
                                                        day: "2-digit",
                                                        month: "short",
                                                    }).format(new Date(`${day.date}T00:00:00`))}
                                                </span>
                                                <div className="h-2 overflow-hidden rounded-full bg-slate-800">
                                                    <div
                                                        className="h-full rounded-full bg-adb-cyan-500/70"
                                                        style={{ width: `${Math.max(2, width)}%` }}
                                                    />
                                                </div>
                                                <span className="text-right tabular-nums text-slate-400">
                                                    {hours(tracked)}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="mt-5 text-sm text-slate-600">No time recorded in this period.</div>
                            )}
                        </Card>
                    </div>
                </>
            ) : null}
        </section>
    );
}

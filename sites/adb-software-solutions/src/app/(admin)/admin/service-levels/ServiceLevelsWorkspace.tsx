"use client";

import { Button, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface TicketSLAItem {
    ticket_id: number;
    reference: string;
    subject: string;
    status: string;
    priority: string;
    queue_id: number;
    queue_name: string;
    client_id: number | null;
    client_name: string | null;
    assigned_to_name: string | null;
    first_response_due_at: string | null;
    first_response_at: string | null;
    first_response_status: string;
    resolution_due_at: string | null;
    resolved_at: string | null;
    resolution_status: string;
    next_due_at: string | null;
    overall_status: string;
    severity: string;
    href: string;
}

interface TicketSLAResponse {
    items: TicketSLAItem[];
    healthy_count: number;
    warning_count: number;
    breached_count: number;
    waiting_customer_count: number;
}

function formatDate(value: string | null) {
    if (!value) return "Not applicable";
    return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
    );
}

function statusClasses(status: string) {
    if (status === "breached") return "border-red-900/70 bg-red-950/30 text-red-300";
    if (status === "warning") return "border-amber-900/70 bg-amber-950/30 text-amber-300";
    if (status === "waiting_customer") return "border-indigo-900/70 bg-indigo-950/30 text-indigo-300";
    return "border-emerald-900/60 bg-emerald-950/20 text-emerald-300";
}

export function ServiceLevelsWorkspace() {
    const [data, setData] = useState<TicketSLAResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [attentionOnly, setAttentionOnly] = useState(true);
    const [mineOnly, setMineOnly] = useState(false);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const query = new URLSearchParams({
                attention_only: String(attentionOnly),
                assigned_to_me: String(mineOnly),
            });
            setData(
                (await fetchAPI(`${API_URL}/api/admin/ticket-sla?${query.toString()}`)) as TicketSLAResponse,
            );
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load Ticket SLAs.");
        } finally {
            setLoading(false);
        }
    }, [attentionOnly, mineOnly]);

    useEffect(() => {
        void load();
    }, [load]);

    async function recalculate(ticketId: number) {
        await fetchAPI(`${API_URL}/api/admin/tickets/${ticketId}/sla/recalculate`, {
            method: "POST",
        });
        await load();
    }

    if (loading && !data) return <DataLoading label="Loading Ticket service levels..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <div className="space-y-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-adb-cyan-400">
                        Support · Escalation
                    </p>
                    <h1 className="mt-2 text-2xl font-semibold text-white">Service levels</h1>
                    <p className="mt-1 max-w-3xl text-sm text-slate-400">
                        Queue-owned first-response and resolution deadlines. Waiting-for-customer Tickets suppress
                        escalation while their recorded deadlines remain unchanged for auditability.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button
                        type="button"
                        onClick={() => setAttentionOnly((value) => !value)}
                        className={`rounded-lg border px-3 py-2 text-sm ${
                            attentionOnly
                                ? "border-adb-cyan-700 bg-adb-cyan-950/30 text-adb-cyan-200"
                                : "border-slate-700 text-slate-400"
                        }`}
                    >
                        Attention only
                    </button>
                    <button
                        type="button"
                        onClick={() => setMineOnly((value) => !value)}
                        className={`rounded-lg border px-3 py-2 text-sm ${
                            mineOnly
                                ? "border-adb-cyan-700 bg-adb-cyan-950/30 text-adb-cyan-200"
                                : "border-slate-700 text-slate-400"
                        }`}
                    >
                        Assigned to me
                    </button>
                    <Button variant="outline" onClick={() => void load()}>
                        Refresh
                    </Button>
                </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                    ["Healthy", data?.healthy_count ?? 0, "text-emerald-300"],
                    ["Warning", data?.warning_count ?? 0, "text-amber-300"],
                    ["Breached", data?.breached_count ?? 0, "text-red-300"],
                    ["Waiting customer", data?.waiting_customer_count ?? 0, "text-indigo-300"],
                ].map(([label, value, classes]) => (
                    <Card key={String(label)} className="p-4">
                        <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                        <p className={`mt-2 text-3xl font-semibold ${classes}`}>{value}</p>
                    </Card>
                ))}
            </div>

            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                        <thead className="bg-slate-900/70 text-xs uppercase tracking-wide text-slate-500">
                            <tr>
                                <th className="px-4 py-3">Ticket</th>
                                <th className="px-4 py-3">Queue / owner</th>
                                <th className="px-4 py-3">First response</th>
                                <th className="px-4 py-3">Resolution</th>
                                <th className="px-4 py-3">State</th>
                                <th className="px-4 py-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {data?.items.map((item) => (
                                <tr key={item.ticket_id} className="align-top">
                                    <td className="px-4 py-4">
                                        <Link href={item.href} className="font-semibold text-adb-cyan-300 hover:text-adb-cyan-200">
                                            {item.reference}
                                        </Link>
                                        <p className="mt-1 max-w-sm text-slate-300">{item.subject}</p>
                                        <p className="mt-1 text-xs text-slate-600">
                                            {item.priority} · {item.status}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4 text-slate-400">
                                        <p>{item.queue_name}</p>
                                        <p className="mt-1 text-xs text-slate-600">
                                            {item.assigned_to_name || "Unassigned"} · {item.client_name || "No Client"}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <p className="text-slate-300">{formatDate(item.first_response_due_at)}</p>
                                        <p className="mt-1 text-xs text-slate-600">
                                            {item.first_response_status.replaceAll("_", " ")}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <p className="text-slate-300">{formatDate(item.resolution_due_at)}</p>
                                        <p className="mt-1 text-xs text-slate-600">
                                            {item.resolution_status.replaceAll("_", " ")}
                                        </p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClasses(item.overall_status)}`}>
                                            {item.overall_status.replaceAll("_", " ")}
                                        </span>
                                    </td>
                                    <td className="px-4 py-4 text-right">
                                        <Button variant="ghost" onClick={() => void recalculate(item.ticket_id)}>
                                            Recalculate
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>

            {!loading && data?.items.length === 0 ? (
                <EmptyState
                    title={attentionOnly ? "No SLA attention required" : "No Tickets in scope"}
                    description="Change the filters or configure SLA targets on Ticket Queues to populate this workspace."
                />
            ) : null}
        </div>
    );
}

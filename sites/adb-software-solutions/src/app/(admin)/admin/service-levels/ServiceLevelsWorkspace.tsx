"use client";

import { Button, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
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

interface TicketQueue {
    id: number;
    name: string;
    key: string;
    brand_name: string | null;
    enabled: boolean;
}

interface QueuePolicy {
    queue_id: number;
    queue_name: string;
    first_response_sla_minutes: number | null;
    resolution_sla_minutes: number | null;
}

interface QueuePolicyDraft extends QueuePolicy {
    firstResponseDraft: string;
    resolutionDraft: string;
    saving: boolean;
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

function parseTarget(value: string) {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined;
}

export function ServiceLevelsWorkspace() {
    const { hasPermission } = useAuth();
    const [data, setData] = useState<TicketSLAResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [attentionOnly, setAttentionOnly] = useState(true);
    const [mineOnly, setMineOnly] = useState(false);
    const [queuePolicies, setQueuePolicies] = useState<QueuePolicyDraft[]>([]);

    const canViewQueues = hasPermission("ticketing.view_ticketqueue");
    const canConfigureQueues = hasPermission("ticketing.configure_ticket_queues");

    const loadQueuePolicies = useCallback(async () => {
        if (!canViewQueues) {
            setQueuePolicies([]);
            return;
        }
        try {
            const queues = (await fetchAPI(`${API_URL}/api/admin/ticket-queues`)) as TicketQueue[];
            const enabledQueues = queues.filter((queue) => queue.enabled);
            const policyResults = await Promise.allSettled(
                enabledQueues.map(
                    (queue) =>
                        fetchAPI(`${API_URL}/api/admin/ticket-queues/${queue.id}/sla`) as Promise<QueuePolicy>,
                ),
            );
            setQueuePolicies(
                policyResults.flatMap((result) => {
                    if (result.status !== "fulfilled") return [];
                    const policy = result.value;
                    return [
                        {
                            ...policy,
                            firstResponseDraft: policy.first_response_sla_minutes?.toString() ?? "",
                            resolutionDraft: policy.resolution_sla_minutes?.toString() ?? "",
                            saving: false,
                        },
                    ];
                }),
            );
        } catch {
            setQueuePolicies([]);
        }
    }, [canViewQueues]);

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

    useEffect(() => {
        void loadQueuePolicies();
    }, [loadQueuePolicies]);

    async function recalculate(ticketId: number) {
        await fetchAPI(`${API_URL}/api/admin/tickets/${ticketId}/sla/recalculate`, {
            method: "POST",
        });
        await load();
    }

    function updateQueueDraft(queueId: number, field: "firstResponseDraft" | "resolutionDraft", value: string) {
        setQueuePolicies((current) =>
            current.map((policy) => (policy.queue_id === queueId ? { ...policy, [field]: value } : policy)),
        );
    }

    async function saveQueuePolicy(policy: QueuePolicyDraft) {
        const firstResponse = parseTarget(policy.firstResponseDraft);
        const resolution = parseTarget(policy.resolutionDraft);
        if (firstResponse === undefined || resolution === undefined) {
            setError("SLA targets must be blank or a positive whole number of minutes.");
            return;
        }
        try {
            setError(null);
            setQueuePolicies((current) =>
                current.map((item) => (item.queue_id === policy.queue_id ? { ...item, saving: true } : item)),
            );
            await fetchAPI(`${API_URL}/api/admin/ticket-queues/${policy.queue_id}/sla`, {
                method: "PUT",
                body: JSON.stringify({
                    first_response_sla_minutes: firstResponse,
                    resolution_sla_minutes: resolution,
                }),
            });
            await Promise.all([loadQueuePolicies(), load()]);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to save Queue SLA policy.");
        } finally {
            setQueuePolicies((current) =>
                current.map((item) => (item.queue_id === policy.queue_id ? { ...item, saving: false } : item)),
            );
        }
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

            {queuePolicies.length > 0 ? (
                <Card>
                    <div className="border-b border-slate-800 px-5 py-4">
                        <h2 className="font-semibold text-white">Queue SLA policies</h2>
                        <p className="mt-1 text-xs text-slate-500">
                            Targets are stored on each Ticket Queue. Blank disables that target for newly calculated Tickets.
                        </p>
                    </div>
                    <div className="divide-y divide-slate-800">
                        {queuePolicies.map((policy) => (
                            <div key={policy.queue_id} className="grid gap-3 px-5 py-4 lg:grid-cols-[1fr_12rem_12rem_auto] lg:items-end">
                                <div>
                                    <p className="font-medium text-slate-200">{policy.queue_name}</p>
                                    <p className="mt-1 text-xs text-slate-600">Queue #{policy.queue_id}</p>
                                </div>
                                <label className="space-y-1 text-xs text-slate-500">
                                    <span>First response · minutes</span>
                                    <input
                                        inputMode="numeric"
                                        value={policy.firstResponseDraft}
                                        disabled={!canConfigureQueues}
                                        onChange={(event) => updateQueueDraft(policy.queue_id, "firstResponseDraft", event.target.value)}
                                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 disabled:opacity-60"
                                        placeholder="Disabled"
                                    />
                                </label>
                                <label className="space-y-1 text-xs text-slate-500">
                                    <span>Resolution · minutes</span>
                                    <input
                                        inputMode="numeric"
                                        value={policy.resolutionDraft}
                                        disabled={!canConfigureQueues}
                                        onChange={(event) => updateQueueDraft(policy.queue_id, "resolutionDraft", event.target.value)}
                                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 disabled:opacity-60"
                                        placeholder="Disabled"
                                    />
                                </label>
                                {canConfigureQueues ? (
                                    <Button
                                        variant="outline"
                                        disabled={policy.saving}
                                        onClick={() => void saveQueuePolicy(policy)}
                                    >
                                        {policy.saving ? "Saving..." : "Save policy"}
                                    </Button>
                                ) : (
                                    <span className="pb-2 text-xs text-slate-600">Read only</span>
                                )}
                            </div>
                        ))}
                    </div>
                </Card>
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

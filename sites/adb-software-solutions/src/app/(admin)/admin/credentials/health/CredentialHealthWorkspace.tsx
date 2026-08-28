"use client";

import { Badge, Button, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface CredentialHealthItem {
    credential_id: number;
    name: string;
    status: string;
    client_id: number | null;
    client_name: string | null;
    expires_at: string | null;
    expires_in_days: number | null;
    last_rotated_at: string | null;
    rotation_interval_days: number | null;
    rotation_due_at: string | null;
    rotation_due_in_days: number | null;
    health_status: string;
    health_severity: string;
    href: string;
}

interface CredentialHealthResponse {
    items: CredentialHealthItem[];
    healthy_count: number;
    warning_count: number;
    critical_count: number;
}

function statusClasses(severity: string) {
    if (severity === "critical") return "border-red-900/70 bg-red-950/30 text-red-300";
    if (severity === "warning") return "border-amber-900/70 bg-amber-950/30 text-amber-300";
    return "border-emerald-900/60 bg-emerald-950/20 text-emerald-300";
}

function formatDate(value: string | null) {
    if (!value) return "Not configured";
    return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(
        new Date(value),
    );
}

export function CredentialHealthWorkspace() {
    const [data, setData] = useState<CredentialHealthResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            setData(
                (await fetchAPI(`${API_URL}/api/admin/credential-health`)) as CredentialHealthResponse,
            );
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load Credential health.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void load();
    }, [load]);

    async function updateLifecycle(
        credentialId: number,
        payload: { rotation_interval_days?: number; clear_rotation_interval?: boolean; mark_rotated?: boolean },
    ) {
        await fetchAPI(`${API_URL}/api/admin/credentials/${credentialId}/lifecycle`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        await load();
    }

    if (loading && !data) return <DataLoading label="Loading Credential health..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <div className="space-y-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-adb-cyan-400">
                        Credential Vault · Lifecycle
                    </p>
                    <h1 className="mt-2 text-2xl font-semibold text-white">Credential health</h1>
                    <p className="mt-1 max-w-3xl text-sm text-slate-400">
                        Expiry and rotation posture derived exclusively from Vault metadata. Secret values are never
                        decrypted to calculate this health view.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Link href="/admin/credentials" className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-900">
                        Back to Vault
                    </Link>
                    <Button variant="outline" onClick={() => void load()}>
                        Refresh
                    </Button>
                </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
                {[
                    ["Healthy", data?.healthy_count ?? 0, "text-emerald-300"],
                    ["Warning", data?.warning_count ?? 0, "text-amber-300"],
                    ["Critical", data?.critical_count ?? 0, "text-red-300"],
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

            <div className="grid gap-4 xl:grid-cols-2">
                {data?.items.map((item) => (
                    <Card key={item.credential_id} className="p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="min-w-0">
                                <Link href={item.href} className="font-semibold text-white hover:text-adb-cyan-300">
                                    {item.name}
                                </Link>
                                <p className="mt-1 text-xs text-slate-500">
                                    {item.client_name || "ADB Internal"} · {item.status}
                                </p>
                            </div>
                            <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClasses(item.health_severity)}`}>
                                {item.health_status.replaceAll("_", " ")}
                            </span>
                        </div>

                        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                            <div>
                                <dt className="text-xs text-slate-500">Expires</dt>
                                <dd className="mt-1 text-slate-300">{formatDate(item.expires_at)}</dd>
                                {item.expires_in_days !== null ? (
                                    <dd className="mt-1 text-xs text-slate-600">{item.expires_in_days} day(s)</dd>
                                ) : null}
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Last rotation</dt>
                                <dd className="mt-1 text-slate-300">{formatDate(item.last_rotated_at)}</dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Rotation interval</dt>
                                <dd className="mt-1 text-slate-300">
                                    {item.rotation_interval_days ? `${item.rotation_interval_days} days` : "Not configured"}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-500">Next rotation</dt>
                                <dd className="mt-1 text-slate-300">{formatDate(item.rotation_due_at)}</dd>
                            </div>
                        </dl>

                        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-slate-800 pt-4">
                            {[30, 60, 90, 180, 365].map((days) => (
                                <button
                                    key={days}
                                    type="button"
                                    onClick={() => void updateLifecycle(item.credential_id, { rotation_interval_days: days })}
                                    className={`rounded-md border px-2.5 py-1.5 text-xs transition ${
                                        item.rotation_interval_days === days
                                            ? "border-adb-cyan-700 bg-adb-cyan-950/30 text-adb-cyan-200"
                                            : "border-slate-800 text-slate-500 hover:text-slate-300"
                                    }`}
                                >
                                    {days}d
                                </button>
                            ))}
                            {item.rotation_interval_days ? (
                                <Button
                                    variant="ghost"
                                    onClick={() => void updateLifecycle(item.credential_id, { clear_rotation_interval: true })}
                                >
                                    Clear interval
                                </Button>
                            ) : null}
                            <Button
                                variant="outline"
                                onClick={() => void updateLifecycle(item.credential_id, { mark_rotated: true })}
                            >
                                Mark rotated
                            </Button>
                        </div>
                    </Card>
                ))}
            </div>

            {!loading && data?.items.length === 0 ? (
                <EmptyState
                    title="No Credentials in scope"
                    description="Active Credentials will appear here when your role can view them."
                />
            ) : null}

            <div className="flex items-center gap-2 text-xs text-slate-600">
                <Badge>Metadata only</Badge>
                <span>Changing lifecycle metadata never reveals, copies or downloads Vault secrets.</span>
            </div>
        </div>
    );
}

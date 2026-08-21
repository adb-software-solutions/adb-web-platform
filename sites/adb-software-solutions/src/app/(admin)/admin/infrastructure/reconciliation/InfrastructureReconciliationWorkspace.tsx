"use client";

import { RecordDrawer } from "@/components/admin/RecordDrawer";
import {
    Button,
    Card,
    DataError,
    DataLoading,
    Input,
    PageHeader,
    Pagination,
    Select,
} from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { useCallback, useEffect, useMemo, useState } from "react";

interface ReconciliationItem {
    legacy_type: string;
    legacy_type_label: string;
    legacy_id: number;
    name: string;
    resource_id: number | null;
    ownership_type: string | null;
    client_id: number | null;
    client_name: string | null;
    lifecycle_status: string | null;
    environment: string | null;
    criticality: string | null;
}

interface ReconciliationPage {
    items: ReconciliationItem[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
    total_legacy: number;
    linked: number;
    unlinked: number;
}

interface ClientOption {
    id: number;
    name: string;
    status: string;
}

interface ReconciliationOptions {
    clients: ClientOption[];
    legacy_types: string[];
    lifecycle_statuses: string[];
    environments: string[];
    criticalities: string[];
}

interface ReconcileForm {
    ownership_type: "internal" | "client";
    client_id: string;
    name: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
}

const PAGE_SIZE = 25;

const TYPE_LABELS: Record<string, string> = {
    server: "Servers",
    database: "Databases",
    website: "Websites",
    domain: "Domains",
    ssl_certificate: "SSL certificates",
    licence: "Licences",
    application: "Applications",
    mobile_app: "Mobile apps",
    api: "APIs",
    bot: "Bots",
    email_system: "Email systems",
};

const VALUE_LABELS: Record<string, string> = {
    not_applicable: "Not applicable",
    production: "Production",
    staging: "Staging",
    development: "Development",
    testing: "Testing",
    shared: "Shared",
    planned: "Planned",
    active: "Active",
    maintenance: "Maintenance",
    deprecated: "Deprecated",
    retired: "Retired",
    archived: "Archived",
    low: "Low",
    normal: "Normal",
    high: "High",
    critical: "Critical",
};

function labelFor(value: string): string {
    return VALUE_LABELS[value] ?? TYPE_LABELS[value] ?? value.replaceAll("_", " ");
}

function initialForm(item: ReconciliationItem): ReconcileForm {
    return {
        ownership_type: "internal",
        client_id: "",
        name: item.name,
        lifecycle_status: "active",
        environment: "not_applicable",
        criticality: "normal",
    };
}

export function InfrastructureReconciliationWorkspace() {
    const [data, setData] = useState<ReconciliationPage | null>(null);
    const [options, setOptions] = useState<ReconciliationOptions | null>(null);
    const [page, setPage] = useState(1);
    const [status, setStatus] = useState("unlinked");
    const [legacyType, setLegacyType] = useState("all");
    const [selected, setSelected] = useState<ReconciliationItem | null>(null);
    const [form, setForm] = useState<ReconcileForm | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [saveError, setSaveError] = useState<string | null>(null);

    const collectionUrl = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
            status,
        });
        if (legacyType !== "all") params.set("legacy_type", legacyType);
        return `${API_URL}/api/admin/infrastructure/reconciliation?${params.toString()}`;
    }, [legacyType, page, status]);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [pageData, optionData] = await Promise.all([
                fetchAPI(collectionUrl) as Promise<ReconciliationPage>,
                fetchAPI(
                    `${API_URL}/api/admin/infrastructure/reconciliation/options`,
                ) as Promise<ReconciliationOptions>,
            ]);
            setData(pageData);
            setOptions(optionData);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load infrastructure reconciliation.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [collectionUrl]);

    useEffect(() => {
        void load();
    }, [load]);

    function openReconciliation(item: ReconciliationItem) {
        if (item.resource_id) return;
        setSelected(item);
        setForm(initialForm(item));
        setSaveError(null);
    }

    function closeReconciliation() {
        if (isSaving) return;
        setSelected(null);
        setForm(null);
        setSaveError(null);
    }

    async function submitReconciliation() {
        if (!selected || !form) return;
        if (form.ownership_type === "client" && !form.client_id) {
            setSaveError("Choose the client that owns this resource.");
            return;
        }

        try {
            setIsSaving(true);
            setSaveError(null);
            await fetchAPI(
                `${API_URL}/api/admin/infrastructure/reconciliation/${selected.legacy_type}/${selected.legacy_id}`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        ownership_type: form.ownership_type,
                        client_id:
                            form.ownership_type === "client"
                                ? Number(form.client_id)
                                : null,
                        name: form.name.trim() || null,
                        lifecycle_status: form.lifecycle_status,
                        environment: form.environment,
                        criticality: form.criticality,
                    }),
                },
            );
            setSelected(null);
            setForm(null);
            await load();
        } catch (saveFailure) {
            setSaveError(
                saveFailure instanceof Error
                    ? saveFailure.message
                    : "Unable to reconcile this infrastructure record.",
            );
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading && !data) {
        return <DataLoading label="Loading infrastructure reconciliation..." />;
    }
    if (error || !data || !options) {
        return (
            <DataError
                message={error || "Infrastructure reconciliation is unavailable."}
                onRetry={() => void load()}
            />
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                eyebrow="Infrastructure migration"
                title="Reconcile existing infrastructure"
                description="Assign an explicit Internal or Client ownership context to each existing technical record before it joins the structured resource graph. Nothing is guessed automatically."
            />

            <div className="grid gap-4 sm:grid-cols-3">
                <Card className="p-5">
                    <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">
                        Existing records
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-white tabular-nums">
                        {data.total_legacy.toLocaleString("en-GB")}
                    </p>
                </Card>
                <Card className="p-5">
                    <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">
                        Reconciled
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-emerald-300 tabular-nums">
                        {data.linked.toLocaleString("en-GB")}
                    </p>
                </Card>
                <Card className="p-5">
                    <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">
                        Still to review
                    </p>
                    <p className="mt-2 text-3xl font-semibold text-amber-300 tabular-nums">
                        {data.unlinked.toLocaleString("en-GB")}
                    </p>
                </Card>
            </div>

            <Card className="overflow-hidden">
                <div className="flex flex-col gap-3 border-b border-slate-800 p-4 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-white">
                            Existing inventory
                        </h2>
                        <p className="mt-1 text-xs text-slate-500">
                            Review records individually so Client ownership is never inferred incorrectly.
                        </p>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2 md:w-auto md:min-w-[26rem]">
                        <Select
                            aria-label="Reconciliation status"
                            value={status}
                            onChange={(event) => {
                                setStatus(event.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="unlinked">Needs reconciliation</option>
                            <option value="linked">Reconciled</option>
                            <option value="all">All existing records</option>
                        </Select>
                        <Select
                            aria-label="Infrastructure type"
                            value={legacyType}
                            onChange={(event) => {
                                setLegacyType(event.target.value);
                                setPage(1);
                            }}
                        >
                            <option value="all">All types</option>
                            {options.legacy_types.map((type) => (
                                <option key={type} value={type}>
                                    {TYPE_LABELS[type] ?? labelFor(type)}
                                </option>
                            ))}
                        </Select>
                    </div>
                </div>

                {data.items.length === 0 ? (
                    <div className="px-5 py-14 text-center">
                        <p className="text-sm font-medium text-slate-300">
                            {status === "unlinked"
                                ? "Everything in this view has been reconciled."
                                : "No infrastructure records match this view."}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                            Change the status or type filter to inspect another part of the inventory.
                        </p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-slate-800 text-sm">
                            <thead className="bg-slate-950/60 text-left text-[11px] font-semibold tracking-wide text-slate-500 uppercase">
                                <tr>
                                    <th className="px-4 py-3">Record</th>
                                    <th className="px-4 py-3">Type</th>
                                    <th className="px-4 py-3">Ownership</th>
                                    <th className="px-4 py-3">Environment</th>
                                    <th className="px-4 py-3">State</th>
                                    <th className="px-4 py-3 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/80">
                                {data.items.map((item) => (
                                    <tr
                                        key={`${item.legacy_type}-${item.legacy_id}`}
                                        className="bg-slate-900/20"
                                    >
                                        <td className="px-4 py-3">
                                            <div className="font-medium text-slate-100">
                                                {item.name}
                                            </div>
                                            <div className="mt-0.5 text-xs text-slate-600">
                                                Legacy #{item.legacy_id}
                                                {item.resource_id
                                                    ? ` · Resource #${item.resource_id}`
                                                    : ""}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {item.legacy_type_label}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {item.resource_id
                                                ? item.client_name || "ADB Internal"
                                                : "Not assigned"}
                                        </td>
                                        <td className="px-4 py-3 text-slate-400">
                                            {item.environment
                                                ? labelFor(item.environment)
                                                : "—"}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span
                                                className={
                                                    item.resource_id
                                                        ? "rounded-full bg-emerald-950/60 px-2 py-1 text-xs font-medium text-emerald-300"
                                                        : "rounded-full bg-amber-950/60 px-2 py-1 text-xs font-medium text-amber-300"
                                                }
                                            >
                                                {item.resource_id
                                                    ? "Reconciled"
                                                    : "Needs review"}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            {item.resource_id ? (
                                                <span className="text-xs text-slate-600">
                                                    Complete
                                                </span>
                                            ) : (
                                                <Button
                                                    type="button"
                                                    variant="secondary"
                                                    size="sm"
                                                    onClick={() => openReconciliation(item)}
                                                >
                                                    Reconcile
                                                </Button>
                                            )}
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

            {selected && form ? (
                <RecordDrawer onClose={closeReconciliation}>
                    <div className="space-y-6">
                        <div>
                            <p className="text-[10px] font-bold tracking-[0.18em] text-adb-cyan-500 uppercase">
                                {selected.legacy_type_label}
                            </p>
                            <h2 className="mt-1 text-2xl font-semibold text-white">
                                {selected.name}
                            </h2>
                            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                                Create the structured identity for this existing record. The legacy record remains intact while the new resource becomes its ownership and relationship anchor.
                            </p>
                        </div>

                        <Card className="space-y-5 p-5">
                            <div>
                                <label className="mb-2 block text-xs font-medium text-slate-400">
                                    Resource name
                                </label>
                                <Input
                                    value={form.name}
                                    onChange={(event) =>
                                        setForm({ ...form, name: event.target.value })
                                    }
                                />
                            </div>

                            <div className="grid gap-4 sm:grid-cols-2">
                                <div>
                                    <label className="mb-2 block text-xs font-medium text-slate-400">
                                        Ownership
                                    </label>
                                    <Select
                                        value={form.ownership_type}
                                        onChange={(event) =>
                                            setForm({
                                                ...form,
                                                ownership_type: event.target.value as
                                                    | "internal"
                                                    | "client",
                                                client_id:
                                                    event.target.value === "internal"
                                                        ? ""
                                                        : form.client_id,
                                            })
                                        }
                                    >
                                        <option value="internal">ADB Internal</option>
                                        <option value="client">Client</option>
                                    </Select>
                                </div>
                                <div>
                                    <label className="mb-2 block text-xs font-medium text-slate-400">
                                        Client
                                    </label>
                                    <Select
                                        value={form.client_id}
                                        disabled={form.ownership_type !== "client"}
                                        onChange={(event) =>
                                            setForm({
                                                ...form,
                                                client_id: event.target.value,
                                            })
                                        }
                                    >
                                        <option value="">Choose client</option>
                                        {options.clients.map((client) => (
                                            <option key={client.id} value={client.id}>
                                                {client.name}
                                                {client.status === "active"
                                                    ? ""
                                                    : ` (${labelFor(client.status)})`}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                            </div>

                            <div className="grid gap-4 sm:grid-cols-3">
                                <div>
                                    <label className="mb-2 block text-xs font-medium text-slate-400">
                                        Environment
                                    </label>
                                    <Select
                                        value={form.environment}
                                        onChange={(event) =>
                                            setForm({
                                                ...form,
                                                environment: event.target.value,
                                            })
                                        }
                                    >
                                        {options.environments.map((value) => (
                                            <option key={value} value={value}>
                                                {labelFor(value)}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <div>
                                    <label className="mb-2 block text-xs font-medium text-slate-400">
                                        Lifecycle
                                    </label>
                                    <Select
                                        value={form.lifecycle_status}
                                        onChange={(event) =>
                                            setForm({
                                                ...form,
                                                lifecycle_status: event.target.value,
                                            })
                                        }
                                    >
                                        {options.lifecycle_statuses.map((value) => (
                                            <option key={value} value={value}>
                                                {labelFor(value)}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                                <div>
                                    <label className="mb-2 block text-xs font-medium text-slate-400">
                                        Criticality
                                    </label>
                                    <Select
                                        value={form.criticality}
                                        onChange={(event) =>
                                            setForm({
                                                ...form,
                                                criticality: event.target.value,
                                            })
                                        }
                                    >
                                        {options.criticalities.map((value) => (
                                            <option key={value} value={value}>
                                                {labelFor(value)}
                                            </option>
                                        ))}
                                    </Select>
                                </div>
                            </div>

                            {saveError ? (
                                <p className="rounded-lg border border-red-950 bg-red-950/30 px-3 py-2 text-sm text-red-300">
                                    {saveError}
                                </p>
                            ) : null}

                            <div className="flex justify-end gap-2 border-t border-slate-800 pt-5">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    onClick={closeReconciliation}
                                    disabled={isSaving}
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="button"
                                    onClick={() => void submitReconciliation()}
                                    disabled={isSaving}
                                >
                                    {isSaving
                                        ? "Reconciling..."
                                        : "Create structured identity"}
                                </Button>
                            </div>
                        </Card>
                    </div>
                </RecordDrawer>
            ) : null}
        </div>
    );
}

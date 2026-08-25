"use client";

import { RecordDrawer } from "@/components/admin/RecordDrawer";
import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    Pagination,
    Select,
    Textarea,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import {
    ProviderAccount,
    ProviderAccountInput,
    ProviderAPI,
    ProviderOptions,
    ProviderPage,
    ServiceProvider,
    ServiceProviderInput,
} from "@/lib/api/providers";
import { Building2, ExternalLink, Plus } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const PAGE_SIZE = 25;
const lifecycleOptions = [
    ["planned", "Planned"],
    ["active", "Active"],
    ["maintenance", "Maintenance"],
    ["deprecated", "Deprecated"],
    ["retired", "Retired"],
    ["archived", "Archived"],
] as const;
const environmentOptions = [
    ["not_applicable", "Not applicable"],
    ["shared", "Shared"],
    ["production", "Production"],
    ["staging", "Staging"],
    ["development", "Development"],
    ["testing", "Testing"],
] as const;
const criticalityOptions = [
    ["low", "Low"],
    ["normal", "Normal"],
    ["high", "High"],
    ["critical", "Critical"],
] as const;

function label(value: string): string {
    return `${value.charAt(0).toUpperCase()}${value.slice(1).replaceAll("_", " ")}`;
}

function accountInput(account?: ProviderAccount): ProviderAccountInput {
    return {
        name: account?.name ?? "",
        provider_id: account?.provider_id ?? 0,
        ownership_type: account?.ownership_type ?? "internal",
        client_id: account?.client_id ?? undefined,
        lifecycle_status: account?.lifecycle_status ?? "active",
        environment: account?.environment ?? "not_applicable",
        criticality: account?.criticality ?? "normal",
        description: account?.description ?? "",
        account_identifier: account?.account_identifier ?? "",
        tenant_id: account?.tenant_id ?? "",
        project_id: account?.project_id ?? "",
        portal_url: account?.portal_url ?? "",
        default_region: account?.default_region ?? "",
        support_plan: account?.support_plan ?? "",
        billing_reference: account?.billing_reference ?? "",
    };
}

function providerInput(): ServiceProviderInput {
    return {
        name: "",
        category: "other",
        website_url: "",
        support_url: "",
        status_page_url: "",
        documentation_url: "",
        notes: "",
    };
}

export function ProviderWorkspace() {
    const { hasPermission } = useAuth();
    const [mode, setMode] = useState<"accounts" | "catalogue">("accounts");
    const [options, setOptions] = useState<ProviderOptions | null>(null);
    const [accounts, setAccounts] =
        useState<ProviderPage<ProviderAccount> | null>(null);
    const [providers, setProviders] =
        useState<ProviderPage<ServiceProvider> | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [lifecycle, setLifecycle] = useState("current");
    const [ownership, setOwnership] = useState("all");
    const [providerId, setProviderId] = useState("");
    const [category, setCategory] = useState("");
    const [active, setActive] = useState("active");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedAccount, setSelectedAccount] =
        useState<ProviderAccount | null>(null);
    const [showAccountForm, setShowAccountForm] = useState(false);
    const [showProviderForm, setShowProviderForm] = useState(false);

    const canCreateAccount =
        hasPermission("infrastructure.add_provideraccount") &&
        hasPermission("infrastructure.add_infrastructureresource");
    const canCreateProvider = hasPermission(
        "infrastructure.add_serviceprovider",
    );

    useEffect(() => {
        const handle = window.setTimeout(
            () => setDebouncedSearch(search.trim()),
            250,
        );
        return () => window.clearTimeout(handle);
    }, [search]);

    useEffect(
        () => setPage(1),
        [
            mode,
            debouncedSearch,
            lifecycle,
            ownership,
            providerId,
            category,
            active,
        ],
    );

    const accountQuery = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
            lifecycle,
            ownership,
        });
        if (providerId) params.set("provider_id", providerId);
        if (debouncedSearch) params.set("search", debouncedSearch);
        return params.toString();
    }, [debouncedSearch, lifecycle, ownership, page, providerId]);

    const providerQuery = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
            active,
        });
        if (category) params.set("category", category);
        if (debouncedSearch) params.set("search", debouncedSearch);
        return params.toString();
    }, [active, category, debouncedSearch, page]);

    const loadOptions = useCallback(async () => {
        setOptions((await fetchAPI(ProviderAPI.options())) as ProviderOptions);
    }, []);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            if (mode === "accounts") {
                setAccounts(
                    (await fetchAPI(
                        ProviderAPI.accounts(accountQuery),
                    )) as ProviderPage<ProviderAccount>,
                );
            } else {
                setProviders(
                    (await fetchAPI(
                        ProviderAPI.providers(providerQuery),
                    )) as ProviderPage<ServiceProvider>,
                );
            }
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load providers.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [accountQuery, mode, providerQuery]);

    useEffect(() => {
        void loadOptions().catch(() => undefined);
    }, [loadOptions]);
    useEffect(() => {
        void load();
    }, [load]);

    const data = mode === "accounts" ? accounts : providers;

    return (
        <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800">
                <div
                    className="flex gap-1"
                    role="tablist"
                    aria-label="Provider views"
                >
                    {(["accounts", "catalogue"] as const).map((item) => (
                        <button
                            key={item}
                            type="button"
                            role="tab"
                            aria-selected={mode === item}
                            onClick={() => setMode(item)}
                            className={`border-b-2 px-4 py-3 text-sm font-medium transition ${
                                mode === item
                                    ? "border-adb-cyan-400 text-white"
                                    : "border-transparent text-slate-500 hover:text-slate-300"
                            }`}
                        >
                            {item === "accounts"
                                ? "Provider accounts"
                                : "Service catalogue"}
                        </button>
                    ))}
                </div>
                {mode === "accounts" && canCreateAccount ? (
                    <Button
                        type="button"
                        onClick={() => setShowAccountForm(true)}
                    >
                        <Plus className="h-4 w-4" /> Add account
                    </Button>
                ) : mode === "catalogue" && canCreateProvider ? (
                    <Button
                        type="button"
                        onClick={() => setShowProviderForm(true)}
                    >
                        <Plus className="h-4 w-4" /> Add provider
                    </Button>
                ) : null}
            </div>

            <div className="grid gap-3 border-b border-slate-800 pb-5 md:grid-cols-2 xl:grid-cols-4">
                <Input
                    aria-label="Search providers"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder={
                        mode === "accounts"
                            ? "Search accounts, tenants or clients..."
                            : "Search providers..."
                    }
                />
                {mode === "accounts" ? (
                    <>
                        <Select
                            value={lifecycle}
                            onChange={(event) =>
                                setLifecycle(event.target.value)
                            }
                        >
                            <option value="current">Current resources</option>
                            {lifecycleOptions.map(([value, text]) => (
                                <option key={value} value={value}>
                                    {text}
                                </option>
                            ))}
                            <option value="all">All lifecycle states</option>
                        </Select>
                        <Select
                            value={ownership}
                            onChange={(event) =>
                                setOwnership(event.target.value)
                            }
                        >
                            <option value="all">All ownership</option>
                            <option value="internal">ADB Internal</option>
                            <option value="client">Client-owned</option>
                        </Select>
                        <Select
                            value={providerId}
                            onChange={(event) =>
                                setProviderId(event.target.value)
                            }
                        >
                            <option value="">All providers</option>
                            {options?.providers.map((provider) => (
                                <option key={provider.id} value={provider.id}>
                                    {provider.name}
                                </option>
                            ))}
                        </Select>
                    </>
                ) : (
                    <>
                        <Select
                            value={active}
                            onChange={(event) => setActive(event.target.value)}
                        >
                            <option value="active">Active providers</option>
                            <option value="inactive">Inactive providers</option>
                            <option value="all">All providers</option>
                        </Select>
                        <Select
                            value={category}
                            onChange={(event) =>
                                setCategory(event.target.value)
                            }
                        >
                            <option value="">All categories</option>
                            {options?.categories.map((item) => (
                                <option key={item.value} value={item.value}>
                                    {item.label}
                                </option>
                            ))}
                        </Select>
                    </>
                )}
            </div>

            {error ? (
                <DataError message={error} onRetry={() => void load()} />
            ) : isLoading && !data ? (
                <DataLoading label="Loading providers..." />
            ) : !data || data.items.length === 0 ? (
                <EmptyState
                    title={
                        mode === "accounts"
                            ? "No provider accounts in this view"
                            : "No service providers in this view"
                    }
                    description="Change the filters or add the first record for this scope."
                />
            ) : mode === "accounts" && accounts ? (
                <AccountTable
                    accounts={accounts.items}
                    onSelect={setSelectedAccount}
                />
            ) : providers ? (
                <ProviderTable providers={providers.items} />
            ) : null}

            {data && data.total > 0 ? (
                <Pagination
                    page={data.page}
                    pageSize={data.page_size}
                    totalItems={data.total}
                    onPageChange={setPage}
                    disabled={isLoading}
                />
            ) : null}

            {selectedAccount ? (
                <RecordDrawer
                    onClose={() => setSelectedAccount(null)}
                    fullPageHref={`/admin/infrastructure/resources/${selectedAccount.resource_id}`}
                >
                    <AccountDetail
                        accountId={selectedAccount.id}
                        options={options}
                        onChanged={() => {
                            void load();
                            void loadOptions();
                        }}
                    />
                </RecordDrawer>
            ) : null}
            {showAccountForm && options ? (
                <RecordDrawer onClose={() => setShowAccountForm(false)}>
                    <AccountForm
                        options={options}
                        onCancel={() => setShowAccountForm(false)}
                        onSaved={(account) => {
                            setShowAccountForm(false);
                            setSelectedAccount(account);
                            void load();
                        }}
                    />
                </RecordDrawer>
            ) : null}
            {showProviderForm && options ? (
                <RecordDrawer onClose={() => setShowProviderForm(false)}>
                    <ProviderForm
                        options={options}
                        onCancel={() => setShowProviderForm(false)}
                        onSaved={() => {
                            setShowProviderForm(false);
                            void loadOptions();
                            void load();
                        }}
                    />
                </RecordDrawer>
            ) : null}
        </div>
    );
}

function AccountTable({
    accounts,
    onSelect,
}: {
    accounts: ProviderAccount[];
    onSelect: (account: ProviderAccount) => void;
}) {
    return (
        <div className="overflow-x-auto border-y border-slate-800">
            <table className="w-full min-w-[960px] text-left text-sm">
                <thead className="bg-slate-950/70 text-xs text-slate-500 uppercase">
                    <tr>
                        <th className="px-4 py-3">Account</th>
                        <th className="px-4 py-3">Provider</th>
                        <th className="px-4 py-3">Scope</th>
                        <th className="px-4 py-3">Identifier</th>
                        <th className="px-4 py-3">Region</th>
                        <th className="px-4 py-3">Lifecycle</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                    {accounts.map((account) => (
                        <tr key={account.id} className="hover:bg-slate-900/45">
                            <td className="px-4 py-3">
                                <button
                                    type="button"
                                    onClick={() => onSelect(account)}
                                    className="hover:text-adb-cyan-300 font-medium text-slate-100"
                                >
                                    {account.name}
                                </button>
                                {account.tenant_id || account.project_id ? (
                                    <div className="mt-1 text-xs text-slate-600">
                                        {account.tenant_id ||
                                            account.project_id}
                                    </div>
                                ) : null}
                            </td>
                            <td className="px-4 py-3 text-slate-300">
                                {account.provider_name}
                            </td>
                            <td className="px-4 py-3 text-slate-400">
                                {account.client_name || "ADB Internal"}
                            </td>
                            <td className="px-4 py-3 font-mono text-xs text-slate-400">
                                {account.account_identifier || "-"}
                            </td>
                            <td className="px-4 py-3 text-slate-400">
                                {account.default_region || "-"}
                            </td>
                            <td className="px-4 py-3">
                                <Badge>{label(account.lifecycle_status)}</Badge>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function ProviderTable({ providers }: { providers: ServiceProvider[] }) {
    return (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {providers.map((provider) => (
                <Card key={provider.id} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-3">
                            <Building2 className="text-adb-cyan-400 h-5 w-5 shrink-0" />
                            <div className="min-w-0">
                                <div className="truncate font-medium text-slate-100">
                                    {provider.name}
                                </div>
                                <div className="mt-0.5 text-xs text-slate-500">
                                    {label(provider.category)}
                                </div>
                            </div>
                        </div>
                        <Badge>{provider.account_count} accounts</Badge>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3 text-xs">
                        {provider.website_url ? (
                            <a
                                href={provider.website_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-adb-cyan-300 inline-flex items-center gap-1"
                            >
                                Website <ExternalLink className="h-3 w-3" />
                            </a>
                        ) : null}
                        {provider.support_url ? (
                            <a
                                href={provider.support_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-slate-400"
                            >
                                Support <ExternalLink className="h-3 w-3" />
                            </a>
                        ) : null}
                        {provider.status_page_url ? (
                            <a
                                href={provider.status_page_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-slate-400"
                            >
                                Status <ExternalLink className="h-3 w-3" />
                            </a>
                        ) : null}
                    </div>
                </Card>
            ))}
        </div>
    );
}

function AccountDetail({
    accountId,
    options,
    onChanged,
}: {
    accountId: number;
    options: ProviderOptions | null;
    onChanged: () => void;
}) {
    const { hasPermission } = useAuth();
    const [account, setAccount] = useState<ProviderAccount | null>(null);
    const [editing, setEditing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const load = useCallback(async () => {
        try {
            setAccount(
                (await fetchAPI(
                    ProviderAPI.account(accountId),
                )) as ProviderAccount,
            );
            setError(null);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load provider account.",
            );
        }
    }, [accountId]);
    useEffect(() => {
        void load();
    }, [load]);

    if (error) return <DataError message={error} onRetry={() => void load()} />;
    if (!account) return <DataLoading label="Loading provider account..." />;
    if (editing && options)
        return (
            <AccountForm
                account={account}
                options={options}
                onCancel={() => setEditing(false)}
                onSaved={(saved) => {
                    setAccount(saved);
                    setEditing(false);
                    onChanged();
                }}
            />
        );

    const canEdit =
        hasPermission("infrastructure.change_provideraccount") &&
        hasPermission("infrastructure.change_infrastructureresource");
    const canArchive =
        hasPermission("infrastructure.delete_provideraccount") &&
        account.lifecycle_status !== "archived";
    async function archive() {
        if (!window.confirm(`Archive ${account?.name}?`)) return;
        const saved = (await fetchAPI(ProviderAPI.archiveAccount(accountId), {
            method: "POST",
        })) as ProviderAccount;
        setAccount(saved);
        onChanged();
    }
    return (
        <div className="space-y-5">
            <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                    <div className="text-adb-cyan-400 text-xs font-semibold uppercase">
                        {account.provider_name}
                    </div>
                    <h2 className="mt-1 text-xl font-semibold text-white">
                        {account.name}
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        {account.client_name || "ADB Internal"}
                    </p>
                </div>
                <div className="flex gap-2">
                    {canEdit ? (
                        <Button
                            type="button"
                            variant="secondary"
                            onClick={() => setEditing(true)}
                        >
                            Edit
                        </Button>
                    ) : null}
                    {canArchive ? (
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => void archive()}
                        >
                            Archive
                        </Button>
                    ) : null}
                </div>
            </div>
            <dl className="grid gap-5 sm:grid-cols-2">
                {[
                    ["Account identifier", account.account_identifier],
                    ["Tenant ID", account.tenant_id],
                    ["Project ID", account.project_id],
                    ["Default region", account.default_region],
                    ["Support plan", account.support_plan],
                    ["Billing reference", account.billing_reference],
                ].map(([term, value]) => (
                    <div key={term}>
                        <dt className="text-xs text-slate-600">{term}</dt>
                        <dd className="mt-1 text-sm break-words text-slate-300">
                            {value || "-"}
                        </dd>
                    </div>
                ))}
            </dl>
            {account.description ? (
                <div className="border-t border-slate-800 pt-4 text-sm leading-6 text-slate-400">
                    {account.description}
                </div>
            ) : null}
            <div className="flex flex-wrap gap-2 border-t border-slate-800 pt-4">
                <ButtonLink
                    href={`/admin/infrastructure/resources/${account.resource_id}`}
                    variant="secondary"
                >
                    Open resource workspace
                </ButtonLink>
                {account.portal_url ? (
                    <ButtonLink
                        href={account.portal_url}
                        target="_blank"
                        rel="noreferrer"
                        variant="ghost"
                    >
                        Open provider portal{" "}
                        <ExternalLink className="h-4 w-4" />
                    </ButtonLink>
                ) : null}
            </div>
        </div>
    );
}

function Field({
    label: text,
    children,
    wide = false,
}: {
    label: string;
    children: React.ReactNode;
    wide?: boolean;
}) {
    return (
        <label className={wide ? "space-y-2 sm:col-span-2" : "space-y-2"}>
            <span className="block text-xs font-medium text-slate-400">
                {text}
            </span>
            {children}
        </label>
    );
}

function AccountForm({
    options,
    account,
    onCancel,
    onSaved,
}: {
    options: ProviderOptions;
    account?: ProviderAccount;
    onCancel: () => void;
    onSaved: (account: ProviderAccount) => void;
}) {
    const [form, setForm] = useState(() => accountInput(account));
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    function update<K extends keyof ProviderAccountInput>(
        key: K,
        value: ProviderAccountInput[K],
    ) {
        setForm((current) => ({ ...current, [key]: value }));
    }
    async function submit(event: FormEvent) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        try {
            const body = account
                ? (({
                      ownership_type: _ownership,
                      client_id: _client,
                      ...editable
                  }) => editable)(form)
                : form;
            const saved = (await fetchAPI(
                account
                    ? ProviderAPI.account(account.id)
                    : ProviderAPI.accounts(),
                {
                    method: account ? "PUT" : "POST",
                    body: JSON.stringify(body),
                },
            )) as ProviderAccount;
            onSaved(saved);
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : "Unable to save provider account.",
            );
        } finally {
            setSaving(false);
        }
    }
    return (
        <form className="space-y-5" onSubmit={(event) => void submit(event)}>
            <div>
                <div className="text-adb-cyan-400 text-xs font-semibold uppercase">
                    Provider account
                </div>
                <h2 className="mt-1 text-xl font-semibold text-white">
                    {account ? "Edit account" : "Add account"}
                </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Account name">
                    <Input
                        required
                        value={form.name}
                        onChange={(e) => update("name", e.target.value)}
                    />
                </Field>
                <Field label="Service provider">
                    <Select
                        required
                        value={form.provider_id || ""}
                        onChange={(e) =>
                            update("provider_id", Number(e.target.value))
                        }
                    >
                        <option value="">Choose provider</option>
                        {options.providers.map((provider) => (
                            <option key={provider.id} value={provider.id}>
                                {provider.name}
                            </option>
                        ))}
                    </Select>
                </Field>
                {!account ? (
                    <>
                        <Field label="Ownership">
                            <Select
                                value={form.ownership_type}
                                onChange={(e) =>
                                    update(
                                        "ownership_type",
                                        e.target.value as "internal" | "client",
                                    )
                                }
                            >
                                <option value="internal">ADB Internal</option>
                                <option value="client">Client-owned</option>
                            </Select>
                        </Field>
                        {form.ownership_type === "client" ? (
                            <Field label="Client">
                                <Select
                                    required
                                    value={form.client_id ?? ""}
                                    onChange={(e) =>
                                        update(
                                            "client_id",
                                            Number(e.target.value),
                                        )
                                    }
                                >
                                    <option value="">Choose client</option>
                                    {options.clients.map((client) => (
                                        <option
                                            key={client.id}
                                            value={client.id}
                                        >
                                            {client.name}
                                        </option>
                                    ))}
                                </Select>
                            </Field>
                        ) : null}
                    </>
                ) : null}
                <Field label="Lifecycle">
                    <Select
                        value={form.lifecycle_status}
                        onChange={(e) =>
                            update("lifecycle_status", e.target.value)
                        }
                    >
                        {lifecycleOptions.map(([value, text]) => (
                            <option key={value} value={value}>
                                {text}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Environment">
                    <Select
                        value={form.environment}
                        onChange={(e) => update("environment", e.target.value)}
                    >
                        {environmentOptions.map(([value, text]) => (
                            <option key={value} value={value}>
                                {text}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Criticality">
                    <Select
                        value={form.criticality}
                        onChange={(e) => update("criticality", e.target.value)}
                    >
                        {criticalityOptions.map(([value, text]) => (
                            <option key={value} value={value}>
                                {text}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Account identifier">
                    <Input
                        value={form.account_identifier}
                        onChange={(e) =>
                            update("account_identifier", e.target.value)
                        }
                    />
                </Field>
                <Field label="Tenant ID">
                    <Input
                        value={form.tenant_id}
                        onChange={(e) => update("tenant_id", e.target.value)}
                    />
                </Field>
                <Field label="Project ID">
                    <Input
                        value={form.project_id}
                        onChange={(e) => update("project_id", e.target.value)}
                    />
                </Field>
                <Field label="Provider portal URL">
                    <Input
                        type="url"
                        value={form.portal_url}
                        onChange={(e) => update("portal_url", e.target.value)}
                    />
                </Field>
                <Field label="Default region">
                    <Input
                        value={form.default_region}
                        onChange={(e) =>
                            update("default_region", e.target.value)
                        }
                    />
                </Field>
                <Field label="Support plan">
                    <Input
                        value={form.support_plan}
                        onChange={(e) => update("support_plan", e.target.value)}
                    />
                </Field>
                <Field label="Billing reference">
                    <Input
                        value={form.billing_reference}
                        onChange={(e) =>
                            update("billing_reference", e.target.value)
                        }
                    />
                </Field>
                <Field label="Safe description" wide>
                    <Textarea
                        rows={3}
                        value={form.description}
                        onChange={(e) => update("description", e.target.value)}
                    />
                </Field>
            </div>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <div className="flex justify-end gap-2 border-t border-slate-800 pt-4">
                <Button
                    type="button"
                    variant="ghost"
                    onClick={onCancel}
                    disabled={saving}
                >
                    Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                    {saving ? "Saving..." : "Save account"}
                </Button>
            </div>
        </form>
    );
}

function ProviderForm({
    options,
    onCancel,
    onSaved,
}: {
    options: ProviderOptions;
    onCancel: () => void;
    onSaved: () => void;
}) {
    const [form, setForm] = useState(providerInput);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    async function submit(event: FormEvent) {
        event.preventDefault();
        setSaving(true);
        setError(null);
        try {
            await fetchAPI(ProviderAPI.providers(), {
                method: "POST",
                body: JSON.stringify(form),
            });
            onSaved();
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : "Unable to save provider.",
            );
        } finally {
            setSaving(false);
        }
    }
    return (
        <form className="space-y-5" onSubmit={(event) => void submit(event)}>
            <div>
                <div className="text-adb-cyan-400 text-xs font-semibold uppercase">
                    Service catalogue
                </div>
                <h2 className="mt-1 text-xl font-semibold text-white">
                    Add provider
                </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Provider name">
                    <Input
                        required
                        value={form.name}
                        onChange={(e) =>
                            setForm({ ...form, name: e.target.value })
                        }
                    />
                </Field>
                <Field label="Category">
                    <Select
                        value={form.category}
                        onChange={(e) =>
                            setForm({ ...form, category: e.target.value })
                        }
                    >
                        {options.categories.map((item) => (
                            <option key={item.value} value={item.value}>
                                {item.label}
                            </option>
                        ))}
                    </Select>
                </Field>
                <Field label="Website URL">
                    <Input
                        type="url"
                        value={form.website_url}
                        onChange={(e) =>
                            setForm({ ...form, website_url: e.target.value })
                        }
                    />
                </Field>
                <Field label="Support URL">
                    <Input
                        type="url"
                        value={form.support_url}
                        onChange={(e) =>
                            setForm({ ...form, support_url: e.target.value })
                        }
                    />
                </Field>
                <Field label="Status page URL">
                    <Input
                        type="url"
                        value={form.status_page_url}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                status_page_url: e.target.value,
                            })
                        }
                    />
                </Field>
                <Field label="Documentation URL">
                    <Input
                        type="url"
                        value={form.documentation_url}
                        onChange={(e) =>
                            setForm({
                                ...form,
                                documentation_url: e.target.value,
                            })
                        }
                    />
                </Field>
                <Field label="Safe notes" wide>
                    <Textarea
                        rows={3}
                        value={form.notes}
                        onChange={(e) =>
                            setForm({ ...form, notes: e.target.value })
                        }
                    />
                </Field>
            </div>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
            <div className="flex justify-end gap-2 border-t border-slate-800 pt-4">
                <Button type="button" variant="ghost" onClick={onCancel}>
                    Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                    {saving ? "Saving..." : "Save provider"}
                </Button>
            </div>
        </form>
    );
}

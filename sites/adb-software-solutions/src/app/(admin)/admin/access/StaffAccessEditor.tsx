"use client";

import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    Input,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import {
    CapabilityOption,
    StaffAccessAPI,
    StaffAccessOptions,
    StaffAccessWrite,
    StaffInviteResponse,
    StaffInviteWrite,
    StaffStatusResponse,
    StaffUserDetail,
} from "@/lib/staff-access";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

interface AccessDraft extends StaffAccessWrite {
    default_mode: "all" | "selected";
}

const EMPTY_ACCESS: AccessDraft = {
    group_ids: [],
    direct_permission_ids: [],
    all_clients: false,
    client_ids: [],
    all_ticket_queues: false,
    ticket_queue_ids: [],
    default_ticket_queue_ids: [],
    default_mode: "all",
};

function toggleId(values: number[], id: number): number[] {
    return values.includes(id) ? values.filter((value) => value !== id) : [...values, id];
}

function personName(user: StaffUserDetail): string {
    return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
}

function formatDateTime(value: string | null): string {
    if (!value) return "Never";
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function permissionGroupLabel(capability: CapabilityOption): string {
    return capability.app_label.replaceAll("_", " ");
}

function SelectionCard({
    checked,
    disabled,
    title,
    description,
    badge,
    onChange,
}: {
    checked: boolean;
    disabled?: boolean;
    title: string;
    description?: string;
    badge?: React.ReactNode;
    onChange: () => void;
}) {
    return (
        <label
            className={`flex gap-3 rounded-lg border p-3 transition ${
                checked ? "border-cyan-800 bg-cyan-950/20" : "border-slate-800 bg-slate-950/40"
            } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-slate-700"}`}
        >
            <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={onChange}
                className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500"
            />
            <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2 text-sm font-medium text-slate-200">
                    {title}
                    {badge}
                </span>
                {description ? (
                    <span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span>
                ) : null}
            </span>
        </label>
    );
}

export function StaffAccessEditor({ userId }: { userId?: string }) {
    const router = useRouter();
    const { hasPermission } = useAuth();
    const canAdminister = hasPermission("access_control.manage_staff_access");
    const isInvite = !userId;
    const [options, setOptions] = useState<StaffAccessOptions | null>(null);
    const [staffUser, setStaffUser] = useState<StaffUserDetail | null>(null);
    const [access, setAccess] = useState<AccessDraft>(EMPTY_ACCESS);
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);

    const load = useCallback(async () => {
        if (!canAdminister) {
            setIsLoading(false);
            return;
        }
        try {
            setIsLoading(true);
            setError(null);
            const [nextOptions, nextUser] = await Promise.all([
                fetchAPI(StaffAccessAPI.options) as Promise<StaffAccessOptions>,
                userId
                    ? (fetchAPI(StaffAccessAPI.detail(userId)) as Promise<StaffUserDetail>)
                    : Promise.resolve(null),
            ]);
            setOptions(nextOptions);
            setStaffUser(nextUser);
            if (nextUser) {
                setAccess({
                    group_ids: nextUser.access.group_ids,
                    direct_permission_ids: nextUser.access.direct_permission_ids,
                    all_clients: nextUser.access.clients.all,
                    client_ids: nextUser.access.clients.ids,
                    all_ticket_queues: nextUser.access.ticket_queues.all,
                    ticket_queue_ids: nextUser.access.ticket_queues.ids,
                    default_ticket_queue_ids: nextUser.access.default_ticket_queue_ids,
                    default_mode:
                        nextUser.access.default_ticket_queue_ids.length === 0 ? "all" : "selected",
                });
            }
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load staff access.");
        } finally {
            setIsLoading(false);
        }
    }, [canAdminister, userId]);

    useEffect(() => {
        void load();
    }, [load]);

    const accessibleEnabledQueueIds = useMemo(() => {
        if (!options) return [];
        return options.ticket_queues
            .filter(
                (queue) =>
                    queue.enabled &&
                    (access.all_ticket_queues || access.ticket_queue_ids.includes(queue.id)),
            )
            .map((queue) => queue.id);
    }, [access.all_ticket_queues, access.ticket_queue_ids, options]);

    useEffect(() => {
        setAccess((current) => ({
            ...current,
            default_ticket_queue_ids: current.default_ticket_queue_ids.filter((id) =>
                accessibleEnabledQueueIds.includes(id),
            ),
        }));
    }, [accessibleEnabledQueueIds]);

    const capabilityGroups = useMemo(() => {
        const groups = new Map<string, CapabilityOption[]>();
        for (const capability of options?.capabilities ?? []) {
            const label = permissionGroupLabel(capability);
            groups.set(label, [...(groups.get(label) ?? []), capability]);
        }
        return Array.from(groups.entries());
    }, [options]);

    const writable = isInvite || Boolean(staffUser?.can_manage);

    const writePayload = (): StaffAccessWrite => ({
        group_ids: access.group_ids,
        direct_permission_ids: access.direct_permission_ids,
        all_clients: access.all_clients,
        client_ids: access.all_clients ? [] : access.client_ids,
        all_ticket_queues: access.all_ticket_queues,
        ticket_queue_ids: access.all_ticket_queues ? [] : access.ticket_queue_ids,
        default_ticket_queue_ids:
            access.default_mode === "all"
                ? accessibleEnabledQueueIds
                : access.default_ticket_queue_ids,
    });

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        if (!writable) return;
        try {
            setIsSaving(true);
            setError(null);
            setNotice(null);
            if (isInvite) {
                const payload: StaffInviteWrite = {
                    ...writePayload(),
                    email,
                    first_name: firstName,
                    last_name: lastName,
                };
                const response = (await fetchAPI(StaffAccessAPI.invite, {
                    method: "POST",
                    body: JSON.stringify(payload),
                })) as StaffInviteResponse;
                router.push(`/admin/access/users/${response.user.id}`);
                return;
            }
            if (!userId) return;
            const nextUser = (await fetchAPI(StaffAccessAPI.update(userId), {
                method: "PUT",
                body: JSON.stringify(writePayload()),
            })) as StaffUserDetail;
            setStaffUser(nextUser);
            setNotice("Staff access updated.");
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to save staff access.");
        } finally {
            setIsSaving(false);
        }
    };

    const changeStatus = async (active: boolean) => {
        if (!userId || !staffUser?.can_manage) return;
        try {
            setIsSaving(true);
            setError(null);
            const response = (await fetchAPI(
                active ? StaffAccessAPI.activate(userId) : StaffAccessAPI.deactivate(userId),
                { method: "POST" },
            )) as StaffStatusResponse;
            setStaffUser(response.user);
            setNotice(response.message);
        } catch (statusError) {
            setError(statusError instanceof Error ? statusError.message : "Unable to change account status.");
        } finally {
            setIsSaving(false);
        }
    };

    const resendInvitation = async () => {
        if (!userId || !staffUser?.can_manage || !staffUser.setup_pending) return;
        try {
            setIsSaving(true);
            setError(null);
            const response = (await fetchAPI(StaffAccessAPI.resendInvitation(userId), {
                method: "POST",
            })) as StaffInviteResponse;
            setStaffUser(response.user);
            setNotice(
                response.invitation_email_sent
                    ? "Invitation email sent with a fresh one-hour setup link."
                    : "A fresh setup link was created, but the invitation email could not be sent.",
            );
        } catch (resendError) {
            setError(resendError instanceof Error ? resendError.message : "Unable to resend invitation.");
        } finally {
            setIsSaving(false);
        }
    };

    if (!canAdminister) {
        return <DataError message="You do not have permission to administer staff access." />;
    }
    if (isLoading) return <DataLoading label="Loading staff access…" />;
    if (error && !options) return <DataError message={error} onRetry={() => void load()} />;
    if (!options) return <DataError message="Staff access options are unavailable." />;
    if (!isInvite && !staffUser) return <DataError message="Staff user could not be loaded." />;

    return (
        <form onSubmit={submit} className="space-y-6">
            {error ? <DataError message={error} /> : null}
            {notice ? (
                <div className="rounded-lg border border-emerald-900/70 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200">
                    {notice}
                </div>
            ) : null}

            {isInvite ? (
                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Staff identity</h2>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                        The new staff member receives a one-hour password-setup link. No temporary password is stored or displayed here.
                    </p>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <div>
                            <label className="mb-1.5 block text-xs font-medium text-slate-400">First name</label>
                            <Input value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
                        </div>
                        <div>
                            <label className="mb-1.5 block text-xs font-medium text-slate-400">Last name</label>
                            <Input value={lastName} onChange={(event) => setLastName(event.target.value)} required />
                        </div>
                        <div className="md:col-span-2">
                            <label className="mb-1.5 block text-xs font-medium text-slate-400">Email</label>
                            <Input
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                required
                            />
                        </div>
                    </div>
                </Card>
            ) : staffUser ? (
                <Card className="p-5">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                            <div className="flex flex-wrap items-center gap-2">
                                <h2 className="text-lg font-semibold text-white">{personName(staffUser)}</h2>
                                <Badge variant={staffUser.is_active ? "success" : "neutral"}>
                                    {staffUser.is_active ? "Active" : "Inactive"}
                                </Badge>
                                {staffUser.setup_pending ? <Badge variant="warning">Setup pending</Badge> : null}
                                {staffUser.is_superuser ? <Badge variant="danger">Superuser</Badge> : null}
                            </div>
                            <p className="mt-1 text-sm text-slate-400">{staffUser.email}</p>
                            <p className="mt-2 text-xs text-slate-600">
                                Last login: {formatDateTime(staffUser.last_login)} · Joined {formatDateTime(staffUser.date_joined)}
                            </p>
                        </div>
                        {staffUser.can_manage ? (
                            <div className="flex flex-wrap gap-2">
                                {staffUser.setup_pending ? (
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        disabled={isSaving}
                                        onClick={() => void resendInvitation()}
                                    >
                                        Resend invitation
                                    </Button>
                                ) : null}
                                <Button
                                    type="button"
                                    variant={staffUser.is_active ? "destructive" : "secondary"}
                                    disabled={isSaving}
                                    onClick={() => void changeStatus(!staffUser.is_active)}
                                >
                                    {staffUser.is_active ? "Deactivate" : "Activate"}
                                </Button>
                            </div>
                        ) : null}
                    </div>
                    {!staffUser.can_manage ? (
                        <p className="mt-4 rounded-lg border border-amber-900/60 bg-amber-950/20 px-3 py-2 text-xs text-amber-200">
                            This account is read-only here. Non-superuser access administrators cannot change their own access or a superuser account.
                        </p>
                    ) : null}
                </Card>
            ) : null}

            <Card className="p-5">
                <h2 className="text-sm font-semibold text-white">Groups / capability bundles</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                    Groups provide reusable role-like bundles. Direct capabilities below are additive exceptions, not a second role system.
                </p>
                <div className="mt-4 grid gap-2 lg:grid-cols-2">
                    {options.groups.map((group) => (
                        <SelectionCard
                            key={group.id}
                            checked={access.group_ids.includes(group.id)}
                            disabled={!writable}
                            title={group.name}
                            description={`${group.permission_ids.length} assignable business capabilities`}
                            onChange={() =>
                                setAccess((current) => ({
                                    ...current,
                                    group_ids: toggleId(current.group_ids, group.id),
                                }))
                            }
                        />
                    ))}
                    {options.groups.length === 0 ? (
                        <p className="text-sm text-slate-600">No Groups are configured yet.</p>
                    ) : null}
                </div>
            </Card>

            <Card className="p-5">
                <h2 className="text-sm font-semibold text-white">Direct capabilities</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                    Grant only capabilities that should sit outside the selected Groups. Framework-level Django user/permission CRUD is intentionally unavailable here.
                </p>
                <div className="mt-5 space-y-5">
                    {capabilityGroups.map(([label, capabilities]) => (
                        <div key={label}>
                            <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                                {label}
                            </h3>
                            <div className="grid gap-2 lg:grid-cols-2">
                                {capabilities.map((capability) => (
                                    <SelectionCard
                                        key={capability.id}
                                        checked={access.direct_permission_ids.includes(capability.id)}
                                        disabled={!writable}
                                        title={capability.name}
                                        description={capability.code}
                                        badge={
                                            capability.sensitive ? (
                                                <Badge variant="warning">Sensitive</Badge>
                                            ) : undefined
                                        }
                                        onChange={() =>
                                            setAccess((current) => ({
                                                ...current,
                                                direct_permission_ids: toggleId(
                                                    current.direct_permission_ids,
                                                    capability.id,
                                                ),
                                            }))
                                        }
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </Card>

            <Card className="p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-white">Client scope</h2>
                        <p className="mt-1 text-xs leading-5 text-slate-500">
                            Controls which Client-owned records this staff member can reach across scoped operational domains.
                        </p>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-300">
                        <input
                            type="checkbox"
                            checked={access.all_clients}
                            disabled={!writable}
                            onChange={(event) =>
                                setAccess((current) => ({ ...current, all_clients: event.target.checked }))
                            }
                            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500"
                        />
                        All clients
                    </label>
                </div>
                {!access.all_clients ? (
                    <div className="mt-4 grid max-h-96 gap-2 overflow-y-auto lg:grid-cols-2">
                        {options.clients.map((client) => (
                            <SelectionCard
                                key={client.id}
                                checked={access.client_ids.includes(client.id)}
                                disabled={!writable}
                                title={client.company || client.name}
                                description={`${client.name} · ${client.status}`}
                                onChange={() =>
                                    setAccess((current) => ({
                                        ...current,
                                        client_ids: toggleId(current.client_ids, client.id),
                                    }))
                                }
                            />
                        ))}
                    </div>
                ) : null}
            </Card>

            <Card className="p-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <h2 className="text-sm font-semibold text-white">Ticket Queue scope</h2>
                        <p className="mt-1 text-xs leading-5 text-slate-500">
                            Queue access is authorization. Default Queues below are only the user's normal Ticket-workspace preference.
                        </p>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-slate-300">
                        <input
                            type="checkbox"
                            checked={access.all_ticket_queues}
                            disabled={!writable}
                            onChange={(event) =>
                                setAccess((current) => ({
                                    ...current,
                                    all_ticket_queues: event.target.checked,
                                }))
                            }
                            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-500"
                        />
                        All queues
                    </label>
                </div>
                {!access.all_ticket_queues ? (
                    <div className="mt-4 grid gap-2 lg:grid-cols-2">
                        {options.ticket_queues.map((queue) => (
                            <SelectionCard
                                key={queue.id}
                                checked={access.ticket_queue_ids.includes(queue.id)}
                                disabled={!writable}
                                title={queue.name}
                                description={`${queue.brand_name ?? "No brand"} · ${queue.key}`}
                                badge={!queue.enabled ? <Badge variant="neutral">Disabled</Badge> : undefined}
                                onChange={() =>
                                    setAccess((current) => ({
                                        ...current,
                                        ticket_queue_ids: toggleId(current.ticket_queue_ids, queue.id),
                                    }))
                                }
                            />
                        ))}
                    </div>
                ) : null}

                <div className="mt-6 border-t border-slate-800 pt-5">
                    <h3 className="text-sm font-semibold text-white">Default Ticket Queues</h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                        “All accessible” stores no narrowing preference. A selected subset changes the default work view but never expands authorization.
                    </p>
                    <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-300">
                        <label className="flex items-center gap-2">
                            <input
                                type="radio"
                                name="default-queue-mode"
                                checked={access.default_mode === "all"}
                                disabled={!writable}
                                onChange={() =>
                                    setAccess((current) => ({ ...current, default_mode: "all" }))
                                }
                            />
                            All accessible queues
                        </label>
                        <label className="flex items-center gap-2">
                            <input
                                type="radio"
                                name="default-queue-mode"
                                checked={access.default_mode === "selected"}
                                disabled={!writable}
                                onChange={() =>
                                    setAccess((current) => ({ ...current, default_mode: "selected" }))
                                }
                            />
                            Selected queues
                        </label>
                    </div>
                    {access.default_mode === "selected" ? (
                        <div className="mt-3 grid gap-2 lg:grid-cols-2">
                            {options.ticket_queues
                                .filter((queue) => accessibleEnabledQueueIds.includes(queue.id))
                                .map((queue) => (
                                    <SelectionCard
                                        key={queue.id}
                                        checked={access.default_ticket_queue_ids.includes(queue.id)}
                                        disabled={!writable}
                                        title={queue.name}
                                        description={queue.brand_name ?? queue.key}
                                        onChange={() =>
                                            setAccess((current) => ({
                                                ...current,
                                                default_ticket_queue_ids: toggleId(
                                                    current.default_ticket_queue_ids,
                                                    queue.id,
                                                ),
                                            }))
                                        }
                                    />
                                ))}
                            {accessibleEnabledQueueIds.length === 0 ? (
                                <p className="text-xs text-slate-600">
                                    No enabled queues are available inside this access scope.
                                </p>
                            ) : null}
                        </div>
                    ) : null}
                </div>
            </Card>

            {!isInvite && staffUser ? (
                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Effective capabilities</h2>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                        Read-only server-authoritative result after combining Groups, direct permissions and superuser status.
                    </p>
                    <div className="mt-4 grid gap-2 lg:grid-cols-2">
                        {staffUser.access.effective_permissions.map((capability) => (
                            <div key={capability.code} className="rounded-lg border border-slate-800 p-3">
                                <div className="flex flex-wrap items-center gap-2">
                                    <p className="text-sm font-medium text-slate-200">{capability.name}</p>
                                    {capability.sensitive ? <Badge variant="warning">Sensitive</Badge> : null}
                                </div>
                                <p className="mt-1 text-xs text-slate-600">{capability.code}</p>
                                <p className="mt-2 text-xs text-slate-500">
                                    {capability.sources.join(" · ") || "No source recorded"}
                                </p>
                            </div>
                        ))}
                        {staffUser.access.effective_permissions.length === 0 ? (
                            <p className="text-sm text-slate-600">No business capabilities are currently effective.</p>
                        ) : null}
                    </div>
                </Card>
            ) : null}

            <div className="flex flex-wrap justify-end gap-2">
                <ButtonLink href="/admin/access" variant="secondary">
                    Cancel
                </ButtonLink>
                {writable ? (
                    <Button type="submit" disabled={isSaving}>
                        {isSaving ? "Saving…" : isInvite ? "Create & send invitation" : "Save access"}
                    </Button>
                ) : null}
            </div>
        </form>
    );
}

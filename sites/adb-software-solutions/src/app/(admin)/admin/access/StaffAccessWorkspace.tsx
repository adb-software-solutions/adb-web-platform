"use client";

import {
    Badge,
    ButtonLink,
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
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { StaffAccessAPI, StaffUserList } from "@/lib/staff-access";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

function formatDateTime(value: string | null): string {
    if (!value) return "Never";
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function StatCard({ label, value, detail }: { label: string; value: number; detail: string }) {
    return (
        <Card className="p-4">
            <p className="text-xs font-semibold tracking-[0.14em] text-slate-500 uppercase">
                {label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-white tabular-nums">{value}</p>
            <p className="mt-1 text-xs text-slate-600">{detail}</p>
        </Card>
    );
}

export function StaffAccessWorkspace() {
    const { hasPermission } = useAuth();
    const canManage = hasPermission("access_control.manage_staff_access");
    const [data, setData] = useState<StaffUserList | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("active");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const query = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: "25",
            status,
        });
        if (search.trim()) params.set("q", search.trim());
        return params.toString();
    }, [page, search, status]);

    const load = useCallback(async () => {
        if (!canManage) {
            setIsLoading(false);
            return;
        }
        try {
            setIsLoading(true);
            setError(null);
            setData((await fetchAPI(StaffAccessAPI.list(query))) as StaffUserList);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load staff access.");
        } finally {
            setIsLoading(false);
        }
    }, [canManage, query]);

    useEffect(() => {
        const timeout = window.setTimeout(() => void load(), 180);
        return () => window.clearTimeout(timeout);
    }, [load]);

    useEffect(() => {
        setPage(1);
    }, [search, status]);

    if (!canManage) {
        return (
            <DataError message="You do not have permission to administer staff users and access." />
        );
    }
    if (isLoading && !data) return <DataLoading label="Loading Users & Access…" />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    const users = data?.items ?? [];

    return (
        <div className="space-y-5">
            <div className="flex justify-end">
                <ButtonLink href="/admin/access/new">Invite staff user</ButtonLink>
            </div>

            {data ? (
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <StatCard
                        label="Active staff"
                        value={data.active_count}
                        detail="Accounts currently able to sign in"
                    />
                    <StatCard
                        label="Inactive staff"
                        value={data.inactive_count}
                        detail="Retained access history, sign-in disabled"
                    />
                    <StatCard
                        label="Current view"
                        value={data.total}
                        detail="Staff matching the current filters"
                    />
                    <StatCard
                        label="Setup pending"
                        value={users.filter((user) => user.setup_pending).length}
                        detail="Visible results still awaiting password setup"
                    />
                </div>
            ) : null}

            <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60">
                <div className="grid gap-3 border-b border-slate-800 p-4 md:grid-cols-[minmax(0,1fr)_220px]">
                    <Input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search staff name or email…"
                        aria-label="Search staff users"
                    />
                    <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                        <option value="active">Active staff</option>
                        <option value="inactive">Inactive staff</option>
                        <option value="all">All staff</option>
                    </Select>
                </div>

                {error ? (
                    <div className="border-b border-slate-800 p-4">
                        <DataError message={error} onRetry={() => void load()} />
                    </div>
                ) : null}

                {users.length === 0 ? (
                    <EmptyState
                        title="No staff match this view"
                        description="Try changing the search or account-status filter."
                    />
                ) : (
                    <Table>
                        <TableHead>
                            <tr>
                                <TableHeaderCell>Staff user</TableHeaderCell>
                                <TableHeaderCell>Access bundles</TableHeaderCell>
                                <TableHeaderCell>Account</TableHeaderCell>
                                <TableHeaderCell>Last login</TableHeaderCell>
                            </tr>
                        </TableHead>
                        <TableBody>
                            {users.map((user) => (
                                <TableRow key={user.id}>
                                    <TableCell>
                                        <Link
                                            href={`/admin/access/users/${user.id}`}
                                            className="font-medium text-slate-100 hover:text-cyan-300"
                                        >
                                            {[user.first_name, user.last_name].filter(Boolean).join(" ") ||
                                                user.email}
                                        </Link>
                                        <p className="mt-1 text-xs text-slate-500">{user.email}</p>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex max-w-xl flex-wrap gap-1.5">
                                            {user.group_names.length ? (
                                                user.group_names.map((group) => (
                                                    <Badge key={group}>{group}</Badge>
                                                ))
                                            ) : (
                                                <span className="text-xs text-slate-600">No group bundles</span>
                                            )}
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="flex flex-wrap gap-1.5">
                                            <Badge variant={user.is_active ? "success" : "neutral"}>
                                                {user.is_active ? "Active" : "Inactive"}
                                            </Badge>
                                            {user.setup_pending ? (
                                                <Badge variant="warning">Setup pending</Badge>
                                            ) : null}
                                            {user.is_superuser ? (
                                                <Badge variant="danger">Superuser</Badge>
                                            ) : null}
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-slate-400">
                                        {formatDateTime(user.last_login)}
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
        </div>
    );
}

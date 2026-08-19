"use client";

import {
    Badge,
    Button,
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
    Textarea,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Ownership = "client" | "internal";
type ContextType = "internal" | "client" | "project" | "task" | "ticket";

interface ClientOption {
    id: number;
    name: string;
}

interface ProjectOption {
    id: number;
    name: string;
    ownership_type: Ownership;
    client_id: number | null;
    client_name: string | null;
}

interface TaskOption {
    id: number;
    title: string;
    ownership_type: Ownership;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
}

interface TicketOption {
    id: number;
    reference: string;
    subject: string;
    client_id: number | null;
    client_name: string | null;
}

interface TimeOptions {
    clients: ClientOption[];
    projects: ProjectOption[];
    tasks: TaskOption[];
    tickets: TicketOption[];
    can_add_time: boolean;
}

interface TimeEntry {
    id: number;
    date: string;
    duration_hours: string;
    description: string;
    billable: boolean;
    entry_type: string;
    ownership_type: Ownership;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    task_id: number | null;
    task_title: string | null;
    ticket_id: number | null;
    ticket_reference: string | null;
    ticket_subject: string | null;
    user_name: string | null;
}

interface TimePage {
    items: TimeEntry[];
    total: number;
    page: number;
    page_size: number;
    tracked_hours: string;
    billable_hours: string;
}

interface RunningTimer {
    id: number;
    started_at: string;
    elapsed_seconds: number;
    description: string;
    billable: boolean;
    ownership_type: Ownership;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    task_id: number | null;
    task_title: string | null;
    ticket_id: number | null;
    ticket_reference: string | null;
    ticket_subject: string | null;
}

interface ContextSelection {
    type: ContextType;
    targetId: number | null;
}

interface ContextPayload {
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
    task_id: number | null;
    ticket_id: number | null;
    internal: boolean;
}

const PAGE_SIZE = 25;
const labelClasses = "space-y-1.5 text-sm font-medium text-slate-300";

function todayValue() {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    return new Date(now.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatHours(value: string | number) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

function formatElapsed(seconds: number) {
    const safeSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(safeSeconds / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const remainder = safeSeconds % 60;
    return [hours, minutes, remainder].map((part) => String(part).padStart(2, "0")).join(":");
}

function resolveContext(selection: ContextSelection, options: TimeOptions): ContextPayload | null {
    if (selection.type === "internal") {
        return {
            ownership_type: "internal",
            client_id: null,
            project_id: null,
            task_id: null,
            ticket_id: null,
            internal: true,
        };
    }

    if (selection.targetId === null) return null;

    if (selection.type === "client") {
        const client = options.clients.find((item) => item.id === selection.targetId);
        if (!client) return null;
        return {
            ownership_type: "client",
            client_id: client.id,
            project_id: null,
            task_id: null,
            ticket_id: null,
            internal: false,
        };
    }

    if (selection.type === "project") {
        const project = options.projects.find((item) => item.id === selection.targetId);
        if (!project) return null;
        return {
            ownership_type: project.ownership_type,
            client_id: project.client_id,
            project_id: project.id,
            task_id: null,
            ticket_id: null,
            internal: project.ownership_type === "internal",
        };
    }

    if (selection.type === "task") {
        const task = options.tasks.find((item) => item.id === selection.targetId);
        if (!task) return null;
        return {
            ownership_type: task.ownership_type,
            client_id: task.client_id,
            project_id: task.project_id,
            task_id: task.id,
            ticket_id: null,
            internal: task.ownership_type === "internal",
        };
    }

    const ticket = options.tickets.find((item) => item.id === selection.targetId);
    if (!ticket) return null;
    return {
        ownership_type: ticket.client_id ? "client" : "internal",
        client_id: ticket.client_id,
        project_id: null,
        task_id: null,
        ticket_id: ticket.id,
        internal: ticket.client_id === null,
    };
}

function contextLabel(entry: TimeEntry | RunningTimer) {
    if (entry.task_title) return entry.task_title;
    if (entry.ticket_reference) return `${entry.ticket_reference}: ${entry.ticket_subject || "Ticket"}`;
    if (entry.project_name) return entry.project_name;
    if (entry.client_name) return entry.client_name;
    return "ADB Internal";
}

function contextLink(entry: TimeEntry) {
    if (entry.task_id) return `/admin/tasks/${entry.task_id}`;
    if (entry.ticket_id) return `/admin/tickets/${entry.ticket_id}`;
    if (entry.project_id) return `/admin/projects/${entry.project_id}`;
    if (entry.client_id) return `/admin/clients/${entry.client_id}`;
    return null;
}

function ContextFields({
    value,
    onChange,
    options,
}: {
    value: ContextSelection;
    onChange: (value: ContextSelection) => void;
    options: TimeOptions;
}) {
    const hasTargets = value.type !== "internal";

    return (
        <div className="grid gap-4 sm:grid-cols-2">
            <label className={labelClasses}>
                <span>Context</span>
                <Select
                    value={value.type}
                    onChange={(event) =>
                        onChange({ type: event.target.value as ContextType, targetId: null })
                    }
                >
                    <option value="internal">ADB internal</option>
                    <option value="client">Client</option>
                    <option value="project">Project</option>
                    <option value="task">Task</option>
                    <option value="ticket">Ticket</option>
                </Select>
            </label>

            {hasTargets ? (
                <label className={labelClasses}>
                    <span>{value.type.charAt(0).toUpperCase() + value.type.slice(1)}</span>
                    <Select
                        value={value.targetId ?? ""}
                        onChange={(event) =>
                            onChange({
                                ...value,
                                targetId: event.target.value ? Number(event.target.value) : null,
                            })
                        }
                        required
                    >
                        <option value="">Select {value.type}</option>
                        {value.type === "client"
                            ? options.clients.map((client) => (
                                  <option key={client.id} value={client.id}>
                                      {client.name}
                                  </option>
                              ))
                            : null}
                        {value.type === "project"
                            ? options.projects.map((project) => (
                                  <option key={project.id} value={project.id}>
                                      {project.name} — {project.client_name || "ADB Internal"}
                                  </option>
                              ))
                            : null}
                        {value.type === "task"
                            ? options.tasks.map((task) => (
                                  <option key={task.id} value={task.id}>
                                      {task.title} — {task.project_name || task.client_name || "ADB Internal"}
                                  </option>
                              ))
                            : null}
                        {value.type === "ticket"
                            ? options.tickets.map((ticket) => (
                                  <option key={ticket.id} value={ticket.id}>
                                      {ticket.reference} — {ticket.subject}
                                  </option>
                              ))
                            : null}
                    </Select>
                </label>
            ) : (
                <div className="rounded-lg border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm text-slate-400">
                    Internal work is kept separate from Clients and is always non-billable.
                </div>
            )}
        </div>
    );
}

export function TimeTrackingWorkspace() {
    const [options, setOptions] = useState<TimeOptions | null>(null);
    const [pageData, setPageData] = useState<TimePage | null>(null);
    const [timer, setTimer] = useState<RunningTimer | null>(null);
    const [page, setPage] = useState(1);
    const [now, setNow] = useState(Date.now());
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [manualContext, setManualContext] = useState<ContextSelection>({
        type: "internal",
        targetId: null,
    });
    const [manualDate, setManualDate] = useState(todayValue());
    const [manualHours, setManualHours] = useState("0");
    const [manualMinutes, setManualMinutes] = useState("30");
    const [manualDescription, setManualDescription] = useState("");
    const [manualBillable, setManualBillable] = useState(false);

    const [timerContext, setTimerContext] = useState<ContextSelection>({
        type: "internal",
        targetId: null,
    });
    const [timerDescription, setTimerDescription] = useState("");
    const [timerBillable, setTimerBillable] = useState(false);

    const query = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
        });
        return params.toString();
    }, [page]);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [loadedOptions, loadedPage, loadedTimer] = await Promise.all([
                fetchAPI(AdminAPI.timeEntries.options()) as Promise<TimeOptions>,
                fetchAPI(AdminAPI.timeEntries.list(query)) as Promise<TimePage>,
                fetchAPI(AdminAPI.timeEntries.timer.current()) as Promise<RunningTimer | null>,
            ]);
            setOptions(loadedOptions);
            setPageData(loadedPage);
            setTimer(loadedTimer);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load time tracking data.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [query]);

    useEffect(() => {
        void load();
    }, [load]);

    useEffect(() => {
        if (!timer) return;
        const interval = window.setInterval(() => setNow(Date.now()), 1000);
        return () => window.clearInterval(interval);
    }, [timer]);

    const manualPayload = options ? resolveContext(manualContext, options) : null;
    const timerPayload = options ? resolveContext(timerContext, options) : null;

    async function addManualEntry(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!manualPayload) {
            setError("Select a valid context before recording time.");
            return;
        }
        const hours = Number(manualHours || 0);
        const minutes = Number(manualMinutes || 0);
        const duration = hours + minutes / 60;
        if (duration <= 0) {
            setError("Tracked time must be greater than zero.");
            return;
        }

        setIsSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.timeEntries.create(), {
                method: "POST",
                body: JSON.stringify({
                    ...manualPayload,
                    date: manualDate,
                    duration_hours: duration.toFixed(4),
                    description: manualDescription,
                    billable: manualPayload.internal ? false : manualBillable,
                }),
            });
            setManualHours("0");
            setManualMinutes("30");
            setManualDescription("");
            setPage(1);
            await load();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to record time.");
        } finally {
            setIsSaving(false);
        }
    }

    async function start(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!timerPayload) {
            setError("Select a valid context before starting the timer.");
            return;
        }
        setIsSaving(true);
        setError(null);
        try {
            const started = (await fetchAPI(AdminAPI.timeEntries.timer.start(), {
                method: "POST",
                body: JSON.stringify({
                    ...timerPayload,
                    description: timerDescription,
                    billable: timerPayload.internal ? false : timerBillable,
                }),
            })) as RunningTimer;
            setTimer(started);
            setNow(Date.now());
        } catch (startError) {
            setError(startError instanceof Error ? startError.message : "Unable to start timer.");
        } finally {
            setIsSaving(false);
        }
    }

    async function stop() {
        setIsSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.timeEntries.timer.stop(), {
                method: "POST",
                body: JSON.stringify({ description: timer?.description ?? null }),
            });
            setTimer(null);
            setTimerDescription("");
            setPage(1);
            await load();
        } catch (stopError) {
            setError(stopError instanceof Error ? stopError.message : "Unable to stop timer.");
        } finally {
            setIsSaving(false);
        }
    }

    async function cancel() {
        setIsSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.timeEntries.timer.cancel(), { method: "POST" });
            setTimer(null);
        } catch (cancelError) {
            setError(cancelError instanceof Error ? cancelError.message : "Unable to cancel timer.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading && !options) return <DataLoading label="Loading time tracking..." />;
    if (error && !options) return <DataError message={error} onRetry={() => void load()} />;
    if (!options) return null;

    const billableHours = Number(pageData?.billable_hours ?? 0);
    const trackedHours = Number(pageData?.tracked_hours ?? 0);
    const elapsed = timer
        ? Math.floor((now - new Date(timer.started_at).getTime()) / 1000)
        : 0;

    return (
        <div className="space-y-6">
            {error ? (
                <div
                    role="alert"
                    className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200"
                >
                    {error}
                </div>
            ) : null}

            {timer ? (
                <Card className="p-6">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                            <div className="text-xs font-medium uppercase tracking-wide text-emerald-400">
                                Timer running
                            </div>
                            <h2 className="mt-1 text-lg font-semibold text-white">
                                {contextLabel(timer)}
                            </h2>
                            <p className="mt-1 text-sm text-slate-400">
                                {timer.description || "No description yet"}
                            </p>
                        </div>
                        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
                            <div className="font-mono text-3xl font-semibold tabular-nums text-white">
                                {formatElapsed(elapsed)}
                            </div>
                            <div className="flex gap-2">
                                <Button disabled={isSaving} onClick={() => void stop()}>
                                    Stop timer
                                </Button>
                                <Button
                                    variant="outline"
                                    disabled={isSaving}
                                    onClick={() => void cancel()}
                                >
                                    Cancel
                                </Button>
                            </div>
                        </div>
                    </div>
                </Card>
            ) : null}

            <div className="grid gap-6 xl:grid-cols-2">
                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Start timer</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        The timer is stored server-side, so it keeps running if you leave this page.
                    </p>
                    <form onSubmit={(event) => void start(event)} className="mt-5 space-y-4">
                        <ContextFields value={timerContext} onChange={setTimerContext} options={options} />
                        <label className={`block ${labelClasses}`}>
                            <span>Description</span>
                            <Textarea
                                value={timerDescription}
                                onChange={(event) => setTimerDescription(event.target.value)}
                                rows={3}
                                placeholder="What are you working on?"
                            />
                        </label>
                        <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={timerPayload?.internal ? false : timerBillable}
                                disabled={timerPayload?.internal ?? false}
                                onChange={(event) => setTimerBillable(event.target.checked)}
                            />
                            Billable
                        </label>
                        <Button type="submit" disabled={isSaving || timer !== null}>
                            Start timer
                        </Button>
                    </form>
                </Card>

                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Add time manually</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Record work completed away from the timer or correct historical time.
                    </p>
                    <form onSubmit={(event) => void addManualEntry(event)} className="mt-5 space-y-4">
                        <ContextFields
                            value={manualContext}
                            onChange={setManualContext}
                            options={options}
                        />
                        <div className="grid gap-4 sm:grid-cols-3">
                            <label className={labelClasses}>
                                <span>Date</span>
                                <Input
                                    type="date"
                                    value={manualDate}
                                    onChange={(event) => setManualDate(event.target.value)}
                                    required
                                />
                            </label>
                            <label className={labelClasses}>
                                <span>Hours</span>
                                <Input
                                    type="number"
                                    min="0"
                                    step="1"
                                    value={manualHours}
                                    onChange={(event) => setManualHours(event.target.value)}
                                    required
                                />
                            </label>
                            <label className={labelClasses}>
                                <span>Minutes</span>
                                <Input
                                    type="number"
                                    min="0"
                                    max="59"
                                    step="1"
                                    value={manualMinutes}
                                    onChange={(event) => setManualMinutes(event.target.value)}
                                    required
                                />
                            </label>
                        </div>
                        <label className={`block ${labelClasses}`}>
                            <span>Description</span>
                            <Textarea
                                value={manualDescription}
                                onChange={(event) => setManualDescription(event.target.value)}
                                rows={3}
                                required
                            />
                        </label>
                        <label className="flex items-center gap-2 text-sm text-slate-300">
                            <input
                                type="checkbox"
                                checked={manualPayload?.internal ? false : manualBillable}
                                disabled={manualPayload?.internal ?? false}
                                onChange={(event) => setManualBillable(event.target.checked)}
                            />
                            Billable
                        </label>
                        <Button type="submit" disabled={isSaving}>
                            Add time
                        </Button>
                    </form>
                </Card>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Tracked</div>
                    <div className="mt-2 text-2xl font-semibold text-white">
                        {formatHours(trackedHours)}
                    </div>
                </Card>
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Billable</div>
                    <div className="mt-2 text-2xl font-semibold text-white">
                        {formatHours(billableHours)}
                    </div>
                </Card>
                <Card className="p-5">
                    <div className="text-xs uppercase tracking-wide text-slate-500">Non-billable</div>
                    <div className="mt-2 text-2xl font-semibold text-white">
                        {formatHours(Math.max(0, trackedHours - billableHours))}
                    </div>
                </Card>
            </div>

            <Card className="overflow-hidden">
                <div className="border-b border-slate-800 px-5 py-4">
                    <h2 className="text-sm font-semibold text-white">Time history</h2>
                </div>
                {isLoading && !pageData ? <DataLoading label="Loading time entries..." /> : null}
                {pageData && pageData.items.length === 0 ? (
                    <EmptyState
                        title="No time recorded yet"
                        description="Manual entries and stopped timers will appear here."
                    />
                ) : null}
                {pageData && pageData.items.length > 0 ? (
                    <>
                        <Table>
                            <TableHead>
                                <tr>
                                    <TableHeaderCell>Date</TableHeaderCell>
                                    <TableHeaderCell>Work</TableHeaderCell>
                                    <TableHeaderCell>Description</TableHeaderCell>
                                    <TableHeaderCell>Staff</TableHeaderCell>
                                    <TableHeaderCell>Type</TableHeaderCell>
                                    <TableHeaderCell>Billing</TableHeaderCell>
                                    <TableHeaderCell className="text-right">Time</TableHeaderCell>
                                </tr>
                            </TableHead>
                            <TableBody>
                                {pageData.items.map((entry) => {
                                    const href = contextLink(entry);
                                    return (
                                        <TableRow key={entry.id}>
                                            <TableCell className="whitespace-nowrap text-slate-400">
                                                {formatDate(entry.date)}
                                            </TableCell>
                                            <TableCell>
                                                {href ? (
                                                    <Link
                                                        href={href}
                                                        className="font-medium text-slate-200 hover:text-adb-cyan-300"
                                                    >
                                                        {contextLabel(entry)}
                                                    </Link>
                                                ) : (
                                                    <span className="font-medium text-slate-200">
                                                        {contextLabel(entry)}
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="max-w-md text-slate-400">
                                                {entry.description || "—"}
                                            </TableCell>
                                            <TableCell className="text-slate-400">
                                                {entry.user_name || "Unknown"}
                                            </TableCell>
                                            <TableCell className="capitalize text-slate-400">
                                                {entry.entry_type}
                                            </TableCell>
                                            <TableCell>
                                                <Badge>
                                                    {entry.billable ? "Billable" : "Non-billable"}
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right font-semibold tabular-nums text-slate-200">
                                                {formatHours(entry.duration_hours)}
                                            </TableCell>
                                        </TableRow>
                                    );
                                })}
                            </TableBody>
                        </Table>
                        <Pagination
                            page={pageData.page}
                            pageSize={pageData.page_size}
                            totalItems={pageData.total}
                            onPageChange={setPage}
                            disabled={isLoading}
                        />
                    </>
                ) : null}
            </Card>
        </div>
    );
}

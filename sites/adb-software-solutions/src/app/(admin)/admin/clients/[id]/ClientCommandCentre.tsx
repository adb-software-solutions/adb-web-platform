"use client";

import { CredentialVault } from "@/app/(admin)/admin/credentials/CredentialVault";
import { KnowledgeBasePanel } from "@/components/admin/KnowledgeBasePanel";
import { MonitoringHealthPanel } from "@/components/admin/MonitoringHealthPanel";
import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Select,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeaderCell,
    TableRow,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ClientInfrastructureWorkspace } from "./infrastructure/ClientInfrastructureWorkspace";

interface Contact {
    id: number;
    name: string;
    email: string;
    phone: string;
    role: string;
    is_active: boolean;
    is_primary: boolean;
    is_billing: boolean;
    is_technical: boolean;
}

interface Project {
    id: number;
    name: string;
    status: string;
    start_date: string;
    end_date: string | null;
    budget: string | null;
}

interface ClientDetail {
    id: number;
    name: string;
    company: string;
    email: string;
    phone: string;
    address: string;
    city: string;
    state: string;
    country: string;
    postal_code: string;
    status: string;
    notes: string;
    contacts: Contact[];
    projects: Project[];
}

interface Capabilities {
    contacts: boolean;
    projects: boolean;
    tasks: boolean;
    tickets: boolean;
    time: boolean;
    infrastructure: boolean;
    credentials: boolean;
    knowledge_base: boolean;
    monitoring: boolean;
    activity: boolean;
}

interface CommandStats {
    active_contacts: number;
    current_projects: number;
    open_tasks: number;
    overdue_tasks: number;
    actionable_tickets: number;
    waiting_customer_tickets: number;
    period_hours: string | number;
    period_billable_hours: string | number;
    current_resources: number;
    active_credentials: number;
    knowledge_documents: number;
    active_monitor_incidents: number;
}

interface CommandProject {
    id: number;
    name: string;
    status: string;
    start_date: string;
    end_date: string | null;
}

interface CommandTask {
    id: number;
    title: string;
    priority: number;
    due_date: string | null;
    status_name: string | null;
    assigned_to_name: string | null;
    project_id: number | null;
    project_name: string | null;
    is_overdue: boolean;
}

interface CommandTicket {
    id: number;
    reference: string;
    subject: string;
    status: string;
    priority: string;
    assigned_to_name: string | null;
    last_message_at: string | null;
    updated_at: string;
}

interface ActivityItem {
    kind: string;
    label: string;
    description: string;
    occurred_at: string;
    href: string;
}

interface CommandCentreData {
    client_id: number;
    period_days: number;
    period_start: string;
    period_end: string;
    capabilities: Capabilities;
    stats: CommandStats;
    projects: CommandProject[];
    tasks: CommandTask[];
    tickets: CommandTicket[];
    activity: ActivityItem[];
}

interface TaskSummary {
    id: number;
    title: string;
    status: string;
    priority: number;
    due_date: string | null;
    completed_at: string | null;
    project_name: string | null;
    assigned_to_name: string | null;
}

interface TaskPage {
    items: TaskSummary[];
    total: number;
    page: number;
    page_size: number;
}

type Section =
    | "overview"
    | "contacts"
    | "projects"
    | "tasks"
    | "tickets"
    | "time"
    | "infrastructure"
    | "credentials"
    | "knowledge"
    | "activity";

type HistoryMode = "current" | "history";
type Presentation = "page" | "drawer";

const CURRENT_PROJECT_STATUSES = new Set(["planning", "active", "paused"]);
const PERIODS = [7, 30, 90, 365] as const;

function pretty(value: string): string {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string | null): string {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(value));
}

function formatDateTime(value: string): string {
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function hours(value: string | number): string {
    return `${Number(value).toFixed(2)}h`;
}

function priorityLabel(priority: number): string {
    return ["Low", "Normal", "High", "Urgent"][priority] ?? "Normal";
}

function StatCard({ label, value, note }: { label: string; value: string | number; note?: string }) {
    return (
        <Card className="p-4">
            <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
            {note ? <p className="mt-1 text-xs text-slate-600">{note}</p> : null}
        </Card>
    );
}

function PanelHeader({
    title,
    description,
    action,
}: {
    title: string;
    description: string;
    action?: React.ReactNode;
}) {
    return (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 className="text-sm font-semibold text-white">{title}</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
            </div>
            {action}
        </div>
    );
}

function SegmentToggle({ value, onChange }: { value: HistoryMode; onChange: (value: HistoryMode) => void }) {
    return (
        <div className="inline-flex rounded-lg border border-slate-800 bg-slate-950 p-1 text-xs">
            {(["current", "history"] as const).map((mode) => (
                <button
                    key={mode}
                    type="button"
                    onClick={() => onChange(mode)}
                    className={`rounded-md px-3 py-1.5 transition ${
                        value === mode
                            ? "bg-slate-800 text-white"
                            : "text-slate-500 hover:text-slate-300"
                    }`}
                >
                    {mode === "current" ? "Current" : "History"}
                </button>
            ))}
        </div>
    );
}

export function ClientCommandCentre({
    clientId,
    initialSection = "overview",
    initialPeriodDays = 30,
    presentation = "page",
}: {
    clientId: number;
    initialSection?: Section;
    initialPeriodDays?: number;
    presentation?: Presentation;
}) {
    const { hasPermission } = useAuth();
    const router = useRouter();
    const pathname = usePathname();
    const [client, setClient] = useState<ClientDetail | null>(null);
    const [command, setCommand] = useState<CommandCentreData | null>(null);
    const [section, setSection] = useState<Section>(initialSection);
    const [periodDays, setPeriodDays] = useState(
        PERIODS.includes(initialPeriodDays as (typeof PERIODS)[number]) ? initialPeriodDays : 30,
    );
    const [projectMode, setProjectMode] = useState<HistoryMode>("current");
    const [taskMode, setTaskMode] = useState<HistoryMode>("current");
    const [tasks, setTasks] = useState<TaskPage | null>(null);
    const [showInactiveContacts, setShowInactiveContacts] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingTasks, setIsLoadingTasks] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [nextClient, nextCommand] = await Promise.all([
                fetchAPI(AdminAPI.clients.get(clientId)) as Promise<ClientDetail>,
                fetchAPI(
                    `${API_URL}/api/admin/clients/${clientId}/command-centre?period_days=${periodDays}`,
                ) as Promise<CommandCentreData>,
            ]);
            setClient(nextClient);
            setCommand(nextCommand);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load the Client Command Centre.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [clientId, periodDays]);

    useEffect(() => {
        void load();
    }, [load]);

    useEffect(() => {
        if (section !== "tasks" || !command?.capabilities.tasks) return;
        void (async () => {
            try {
                setIsLoadingTasks(true);
                const params = new URLSearchParams({
                    client_id: String(clientId),
                    ownership_type: "client",
                    completed: taskMode === "history" ? "true" : "false",
                    page: "1",
                    page_size: "100",
                });
                setTasks((await fetchAPI(AdminAPI.tasks.list(params.toString()))) as TaskPage);
            } catch (taskError) {
                setError(taskError instanceof Error ? taskError.message : "Unable to load client tasks.");
            } finally {
                setIsLoadingTasks(false);
            }
        })();
    }, [clientId, command?.capabilities.tasks, section, taskMode]);

    const navigate = useCallback(
        (nextSection: Section, nextPeriod = periodDays) => {
            setSection(nextSection);
            if (presentation === "drawer") return;
            const params = new URLSearchParams({
                section: nextSection,
                period_days: String(nextPeriod),
            });
            router.replace(`${pathname}?${params.toString()}`, { scroll: false });
        },
        [pathname, periodDays, presentation, router],
    );

    const changePeriod = (value: number) => {
        setPeriodDays(value);
        if (presentation === "drawer") return;
        const params = new URLSearchParams({ section, period_days: String(value) });
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    };

    const navItems = useMemo(() => {
        if (!command) return [];
        const items: { id: Section; label: string; visible: boolean; count?: number }[] = [
            { id: "overview", label: "Overview", visible: true },
            {
                id: "contacts",
                label: "Contacts",
                visible: command.capabilities.contacts,
                count: command.stats.active_contacts,
            },
            {
                id: "projects",
                label: "Projects",
                visible: command.capabilities.projects,
                count: command.stats.current_projects,
            },
            {
                id: "tasks",
                label: "Tasks",
                visible: command.capabilities.tasks,
                count: command.stats.open_tasks,
            },
            {
                id: "tickets",
                label: "Tickets",
                visible: command.capabilities.tickets,
                count: command.stats.actionable_tickets,
            },
            { id: "time", label: "Time", visible: command.capabilities.time },
            {
                id: "infrastructure",
                label: "Infrastructure",
                visible: command.capabilities.infrastructure,
                count: command.stats.current_resources,
            },
            {
                id: "credentials",
                label: "Credentials",
                visible: command.capabilities.credentials,
                count: command.stats.active_credentials,
            },
            {
                id: "knowledge",
                label: "Knowledge",
                visible: command.capabilities.knowledge_base,
                count: command.stats.knowledge_documents,
            },
            { id: "activity", label: "Activity", visible: command.capabilities.activity },
        ];
        return items.filter((item) => item.visible);
    }, [command]);

    useEffect(() => {
        if (!command || navItems.some((item) => item.id === section)) return;
        navigate("overview");
    }, [command, navItems, navigate, section]);

    if (isLoading && (!client || !command)) return <DataLoading label="Loading Client Command Centre…" />;
    if (error && (!client || !command)) {
        return <DataError message={error} onRetry={() => void load()} />;
    }
    if (!client || !command) return <DataError message="Client Command Centre is unavailable." />;

    const location = [client.address, client.city, client.state, client.postal_code, client.country]
        .filter(Boolean)
        .join(", ");
    const activeContacts = client.contacts.filter((contact) => contact.is_active);
    const inactiveContacts = client.contacts.filter((contact) => !contact.is_active);
    const visibleContacts = showInactiveContacts ? client.contacts : activeContacts;
    const currentProjects = client.projects.filter((project) => CURRENT_PROJECT_STATUSES.has(project.status));
    const historicalProjects = client.projects.filter(
        (project) => !CURRENT_PROJECT_STATUSES.has(project.status),
    );
    const visibleProjects = projectMode === "current" ? currentProjects : historicalProjects;

    const canEditClient = hasPermission("clients.change_client");
    const canAddContact = hasPermission("clients.add_clientcontact");
    const canAddProject = hasPermission("clients.add_project");
    const canAddTask = hasPermission("tasks.add_task");
    const canAddKnowledge = hasPermission("knowledge_base.add_knowledgebasedocument");

    return (
        <div className="space-y-6">
            {error ? <DataError message={error} onRetry={() => void load()} /> : null}

            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    {presentation === "page" ? (
                        <Link href="/admin/clients" className="text-xs text-slate-500 hover:text-slate-300">
                            ← Clients
                        </Link>
                    ) : null}
                    <div className={`${presentation === "page" ? "mt-2 " : ""}flex flex-wrap items-center gap-3`}>
                        <h1 className="text-2xl font-semibold text-white">{client.company || client.name}</h1>
                        <Badge>{client.status}</Badge>
                    </div>
                    {client.company && client.name ? (
                        <p className="mt-1 text-sm text-slate-400">Primary account contact: {client.name}</p>
                    ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                    <a
                        href={`mailto:${client.email}`}
                        className="inline-flex h-9 items-center rounded-lg border border-slate-700 px-3 text-sm text-slate-300 hover:bg-slate-900"
                    >
                        Email
                    </a>
                    {client.phone ? (
                        <a
                            href={`tel:${client.phone}`}
                            className="inline-flex h-9 items-center rounded-lg border border-slate-700 px-3 text-sm text-slate-300 hover:bg-slate-900"
                        >
                            Call
                        </a>
                    ) : null}
                    {canEditClient ? (
                        <ButtonLink href={`/admin/clients/${client.id}/edit`} variant="secondary">
                            Edit client
                        </ButtonLink>
                    ) : null}
                </div>
            </div>

            <Card className="overflow-x-auto p-2">
                <nav className="flex min-w-max gap-1" aria-label="Client sections">
                    {navItems.map((item) => (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => navigate(item.id)}
                            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                                section === item.id
                                    ? "bg-cyan-500/10 text-cyan-200"
                                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                            }`}
                        >
                            {item.label}
                            {item.count !== undefined ? (
                                <span className="rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                                    {item.count}
                                </span>
                            ) : null}
                        </button>
                    ))}
                </nav>
            </Card>

            {section === "overview" ? (
                <div className="space-y-6">
                    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {command.capabilities.tickets ? (
                            <StatCard
                                label="Actionable tickets"
                                value={command.stats.actionable_tickets}
                                note={`${command.stats.waiting_customer_tickets} waiting on customer`}
                            />
                        ) : null}
                        {command.capabilities.tasks ? (
                            <StatCard
                                label="Open tasks"
                                value={command.stats.open_tasks}
                                note={`${command.stats.overdue_tasks} overdue`}
                            />
                        ) : null}
                        {command.capabilities.projects ? (
                            <StatCard label="Current projects" value={command.stats.current_projects} />
                        ) : null}
                        {command.capabilities.time ? (
                            <StatCard
                                label={`${command.period_days}-day time`}
                                value={hours(command.stats.period_hours)}
                                note={`${hours(command.stats.period_billable_hours)} billable`}
                            />
                        ) : null}
                        {command.capabilities.infrastructure ? (
                            <StatCard
                                label="Current resources"
                                value={command.stats.current_resources}
                                note={
                                    command.capabilities.monitoring
                                        ? `${command.stats.active_monitor_incidents} active monitoring incidents`
                                        : undefined
                                }
                            />
                        ) : null}
                        {command.capabilities.credentials ? (
                            <StatCard label="Active credentials" value={command.stats.active_credentials} />
                        ) : null}
                        {command.capabilities.knowledge_base ? (
                            <StatCard label="Knowledge documents" value={command.stats.knowledge_documents} />
                        ) : null}
                        {command.capabilities.contacts ? (
                            <StatCard label="Active contacts" value={command.stats.active_contacts} />
                        ) : null}
                    </div>

                    <div className="grid gap-6 xl:grid-cols-2">
                        {command.capabilities.tasks ? (
                            <Card className="p-5">
                                <PanelHeader
                                    title="Work needing attention"
                                    description="Open client tasks, with overdue work surfaced first."
                                    action={
                                        <Button type="button" size="sm" variant="ghost" onClick={() => navigate("tasks")}>
                                            View tasks
                                        </Button>
                                    }
                                />
                                {command.tasks.length === 0 ? (
                                    <EmptyState title="No open tasks" description="There is no current client work in the task queue." />
                                ) : (
                                    <div className="space-y-2">
                                        {command.tasks.slice(0, 5).map((task) => (
                                            <Link
                                                key={task.id}
                                                href={`/admin/tasks/${task.id}`}
                                                className="block rounded-lg border border-slate-800 p-3 hover:border-slate-700 hover:bg-slate-900/60"
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-medium text-slate-200">{task.title}</p>
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            {task.project_name ?? "Client task"}
                                                            {task.assigned_to_name ? ` · ${task.assigned_to_name}` : ""}
                                                        </p>
                                                    </div>
                                                    {task.is_overdue ? <Badge variant="danger">Overdue</Badge> : null}
                                                </div>
                                            </Link>
                                        ))}
                                    </div>
                                )}
                            </Card>
                        ) : null}

                        {command.capabilities.tickets ? (
                            <Card className="p-5">
                                <PanelHeader
                                    title="Current conversations"
                                    description="Active client tickets visible through your Ticket Queue scope."
                                    action={
                                        <Button type="button" size="sm" variant="ghost" onClick={() => navigate("tickets")}>
                                            View tickets
                                        </Button>
                                    }
                                />
                                {command.tickets.length === 0 ? (
                                    <EmptyState title="No active tickets" description="There are no current conversations waiting in your accessible queues." />
                                ) : (
                                    <div className="space-y-2">
                                        {command.tickets.slice(0, 5).map((ticket) => (
                                            <Link
                                                key={ticket.id}
                                                href={`/admin/tickets/${ticket.id}`}
                                                className="block rounded-lg border border-slate-800 p-3 hover:border-slate-700 hover:bg-slate-900/60"
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div>
                                                        <p className="text-sm font-medium text-slate-200">{ticket.subject}</p>
                                                        <p className="mt-1 text-xs text-slate-500">
                                                            {ticket.reference}
                                                            {ticket.assigned_to_name ? ` · ${ticket.assigned_to_name}` : ""}
                                                        </p>
                                                    </div>
                                                    <Badge>{pretty(ticket.status)}</Badge>
                                                </div>
                                            </Link>
                                        ))}
                                    </div>
                                )}
                            </Card>
                        ) : null}
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.6fr)]">
                        <Card className="p-5">
                            <PanelHeader title="Account" description="Core account details and internal context." />
                            <dl className="grid gap-4 text-sm sm:grid-cols-2">
                                <div>
                                    <dt className="text-xs text-slate-500">Email</dt>
                                    <dd className="mt-1 text-slate-300">{client.email}</dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-slate-500">Phone</dt>
                                    <dd className="mt-1 text-slate-300">{client.phone || "—"}</dd>
                                </div>
                                <div className="sm:col-span-2">
                                    <dt className="text-xs text-slate-500">Address</dt>
                                    <dd className="mt-1 text-slate-300">{location || "—"}</dd>
                                </div>
                            </dl>
                        </Card>
                        <Card className="p-5">
                            <PanelHeader title="Notes" description="Internal client-account notes." />
                            <p className="whitespace-pre-wrap text-sm leading-6 text-slate-400">
                                {client.notes || "No account notes recorded."}
                            </p>
                        </Card>
                    </div>

                    {command.capabilities.activity ? (
                        <Card className="p-5">
                            <PanelHeader
                                title="Recent activity"
                                description="Safe recent metadata changes across this client's visible operational domains."
                                action={
                                    <Button type="button" size="sm" variant="ghost" onClick={() => navigate("activity")}>
                                        View activity
                                    </Button>
                                }
                            />
                            <div className="space-y-2">
                                {command.activity.slice(0, 6).map((item, index) => (
                                    <Link
                                        key={`${item.kind}-${item.occurred_at}-${index}`}
                                        href={item.href}
                                        className="flex flex-col gap-1 rounded-lg px-3 py-2 hover:bg-slate-900 sm:flex-row sm:items-center sm:justify-between"
                                    >
                                        <div>
                                            <p className="text-sm text-slate-300">{item.label}</p>
                                            <p className="text-xs text-slate-500">{item.description}</p>
                                        </div>
                                        <span className="text-xs text-slate-600">{formatDateTime(item.occurred_at)}</span>
                                    </Link>
                                ))}
                            </div>
                        </Card>
                    ) : null}
                </div>
            ) : null}

            {section === "contacts" && command.capabilities.contacts ? (
                <Card className="p-5">
                    <PanelHeader
                        title="Contacts"
                        description="Active account contacts are shown first; inactive people remain available as history."
                        action={
                            <div className="flex gap-2">
                                {inactiveContacts.length ? (
                                    <Button
                                        type="button"
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => setShowInactiveContacts((value) => !value)}
                                    >
                                        {showInactiveContacts ? "Hide inactive" : `Show inactive (${inactiveContacts.length})`}
                                    </Button>
                                ) : null}
                                {canAddContact ? (
                                    <ButtonLink size="sm" href={`/admin/clients/${client.id}/contacts/new`}>
                                        Add contact
                                    </ButtonLink>
                                ) : null}
                            </div>
                        }
                    />
                    {visibleContacts.length === 0 ? (
                        <EmptyState title="No active contacts" description="Add a contact or show inactive contacts." />
                    ) : (
                        <Table>
                            <TableHead>
                                <tr>
                                    <TableHeaderCell>Name</TableHeaderCell>
                                    <TableHeaderCell>Role</TableHeaderCell>
                                    <TableHeaderCell>Contact</TableHeaderCell>
                                    <TableHeaderCell>Responsibilities</TableHeaderCell>
                                </tr>
                            </TableHead>
                            <TableBody>
                                {visibleContacts.map((contact) => (
                                    <TableRow key={contact.id}>
                                        <TableCell>
                                            <Link
                                                href={`/admin/clients/${client.id}/contacts/${contact.id}`}
                                                className="font-medium text-slate-200 hover:text-cyan-300"
                                            >
                                                {contact.name}
                                            </Link>
                                            {!contact.is_active ? <p className="text-xs text-slate-600">Inactive</p> : null}
                                        </TableCell>
                                        <TableCell className="text-slate-400">{contact.role || "—"}</TableCell>
                                        <TableCell>
                                            <a href={`mailto:${contact.email}`} className="text-slate-300 hover:text-cyan-300">
                                                {contact.email}
                                            </a>
                                            <p className="mt-1 text-xs text-slate-500">{contact.phone || "—"}</p>
                                        </TableCell>
                                        <TableCell className="text-xs text-slate-400">
                                            {[
                                                contact.is_primary && "Primary",
                                                contact.is_billing && "Billing",
                                                contact.is_technical && "Technical",
                                            ]
                                                .filter(Boolean)
                                                .join(" · ") || "—"}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </Card>
            ) : null}

            {section === "projects" && command.capabilities.projects ? (
                <Card className="p-5">
                    <PanelHeader
                        title="Projects"
                        description="Planning, active and paused work is current; completed and archived delivery stays in history."
                        action={
                            <div className="flex flex-wrap gap-2">
                                <SegmentToggle value={projectMode} onChange={setProjectMode} />
                                {canAddProject ? (
                                    <ButtonLink size="sm" href={`/admin/projects/new?client_id=${client.id}`}>
                                        New project
                                    </ButtonLink>
                                ) : null}
                            </div>
                        }
                    />
                    {visibleProjects.length === 0 ? (
                        <EmptyState
                            title={projectMode === "current" ? "No current projects" : "No project history"}
                            description="There are no projects in this view."
                        />
                    ) : (
                        <Table>
                            <TableHead>
                                <tr>
                                    <TableHeaderCell>Project</TableHeaderCell>
                                    <TableHeaderCell>Status</TableHeaderCell>
                                    <TableHeaderCell>Start</TableHeaderCell>
                                    <TableHeaderCell>End</TableHeaderCell>
                                    <TableHeaderCell>Budget</TableHeaderCell>
                                </tr>
                            </TableHead>
                            <TableBody>
                                {visibleProjects.map((project) => (
                                    <TableRow key={project.id}>
                                        <TableCell>
                                            <Link href={`/admin/projects/${project.id}`} className="font-medium text-slate-200 hover:text-cyan-300">
                                                {project.name}
                                            </Link>
                                        </TableCell>
                                        <TableCell><Badge>{pretty(project.status)}</Badge></TableCell>
                                        <TableCell className="text-slate-400">{formatDate(project.start_date)}</TableCell>
                                        <TableCell className="text-slate-400">{formatDate(project.end_date)}</TableCell>
                                        <TableCell className="text-slate-400">
                                            {project.budget ? `£${Number(project.budget).toLocaleString("en-GB")}` : "—"}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </Card>
            ) : null}

            {section === "tasks" && command.capabilities.tasks ? (
                <Card className="p-5">
                    <PanelHeader
                        title="Tasks"
                        description="Open client work is current; completed tasks remain available as history."
                        action={
                            <div className="flex flex-wrap gap-2">
                                <SegmentToggle value={taskMode} onChange={setTaskMode} />
                                {canAddTask ? (
                                    <ButtonLink size="sm" href={`/admin/tasks/new?client_id=${client.id}`}>
                                        New task
                                    </ButtonLink>
                                ) : null}
                            </div>
                        }
                    />
                    {isLoadingTasks ? <DataLoading label="Loading client tasks…" /> : null}
                    {!isLoadingTasks && tasks?.items.length === 0 ? (
                        <EmptyState
                            title={taskMode === "current" ? "No open tasks" : "No completed tasks"}
                            description="There are no client tasks in this view."
                        />
                    ) : null}
                    {!isLoadingTasks && tasks?.items.length ? (
                        <div className="space-y-2">
                            {tasks.items.map((task) => (
                                <Link
                                    key={task.id}
                                    href={`/admin/tasks/${task.id}`}
                                    className="flex flex-col gap-2 rounded-lg border border-slate-800 p-3 hover:border-slate-700 hover:bg-slate-900/60 sm:flex-row sm:items-center sm:justify-between"
                                >
                                    <div>
                                        <p className="text-sm font-medium text-slate-200">{task.title}</p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {task.project_name ?? "Client task"}
                                            {task.assigned_to_name ? ` · ${task.assigned_to_name}` : ""}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-slate-500">
                                        <span>{priorityLabel(task.priority)}</span>
                                        <span>·</span>
                                        <span>{task.due_date ? formatDate(task.due_date) : "No due date"}</span>
                                        <Badge>{taskMode === "history" ? "Completed" : task.status}</Badge>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    ) : null}
                </Card>
            ) : null}

            {section === "tickets" && command.capabilities.tickets ? (
                <Card className="p-5">
                    <PanelHeader
                        title="Tickets"
                        description="Current conversations are restricted to the Ticket Queues you can access. Resolved and closed history remains in the full Ticket workspace."
                        action={
                            <ButtonLink size="sm" variant="secondary" href={`/admin/tickets?client_id=${client.id}`}>
                                Full ticket history
                            </ButtonLink>
                        }
                    />
                    {command.tickets.length === 0 ? (
                        <EmptyState title="No active tickets" description="No current client conversations are visible in your queues." />
                    ) : (
                        <Table>
                            <TableHead>
                                <tr>
                                    <TableHeaderCell>Ticket</TableHeaderCell>
                                    <TableHeaderCell>Status</TableHeaderCell>
                                    <TableHeaderCell>Priority</TableHeaderCell>
                                    <TableHeaderCell>Assignee</TableHeaderCell>
                                    <TableHeaderCell>Last message</TableHeaderCell>
                                </tr>
                            </TableHead>
                            <TableBody>
                                {command.tickets.map((ticket) => (
                                    <TableRow key={ticket.id}>
                                        <TableCell>
                                            <Link href={`/admin/tickets/${ticket.id}`} className="font-medium text-slate-200 hover:text-cyan-300">
                                                {ticket.subject}
                                            </Link>
                                            <p className="mt-1 text-xs text-slate-600">{ticket.reference}</p>
                                        </TableCell>
                                        <TableCell><Badge>{pretty(ticket.status)}</Badge></TableCell>
                                        <TableCell className="text-slate-400">{pretty(ticket.priority)}</TableCell>
                                        <TableCell className="text-slate-400">{ticket.assigned_to_name ?? "Unassigned"}</TableCell>
                                        <TableCell className="text-slate-400">
                                            {ticket.last_message_at ? formatDateTime(ticket.last_message_at) : "—"}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </Card>
            ) : null}

            {section === "time" && command.capabilities.time ? (
                <div className="space-y-6">
                    <Card className="p-5">
                        <PanelHeader
                            title="Time"
                            description="Tracked and billable time for this client in the selected period."
                            action={
                                <Select
                                    aria-label="Time period"
                                    value={String(periodDays)}
                                    onChange={(event) => changePeriod(Number(event.target.value))}
                                >
                                    <option value="7">Last 7 days</option>
                                    <option value="30">Last 30 days</option>
                                    <option value="90">Last 90 days</option>
                                    <option value="365">Last 365 days</option>
                                </Select>
                            }
                        />
                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                            <StatCard label="Tracked" value={hours(command.stats.period_hours)} />
                            <StatCard label="Billable" value={hours(command.stats.period_billable_hours)} />
                            <StatCard label="Period start" value={formatDate(command.period_start)} />
                            <StatCard label="Period end" value={formatDate(command.period_end)} />
                        </div>
                        <div className="mt-5 flex justify-end">
                            <ButtonLink href={`/admin/time-tracking?client_id=${client.id}`} variant="secondary">
                                Open Time Tracking
                            </ButtonLink>
                        </div>
                    </Card>
                </div>
            ) : null}

            {section === "infrastructure" && command.capabilities.infrastructure ? (
                <div className="space-y-6">
                    <ClientInfrastructureWorkspace clientId={client.id} presentation="embedded" />
                    {command.capabilities.monitoring ? (
                        <MonitoringHealthPanel
                            clientId={client.id}
                            title="Client technical health"
                            description="Current monitoring state for infrastructure owned by this client."
                        />
                    ) : null}
                </div>
            ) : null}

            {section === "credentials" && command.capabilities.credentials ? (
                <CredentialVault initialClientId={client.id} compact />
            ) : null}

            {section === "knowledge" && command.capabilities.knowledge_base ? (
                <div className="space-y-4">
                    {canAddKnowledge ? (
                        <div className="flex justify-end">
                            <ButtonLink href={`/admin/knowledge-base/documents/new?client_id=${client.id}`}>
                                Add document
                            </ButtonLink>
                        </div>
                    ) : null}
                    <KnowledgeBasePanel
                        clientId={client.id}
                        title="Client knowledge"
                        description="Current runbooks and documentation owned by this client."
                    />
                </div>
            ) : null}

            {section === "activity" && command.capabilities.activity ? (
                <Card className="p-5">
                    <PanelHeader
                        title="Activity"
                        description="Recent safe metadata activity across the client account and operational domains you can access."
                    />
                    {command.activity.length === 0 ? (
                        <EmptyState title="No recent activity" description="No activity is available in your visible client context yet." />
                    ) : (
                        <div className="divide-y divide-slate-800">
                            {command.activity.map((item, index) => (
                                <Link
                                    key={`${item.kind}-${item.occurred_at}-${index}`}
                                    href={item.href}
                                    className="flex flex-col gap-2 py-4 hover:bg-slate-900/40 sm:flex-row sm:items-start sm:justify-between sm:px-2"
                                >
                                    <div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <Badge>{pretty(item.kind)}</Badge>
                                            <p className="text-sm font-medium text-slate-200">{item.label}</p>
                                        </div>
                                        <p className="mt-1 text-xs text-slate-500">{item.description}</p>
                                    </div>
                                    <span className="text-xs text-slate-600">{formatDateTime(item.occurred_at)}</span>
                                </Link>
                            ))}
                        </div>
                    )}
                </Card>
            ) : null}
        </div>
    );
}

"use client";

import { Badge, ButtonLink, Card, DataError, DataLoading } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ProjectActivityPanels } from "./ProjectActivityPanels";
import { ProjectTaskWorkspaceView } from "./ProjectTaskWorkspaceView";
import { ProjectTimelineWorkspace } from "./ProjectTimelineWorkspace";
import { ProjectTimeWorkspace } from "./ProjectTimeWorkspace";

type ProjectTab = "overview" | "work" | "timeline" | "time";

interface ProjectDetail {
    id: number;
    name: string;
    description: string;
    status: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    start_date: string;
    end_date: string | null;
    budget: string | null;
    hourly_rate: string | null;
    created_at: string;
    updated_at: string;
    task_count: number;
    open_task_count: number;
    time_entry_count: number;
    tracked_hours: string;
    billable_hours: string;
    can_change: boolean;
}

const tabs: Array<{ value: ProjectTab; label: string; description: string }> = [
    { value: "work", label: "Work", description: "List and board views" },
    { value: "timeline", label: "Timeline", description: "Schedule and dependencies" },
    { value: "overview", label: "Overview", description: "Project context and activity" },
    { value: "time", label: "Time", description: "Tracked delivery time" },
];

function statusClasses(status: string) {
    if (status === "active") {
        return "border-emerald-900/70 bg-emerald-950/50 text-emerald-300";
    }
    if (status === "paused") {
        return "border-amber-900/70 bg-amber-950/40 text-amber-300";
    }
    if (status === "completed") {
        return "border-cyan-900/70 bg-cyan-950/40 text-cyan-300";
    }
    if (status === "planning") {
        return "border-indigo-900/70 bg-indigo-950/40 text-indigo-300";
    }
    return "border-slate-700 bg-slate-900 text-slate-400";
}

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

function formatMoney(value: string | null) {
    if (!value) return "—";
    return new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
    }).format(Number(value));
}

function formatHours(value: string) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

export function ProjectWorkspace({ projectId }: { projectId: number }) {
    const [project, setProject] = useState<ProjectDetail | null>(null);
    const [tab, setTab] = useState<ProjectTab>("work");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const loadProject = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const data = (await fetchAPI(AdminAPI.projects.get(projectId))) as ProjectDetail;
            setProject(data);
        } catch (loadError) {
            setError(
                loadError instanceof Error ? loadError.message : "Unable to load project details.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        const stored = window.localStorage.getItem(`project-tab:${projectId}`);
        if (
            stored === "overview" ||
            stored === "work" ||
            stored === "timeline" ||
            stored === "time"
        ) {
            setTab(stored);
        }
        void loadProject();
    }, [loadProject, projectId]);

    function changeTab(next: ProjectTab) {
        setTab(next);
        window.localStorage.setItem(`project-tab:${projectId}`, next);
    }

    if (isLoading) return <DataLoading label="Loading project..." />;
    if (error || !project) {
        return (
            <DataError
                message={error || "Project could not be loaded."}
                onRetry={() => void loadProject()}
            />
        );
    }

    return (
        <div className="space-y-6">
            <header className="space-y-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                        <Link
                            href="/admin/projects"
                            className="text-xs text-slate-500 hover:text-slate-300"
                        >
                            ← Projects
                        </Link>
                        <div className="mt-2 flex flex-wrap items-center gap-3">
                            <h1 className="truncate text-2xl font-semibold text-white">{project.name}</h1>
                            <Badge className={statusClasses(project.status)}>{project.status}</Badge>
                            <Badge>
                                {project.ownership_type === "internal" ? "Internal" : "Client"}
                            </Badge>
                        </div>
                        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
                            <span>{project.client_name || "ADB Internal"}</span>
                            <span>·</span>
                            <span>{project.open_task_count} open tasks</span>
                            <span>·</span>
                            <span>{formatHours(project.tracked_hours)} tracked</span>
                            {project.end_date ? (
                                <>
                                    <span>·</span>
                                    <span>Due {formatDate(project.end_date)}</span>
                                </>
                            ) : null}
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <ButtonLink href={`/admin/tasks/new?project_id=${project.id}`}>
                            Add task
                        </ButtonLink>
                        <ButtonLink
                            href={`/admin/time-tracking?project_id=${project.id}&mode=timer#record-time`}
                            variant="outline"
                        >
                            Track time
                        </ButtonLink>
                        {project.client_id ? (
                            <ButtonLink href={`/admin/clients/${project.client_id}`} variant="ghost">
                                Client
                            </ButtonLink>
                        ) : null}
                        {project.can_change ? (
                            <ButtonLink href={`/admin/projects/${project.id}/edit`} variant="ghost">
                                Settings
                            </ButtonLink>
                        ) : null}
                    </div>
                </div>

                <nav className="flex gap-1 overflow-x-auto border-b border-slate-800" aria-label="Project views">
                    {tabs.map((item) => (
                        <button
                            key={item.value}
                            type="button"
                            onClick={() => changeTab(item.value)}
                            className={`min-w-fit border-b-2 px-4 py-3 text-left transition ${
                                tab === item.value
                                    ? "border-adb-cyan-400 text-white"
                                    : "border-transparent text-slate-500 hover:border-slate-700 hover:text-slate-300"
                            }`}
                        >
                            <div className="text-sm font-medium">{item.label}</div>
                            <div className="mt-0.5 text-[11px] text-slate-600">{item.description}</div>
                        </button>
                    ))}
                </nav>
            </header>

            {tab === "work" ? <ProjectTaskWorkspaceView projectId={project.id} /> : null}

            {tab === "timeline" ? <ProjectTimelineWorkspace projectId={project.id} /> : null}

            {tab === "time" ? <ProjectTimeWorkspace projectId={project.id} /> : null}

            {tab === "overview" ? (
                <div className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Open tasks</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {project.open_task_count}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                                {project.task_count} total project tasks
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Tracked time</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {formatHours(project.tracked_hours)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                                {project.time_entry_count} time entries
                            </div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Billable time</div>
                            <div className="mt-2 text-2xl font-semibold text-white">
                                {formatHours(project.billable_hours)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">Recorded billable hours</div>
                        </Card>
                        <Card className="p-5">
                            <div className="text-xs uppercase tracking-wide text-slate-500">Schedule</div>
                            <div className="mt-2 text-sm font-semibold text-white">
                                {formatDate(project.start_date)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                                to {formatDate(project.end_date)}
                            </div>
                        </Card>
                    </div>

                    <ProjectActivityPanels projectId={project.id} />

                    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
                        <Card className="p-5">
                            <h2 className="text-sm font-semibold text-white">Project brief</h2>
                            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                                {project.description || "No project description has been recorded yet."}
                            </p>
                        </Card>

                        <Card className="p-5">
                            <h2 className="text-sm font-semibold text-white">Project details</h2>
                            <dl className="mt-4 space-y-4 text-sm">
                                <div>
                                    <dt className="text-xs text-slate-500">Owner</dt>
                                    <dd className="mt-1 text-slate-300">
                                        {project.client_name || "ADB Internal"}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-slate-500">Budget</dt>
                                    <dd className="mt-1 text-slate-300">{formatMoney(project.budget)}</dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-slate-500">Hourly rate</dt>
                                    <dd className="mt-1 text-slate-300">
                                        {formatMoney(project.hourly_rate)}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-slate-500">Created</dt>
                                    <dd className="mt-1 text-slate-300">
                                        {formatDateTime(project.created_at)}
                                    </dd>
                                </div>
                                <div>
                                    <dt className="text-xs text-slate-500">Last updated</dt>
                                    <dd className="mt-1 text-slate-300">
                                        {formatDateTime(project.updated_at)}
                                    </dd>
                                </div>
                            </dl>
                        </Card>
                    </div>
                </div>
            ) : null}
        </div>
    );
}

"use client";

import { Badge, ButtonLink, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface ProjectTask {
    id: number;
    title: string;
    status: string;
    priority: number;
    due_date: string | null;
    assigned_to_name: string | null;
    recurrence_frequency: string;
}

interface TaskPage {
    items: ProjectTask[];
    total: number;
}

interface ProjectTimeEntry {
    id: number;
    date: string;
    duration_hours: string;
    description: string;
    billable: boolean;
    task_id: number | null;
    task_title: string | null;
    user_name: string | null;
}

interface TimePage {
    items: ProjectTimeEntry[];
    total: number;
    tracked_hours: string;
    billable_hours: string;
}

const priorityLabels: Record<number, string> = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Critical",
};

function formatDate(value: string | null) {
    if (!value) return "No due date";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatHours(value: string) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

export function ProjectActivityPanels({ projectId }: { projectId: number }) {
    const [tasks, setTasks] = useState<TaskPage | null>(null);
    const [time, setTime] = useState<TimePage | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const taskQuery = new URLSearchParams({
                project_id: String(projectId),
                completed: "false",
                page_size: "8",
            });
            const timeQuery = new URLSearchParams({
                project_id: String(projectId),
                page_size: "8",
            });
            const [taskData, timeData] = await Promise.all([
                fetchAPI(AdminAPI.tasks.list(taskQuery.toString())) as Promise<TaskPage>,
                fetchAPI(AdminAPI.timeEntries.list(timeQuery.toString())) as Promise<TimePage>,
            ]);
            setTasks(taskData);
            setTime(timeData);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load project work activity.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        void load();
    }, [load]);

    if (isLoading) return <DataLoading label="Loading project tasks and time..." />;
    if (error) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <div className="grid gap-6 xl:grid-cols-2">
            <Card className="overflow-hidden">
                <div className="flex items-center justify-between gap-4 border-b border-slate-800 px-5 py-4">
                    <div>
                        <h2 className="text-sm font-semibold text-white">Open tasks</h2>
                        <p className="mt-1 text-xs text-slate-500">
                            {tasks?.total ?? 0} open task{tasks?.total === 1 ? "" : "s"} on this project
                        </p>
                    </div>
                    <ButtonLink href={`/admin/tasks/new?project_id=${projectId}`}>Add task</ButtonLink>
                </div>
                {!tasks || tasks.items.length === 0 ? (
                    <EmptyState
                        title="No open project tasks"
                        description="Add a task to start planning the work for this project."
                    />
                ) : (
                    <div className="divide-y divide-slate-800">
                        {tasks.items.map((task) => (
                            <Link
                                key={task.id}
                                href={`/admin/tasks/${task.id}`}
                                className="flex items-start justify-between gap-4 px-5 py-4 hover:bg-slate-900/60"
                            >
                                <div className="min-w-0">
                                    <div className="font-medium text-slate-200">{task.title}</div>
                                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                                        <span>{task.assigned_to_name || "Unassigned"}</span>
                                        <span>{formatDate(task.due_date)}</span>
                                        {task.recurrence_frequency !== "none" ? (
                                            <span className="capitalize">
                                                {task.recurrence_frequency} recurring
                                            </span>
                                        ) : null}
                                    </div>
                                </div>
                                <div className="flex shrink-0 flex-col items-end gap-2">
                                    <Badge>{task.status}</Badge>
                                    <span className="text-xs text-slate-500">
                                        {priorityLabels[task.priority] || "Unknown"}
                                    </span>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </Card>

            <Card className="overflow-hidden">
                <div className="border-b border-slate-800 px-5 py-4">
                    <h2 className="text-sm font-semibold text-white">Recent time</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        {formatHours(time?.tracked_hours ?? "0")} tracked · {formatHours(
                            time?.billable_hours ?? "0",
                        )} billable
                    </p>
                </div>
                {!time || time.items.length === 0 ? (
                    <EmptyState
                        title="No project time recorded"
                        description="Manual entries and stopped timers for this project will appear here."
                    />
                ) : (
                    <div className="divide-y divide-slate-800">
                        {time.items.map((entry) => (
                            <div key={entry.id} className="flex items-start justify-between gap-4 px-5 py-4">
                                <div className="min-w-0">
                                    <div className="text-sm font-medium text-slate-200">
                                        {entry.description || entry.task_title || "Project work"}
                                    </div>
                                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                                        <span>{formatDate(entry.date)}</span>
                                        <span>{entry.user_name || "Unknown staff"}</span>
                                        {entry.task_id ? (
                                            <Link
                                                href={`/admin/tasks/${entry.task_id}`}
                                                className="hover:text-adb-cyan-300"
                                            >
                                                {entry.task_title || "Task"}
                                            </Link>
                                        ) : null}
                                    </div>
                                </div>
                                <div className="shrink-0 text-right">
                                    <div className="font-semibold tabular-nums text-slate-200">
                                        {formatHours(entry.duration_hours)}
                                    </div>
                                    <div className="mt-1 text-xs text-slate-500">
                                        {entry.billable ? "Billable" : "Non-billable"}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>
        </div>
    );
}

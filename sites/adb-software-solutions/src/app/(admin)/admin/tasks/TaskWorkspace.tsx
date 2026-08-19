"use client";

import { Badge, Button, ButtonLink, Card, DataError, DataLoading } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface TaskDetail {
    id: number;
    title: string;
    description: string;
    status: string;
    priority: number;
    due_date: string | null;
    completed_at: string | null;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    task_list_name: string | null;
    assigned_to_name: string | null;
    recurrence_frequency: string;
    previous_occurrence_id: number | null;
    next_occurrence_id: number | null;
    created_by_name: string | null;
    created_at: string;
    updated_at: string;
    can_change: boolean;
    can_complete: boolean;
    can_reopen: boolean;
}

const priorityLabels: Record<number, string> = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Critical",
};

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value: string | null) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

export function TaskWorkspace({ taskId }: { taskId: number }) {
    const [task, setTask] = useState<TaskDetail | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isChanging, setIsChanging] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadTask = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const data = (await fetchAPI(AdminAPI.tasks.get(taskId))) as TaskDetail;
            setTask(data);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task details.");
        } finally {
            setIsLoading(false);
        }
    }, [taskId]);

    useEffect(() => {
        void loadTask();
    }, [loadTask]);

    async function changeCompletion(action: "complete" | "reopen") {
        setIsChanging(true);
        setError(null);
        try {
            const data = (await fetchAPI(
                action === "complete" ? AdminAPI.tasks.complete(taskId) : AdminAPI.tasks.reopen(taskId),
                { method: "POST" },
            )) as TaskDetail;
            setTask(data);
        } catch (changeError) {
            setError(changeError instanceof Error ? changeError.message : "Unable to update the task.");
        } finally {
            setIsChanging(false);
        }
    }

    if (isLoading) return <DataLoading label="Loading task..." />;
    if (error && !task) {
        return <DataError message={error} onRetry={() => void loadTask()} />;
    }
    if (!task) return <DataError message="Task could not be loaded." onRetry={() => void loadTask()} />;

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

            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <Link href="/admin/tasks" className="text-xs text-slate-500 hover:text-slate-300">
                        ← Tasks
                    </Link>
                    <div className="mt-2 flex flex-wrap items-center gap-3">
                        <h1 className="text-2xl font-semibold text-white">{task.title}</h1>
                        <Badge>{task.status}</Badge>
                        <Badge>{priorityLabels[task.priority] ?? "Unknown"}</Badge>
                        {task.completed_at ? <Badge>Completed</Badge> : null}
                    </div>
                    <p className="mt-1 text-sm text-slate-400">
                        {task.project_name || task.client_name || "ADB Internal"}
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {task.can_complete ? (
                        <Button disabled={isChanging} onClick={() => void changeCompletion("complete")}>
                            {isChanging ? "Updating..." : "Complete task"}
                        </Button>
                    ) : null}
                    {task.can_reopen ? (
                        <Button
                            variant="secondary"
                            disabled={isChanging}
                            onClick={() => void changeCompletion("reopen")}
                        >
                            {isChanging ? "Updating..." : "Reopen task"}
                        </Button>
                    ) : null}
                    {task.can_change && !task.completed_at ? (
                        <ButtonLink href={`/admin/tasks/${task.id}/edit`} variant="secondary">
                            Edit task
                        </ButtonLink>
                    ) : null}
                </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
                <Card className="p-5 lg:col-span-2">
                    <h2 className="text-sm font-semibold text-white">Task details</h2>
                    <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                        <div>
                            <dt className="text-xs text-slate-500">Ownership</dt>
                            <dd className="mt-1 text-slate-300">
                                {task.ownership_type === "internal" ? "ADB Internal" : task.client_name}
                            </dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Assigned to</dt>
                            <dd className="mt-1 text-slate-300">{task.assigned_to_name || "Unassigned"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Project</dt>
                            <dd className="mt-1 text-slate-300">
                                {task.project_id ? (
                                    <Link
                                        href={`/admin/projects/${task.project_id}`}
                                        className="hover:text-adb-cyan-300"
                                    >
                                        {task.project_name}
                                    </Link>
                                ) : (
                                    "No project"
                                )}
                            </dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Task list</dt>
                            <dd className="mt-1 text-slate-300">{task.task_list_name || "No task list"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Due date</dt>
                            <dd className="mt-1 text-slate-300">{formatDate(task.due_date)}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Recurrence</dt>
                            <dd className="mt-1 capitalize text-slate-300">
                                {task.recurrence_frequency === "none"
                                    ? "Does not repeat"
                                    : task.recurrence_frequency}
                            </dd>
                        </div>
                    </dl>
                </Card>

                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Record</h2>
                    <dl className="mt-4 space-y-4 text-sm">
                        <div>
                            <dt className="text-xs text-slate-500">Created by</dt>
                            <dd className="mt-1 text-slate-300">{task.created_by_name || "System"}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Created</dt>
                            <dd className="mt-1 text-slate-300">{formatDateTime(task.created_at)}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Last updated</dt>
                            <dd className="mt-1 text-slate-300">{formatDateTime(task.updated_at)}</dd>
                        </div>
                        <div>
                            <dt className="text-xs text-slate-500">Completed</dt>
                            <dd className="mt-1 text-slate-300">{formatDateTime(task.completed_at)}</dd>
                        </div>
                    </dl>
                </Card>
            </div>

            <Card className="p-5">
                <h2 className="text-sm font-semibold text-white">Description</h2>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                    {task.description || "No task description has been recorded yet."}
                </p>
            </Card>

            {task.previous_occurrence_id || task.next_occurrence_id ? (
                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Recurring history</h2>
                    <div className="mt-3 flex flex-wrap gap-3 text-sm">
                        {task.previous_occurrence_id ? (
                            <ButtonLink
                                href={`/admin/tasks/${task.previous_occurrence_id}`}
                                variant="outline"
                            >
                                Previous occurrence
                            </ButtonLink>
                        ) : null}
                        {task.next_occurrence_id ? (
                            <ButtonLink
                                href={`/admin/tasks/${task.next_occurrence_id}`}
                                variant="outline"
                            >
                                Next occurrence
                            </ButtonLink>
                        ) : null}
                    </div>
                </Card>
            ) : null}
        </div>
    );
}

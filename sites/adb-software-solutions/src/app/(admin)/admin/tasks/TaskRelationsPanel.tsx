"use client";

import { Badge, Button, Card, DataError, DataLoading, EmptyState, Input, Select } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

interface RelationTask {
    id: number;
    title: string;
    status: string;
    completed: boolean;
    assigned_to_name: string | null;
    due_date: string | null;
    subtask_count: number;
    blocked_by_count: number;
}

interface Relations {
    task_id: number;
    subtasks: RelationTask[];
    blocked_by: RelationTask[];
    blocking: RelationTask[];
    can_change: boolean;
    can_add_subtask: boolean;
}

interface TaskOption {
    id: number;
    title: string;
    completed_at: string | null;
    client_name: string | null;
    project_name: string | null;
}

interface TaskPage {
    items: TaskOption[];
}

function formatDate(value: string | null) {
    if (!value) return null;
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
    }).format(new Date(`${value}T00:00:00`));
}

export function TaskRelationsPanel({ taskId }: { taskId: number }) {
    const [relations, setRelations] = useState<Relations | null>(null);
    const [availableTasks, setAvailableTasks] = useState<TaskOption[]>([]);
    const [subtaskTitle, setSubtaskTitle] = useState("");
    const [blockingTaskId, setBlockingTaskId] = useState<number | null>(null);
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const [relationData, taskData] = await Promise.all([
                fetchAPI(AdminAPI.tasks.relations(taskId)) as Promise<Relations>,
                fetchAPI(AdminAPI.tasks.list("page_size=100&completed=false")) as Promise<TaskPage>,
            ]);
            setRelations(relationData);
            setAvailableTasks(taskData.items);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task relationships.");
        } finally {
            setLoading(false);
        }
    }, [taskId]);

    useEffect(() => {
        void load();
    }, [load]);

    const dependencyOptions = useMemo(() => {
        const existing = new Set(relations?.blocked_by.map((task) => task.id) ?? []);
        return availableTasks.filter((task) => task.id !== taskId && !existing.has(task.id));
    }, [availableTasks, relations, taskId]);

    async function addSubtask(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!subtaskTitle.trim()) return;
        setSaving(true);
        try {
            await fetchAPI(AdminAPI.tasks.subtasks(taskId), {
                method: "POST",
                body: JSON.stringify({ title: subtaskTitle.trim() }),
            });
            setSubtaskTitle("");
            await load();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to add subtask.");
        } finally {
            setSaving(false);
        }
    }

    async function addDependency(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!blockingTaskId) return;
        setSaving(true);
        try {
            await fetchAPI(AdminAPI.tasks.dependencies(taskId), {
                method: "POST",
                body: JSON.stringify({ blocking_task_id: blockingTaskId }),
            });
            setBlockingTaskId(null);
            await load();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to add dependency.");
        } finally {
            setSaving(false);
        }
    }

    async function removeDependency(blockerId: number) {
        setSaving(true);
        try {
            await fetchAPI(AdminAPI.tasks.removeDependency(taskId, blockerId), { method: "DELETE" });
            await load();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to remove dependency.");
        } finally {
            setSaving(false);
        }
    }

    if (loading && !relations) return <DataLoading label="Loading subtasks and dependencies..." />;
    if (error && !relations) return <DataError message={error} onRetry={() => void load()} />;
    if (!relations) return null;

    return (
        <div className="grid gap-6 xl:grid-cols-2">
            {error ? (
                <div className="xl:col-span-2 rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <Card className="overflow-hidden">
                <div className="border-b border-slate-800 px-5 py-4">
                    <div className="flex items-center justify-between gap-3">
                        <h2 className="text-sm font-semibold text-white">Subtasks</h2>
                        <span className="text-xs text-slate-500">{relations.subtasks.length}</span>
                    </div>
                </div>
                {relations.subtasks.length ? (
                    <div className="divide-y divide-slate-800">
                        {relations.subtasks.map((task) => (
                            <Link
                                key={task.id}
                                href={`/admin/tasks/${task.id}`}
                                className="flex items-start justify-between gap-4 px-5 py-4 transition hover:bg-slate-900/60"
                            >
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-sm font-medium ${task.completed ? "text-slate-500 line-through" : "text-slate-200"}`}>
                                            {task.title}
                                        </span>
                                        {task.blocked_by_count ? <Badge>Blocked</Badge> : null}
                                    </div>
                                    <div className="mt-1 text-xs text-slate-600">
                                        {task.assigned_to_name || "Unassigned"}
                                        {task.due_date ? ` · ${formatDate(task.due_date)}` : ""}
                                    </div>
                                </div>
                                <span className="shrink-0 text-xs text-slate-500">{task.status}</span>
                            </Link>
                        ))}
                    </div>
                ) : (
                    <EmptyState
                        title="No subtasks yet"
                        description="Break larger work down without losing the parent task context."
                    />
                )}
                {relations.can_add_subtask ? (
                    <form onSubmit={(event) => void addSubtask(event)} className="flex gap-2 border-t border-slate-800 bg-slate-950/40 p-4">
                        <Input
                            value={subtaskTitle}
                            onChange={(event) => setSubtaskTitle(event.target.value)}
                            placeholder="Add a subtask..."
                        />
                        <Button type="submit" variant="outline" disabled={saving || !subtaskTitle.trim()}>
                            Add
                        </Button>
                    </form>
                ) : null}
            </Card>

            <Card className="overflow-hidden">
                <div className="border-b border-slate-800 px-5 py-4">
                    <h2 className="text-sm font-semibold text-white">Dependencies</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        Make blocking relationships explicit so project planning and timelines can use them.
                    </p>
                </div>
                <div className="grid gap-5 p-5 md:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                    <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Blocked by</h3>
                        {relations.blocked_by.length ? (
                            <div className="mt-3 space-y-2">
                                {relations.blocked_by.map((task) => (
                                    <div key={task.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
                                        <Link
                                            href={`/admin/tasks/${task.id}`}
                                            className="min-w-0 truncate text-sm text-slate-300 hover:text-adb-cyan-300"
                                        >
                                            {task.title}
                                        </Link>
                                        {relations.can_change ? (
                                            <button
                                                type="button"
                                                disabled={saving}
                                                onClick={() => void removeDependency(task.id)}
                                                className="shrink-0 text-xs text-slate-600 hover:text-red-300"
                                            >
                                                Remove
                                            </button>
                                        ) : null}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-3 text-sm text-slate-600">Nothing currently blocks this task.</p>
                        )}
                    </div>
                    <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Blocking</h3>
                        {relations.blocking.length ? (
                            <div className="mt-3 space-y-2">
                                {relations.blocking.map((task) => (
                                    <Link
                                        key={task.id}
                                        href={`/admin/tasks/${task.id}`}
                                        className="block rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-sm text-slate-300 hover:border-slate-700 hover:text-adb-cyan-300"
                                    >
                                        {task.title}
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-3 text-sm text-slate-600">This task is not blocking anything else.</p>
                        )}
                    </div>
                </div>
                {relations.can_change ? (
                    <form onSubmit={(event) => void addDependency(event)} className="flex gap-2 border-t border-slate-800 bg-slate-950/40 p-4">
                        <Select
                            value={blockingTaskId ?? ""}
                            onChange={(event) => setBlockingTaskId(event.target.value ? Number(event.target.value) : null)}
                        >
                            <option value="">Select a blocking task...</option>
                            {dependencyOptions.map((task) => (
                                <option key={task.id} value={task.id}>
                                    {task.title} — {task.project_name || task.client_name || "ADB Internal"}
                                </option>
                            ))}
                        </Select>
                        <Button type="submit" variant="outline" disabled={saving || !blockingTaskId}>
                            Add dependency
                        </Button>
                    </form>
                ) : null}
            </Card>
        </div>
    );
}

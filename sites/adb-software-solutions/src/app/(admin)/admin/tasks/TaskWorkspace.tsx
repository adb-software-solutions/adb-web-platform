"use client";

import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    Input,
    Select,
    Textarea,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface TaskDetail {
    id: number;
    title: string;
    description: string;
    status: string;
    status_id: number | null;
    priority: number;
    start_date: string | null;
    due_date: string | null;
    completed_at: string | null;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    task_list_id: number | null;
    task_list_name: string | null;
    assigned_to_id: string | null;
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

interface StaffOption {
    id: string;
    name: string;
    email: string;
}

interface TaskOptions {
    staff: StaffOption[];
}

interface QuickUpdate {
    title?: string;
    description?: string;
    priority?: number;
    start_date?: string | null;
    due_date?: string | null;
    assigned_to_id?: string | null;
}

const priorityLabels: Record<number, string> = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Critical",
};

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

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

export function TaskWorkspace({
    taskId,
    presentation = "page",
    onClose,
    onChanged,
}: {
    taskId: number;
    presentation?: "page" | "drawer";
    onClose?: () => void;
    onChanged?: () => void;
}) {
    const { hasPermission } = useAuth();
    const [task, setTask] = useState<TaskDetail | null>(null);
    const [options, setOptions] = useState<TaskOptions | null>(null);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isChanging, setIsChanging] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function syncDraft(data: TaskDetail) {
        setTitle(data.title);
        setDescription(data.description);
    }

    const loadTask = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const data = (await fetchAPI(AdminAPI.tasks.get(taskId))) as TaskDetail;
            setTask(data);
            syncDraft(data);
            if (data.can_change) {
                try {
                    setOptions((await fetchAPI(AdminAPI.tasks.options())) as TaskOptions);
                } catch {
                    setOptions(null);
                }
            }
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task details.");
        } finally {
            setIsLoading(false);
        }
    }, [taskId]);

    useEffect(() => {
        void loadTask();
    }, [loadTask]);

    async function quickUpdate(payload: QuickUpdate) {
        if (!task?.can_change || task.completed_at) return;
        setIsSaving(true);
        setError(null);
        try {
            const data = (await fetchAPI(`${API_URL}/api/admin/tasks/${task.id}/quick-update`, {
                method: "PATCH",
                body: JSON.stringify(payload),
            })) as TaskDetail;
            setTask(data);
            syncDraft(data);
            onChanged?.();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to update the task.");
            syncDraft(task);
        } finally {
            setIsSaving(false);
        }
    }

    async function changeCompletion(action: "complete" | "reopen") {
        setIsChanging(true);
        setError(null);
        try {
            const data = (await fetchAPI(
                action === "complete" ? AdminAPI.tasks.complete(taskId) : AdminAPI.tasks.reopen(taskId),
                { method: "POST" },
            )) as TaskDetail;
            setTask(data);
            syncDraft(data);
            onChanged?.();
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

    const editable = task.can_change && !task.completed_at;
    const canAddTime = hasPermission("clients.add_timeentry");

    return (
        <div className={presentation === "drawer" ? "space-y-5" : "space-y-6"}>
            {error ? (
                <div
                    role="alert"
                    className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200"
                >
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                    {presentation === "page" ? (
                        <Link href="/admin/tasks" className="text-xs text-slate-500 hover:text-slate-300">
                            ← My tasks
                        </Link>
                    ) : null}
                    <div className={presentation === "page" ? "mt-3 flex gap-3" : "flex gap-3"}>
                        {task.can_complete ? (
                            <Button
                                type="button"
                                variant="ghost"
                                disabled={isChanging}
                                onClick={() => void changeCompletion("complete")}
                                className="mt-1 h-8 w-8 shrink-0 rounded-full border border-slate-700 p-0 text-transparent hover:border-emerald-500 hover:bg-emerald-500/10 hover:text-emerald-300"
                                aria-label="Mark task complete"
                                title="Mark complete"
                            >
                                ✓
                            </Button>
                        ) : (
                            <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-emerald-900/60 bg-emerald-950/30 text-sm text-emerald-400">
                                ✓
                            </span>
                        )}
                        <div className="min-w-0 flex-1">
                            {editable ? (
                                <Input
                                    value={title}
                                    onChange={(event) => setTitle(event.target.value)}
                                    onBlur={() => {
                                        if (title.trim() && title.trim() !== task.title) {
                                            void quickUpdate({ title: title.trim() });
                                        }
                                    }}
                                    className="h-auto border-transparent bg-transparent px-0 py-0 text-2xl font-semibold text-white focus:border-transparent focus:ring-0"
                                    aria-label="Task title"
                                />
                            ) : (
                                <h1
                                    className={`text-2xl font-semibold ${
                                        task.completed_at ? "text-slate-500 line-through" : "text-white"
                                    }`}
                                >
                                    {task.title}
                                </h1>
                            )}
                            <div className="mt-2 flex flex-wrap items-center gap-2">
                                <Badge>{task.status}</Badge>
                                {task.completed_at ? <Badge>Completed</Badge> : null}
                                <span className="text-sm text-slate-500">
                                    {task.project_name || task.client_name || "ADB Internal"}
                                </span>
                                {isSaving ? <span className="text-xs text-slate-600">Saving…</span> : null}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex flex-wrap gap-2">
                    {canAddTime ? (
                        <ButtonLink
                            href={`/admin/time-tracking?task_id=${task.id}&mode=manual#record-time`}
                            variant="outline"
                        >
                            Add time
                        </ButtonLink>
                    ) : null}
                    {task.can_reopen ? (
                        <Button
                            variant="secondary"
                            disabled={isChanging}
                            onClick={() => void changeCompletion("reopen")}
                        >
                            Reopen
                        </Button>
                    ) : null}
                    {editable ? (
                        <ButtonLink href={`/admin/tasks/${task.id}/edit`} variant="outline">
                            More fields
                        </ButtonLink>
                    ) : null}
                    {presentation === "drawer" ? (
                        <>
                            <ButtonLink href={`/admin/tasks/${task.id}`} variant="ghost">
                                Open full page
                            </ButtonLink>
                            {onClose ? (
                                <Button type="button" variant="ghost" onClick={onClose} aria-label="Close task">
                                    ×
                                </Button>
                            ) : null}
                        </>
                    ) : null}
                </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
                <div className="space-y-6">
                    <Card className="p-5">
                        <div className="flex items-center justify-between gap-3">
                            <h2 className="text-sm font-semibold text-white">Description</h2>
                            {editable ? (
                                <span className="text-xs text-slate-600">
                                    Autosaves when you leave the field
                                </span>
                            ) : null}
                        </div>
                        {editable ? (
                            <Textarea
                                value={description}
                                onChange={(event) => setDescription(event.target.value)}
                                onBlur={() => {
                                    if (description !== task.description) {
                                        void quickUpdate({ description });
                                    }
                                }}
                                rows={10}
                                placeholder="Add task details, notes, acceptance criteria or links..."
                                className="mt-4 min-h-56"
                            />
                        ) : (
                            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                                {task.description || "No task description has been recorded yet."}
                            </p>
                        )}
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

                    <div className="text-xs text-slate-700">
                        Created by {task.created_by_name || "System"} · {formatDateTime(task.created_at)} · Last updated {formatDateTime(task.updated_at)}
                    </div>
                </div>

                <Card className="h-fit overflow-hidden xl:sticky xl:top-6">
                    <div className="border-b border-slate-800 px-5 py-4">
                        <h2 className="text-sm font-semibold text-white">Task details</h2>
                    </div>
                    <div className="space-y-5 p-5">
                        <label className="block space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Assigned to</span>
                            {editable && options ? (
                                <Select
                                    value={task.assigned_to_id ?? ""}
                                    disabled={isSaving}
                                    onChange={(event) =>
                                        void quickUpdate({ assigned_to_id: event.target.value || null })
                                    }
                                >
                                    <option value="">Unassigned</option>
                                    {options.staff.map((staff) => (
                                        <option key={staff.id} value={staff.id}>
                                            {staff.name}
                                        </option>
                                    ))}
                                </Select>
                            ) : (
                                <div className="text-sm text-slate-300">
                                    {task.assigned_to_name || "Unassigned"}
                                </div>
                            )}
                        </label>

                        <label className="block space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Priority</span>
                            {editable ? (
                                <Select
                                    value={task.priority}
                                    disabled={isSaving}
                                    onChange={(event) =>
                                        void quickUpdate({ priority: Number(event.target.value) })
                                    }
                                >
                                    {Object.entries(priorityLabels).map(([value, label]) => (
                                        <option key={value} value={value}>
                                            {label}
                                        </option>
                                    ))}
                                </Select>
                            ) : (
                                <div className="text-sm text-slate-300">
                                    {priorityLabels[task.priority] ?? "Unknown"}
                                </div>
                            )}
                        </label>

                        <label className="block space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Start date</span>
                            {editable ? (
                                <Input
                                    type="date"
                                    value={task.start_date ?? ""}
                                    disabled={isSaving}
                                    onChange={(event) =>
                                        void quickUpdate({ start_date: event.target.value || null })
                                    }
                                />
                            ) : (
                                <div className="text-sm text-slate-300">
                                    {task.start_date ? formatDate(task.start_date) : "No start date"}
                                </div>
                            )}
                        </label>

                        <label className="block space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Due date</span>
                            {editable ? (
                                <Input
                                    type="date"
                                    value={task.due_date ?? ""}
                                    disabled={isSaving}
                                    onChange={(event) =>
                                        void quickUpdate({ due_date: event.target.value || null })
                                    }
                                />
                            ) : (
                                <div className="text-sm text-slate-300">
                                    {task.due_date ? formatDate(task.due_date) : "No due date"}
                                </div>
                            )}
                        </label>

                        <div>
                            <div className="text-xs font-medium text-slate-500">Status</div>
                            <div className="mt-1.5 text-sm text-slate-300">{task.status}</div>
                        </div>

                        <div>
                            <div className="text-xs font-medium text-slate-500">Project</div>
                            <div className="mt-1.5 text-sm text-slate-300">
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
                            </div>
                        </div>

                        <div>
                            <div className="text-xs font-medium text-slate-500">Task list</div>
                            <div className="mt-1.5 text-sm text-slate-300">
                                {task.task_list_id ? (
                                    <Link
                                        href={`/admin/task-lists/${task.task_list_id}`}
                                        className="hover:text-adb-cyan-300"
                                    >
                                        {task.task_list_name}
                                    </Link>
                                ) : (
                                    "No task list"
                                )}
                            </div>
                        </div>

                        <div>
                            <div className="text-xs font-medium text-slate-500">Recurrence</div>
                            <div className="mt-1.5 text-sm capitalize text-slate-300">
                                {task.recurrence_frequency === "none"
                                    ? "Does not repeat"
                                    : task.recurrence_frequency}
                            </div>
                        </div>

                        <div>
                            <div className="text-xs font-medium text-slate-500">Ownership</div>
                            <div className="mt-1.5 text-sm text-slate-300">
                                {task.ownership_type === "internal" ? "ADB Internal" : task.client_name}
                            </div>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}

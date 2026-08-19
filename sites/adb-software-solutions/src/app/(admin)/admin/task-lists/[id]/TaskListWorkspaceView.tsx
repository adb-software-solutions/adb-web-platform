"use client";

import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { DragEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type ViewMode = "list" | "board" | "timeline";

interface WorkspaceTask {
    id: number;
    title: string;
    status: string;
    priority: number;
    start_date: string | null;
    due_date: string | null;
    completed: boolean;
    assigned_to_name: string | null;
    section_id: number | null;
    parent_task_id: number | null;
    sort_order: string;
    subtask_count: number;
    blocked_by_count: number;
}

interface WorkspaceSection {
    id: number;
    name: string;
    sort_order: string;
    tasks: WorkspaceTask[];
}

interface Workspace {
    id: number;
    name: string;
    description: string;
    ownership_type: "client" | "internal";
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    sections: WorkspaceSection[];
    unsectioned_tasks: WorkspaceTask[];
    total_tasks: number;
    open_tasks: number;
    can_change: boolean;
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
    }).format(new Date(`${value}T00:00:00`));
}

function allTopLevelTasks(workspace: Workspace) {
    return [
        ...workspace.unsectioned_tasks,
        ...workspace.sections.flatMap((section) => section.tasks),
    ];
}

function TaskMeta({ task }: { task: WorkspaceTask }) {
    return (
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
            <span>{task.assigned_to_name || "Unassigned"}</span>
            {task.due_date ? <span>Due {formatDate(task.due_date)}</span> : null}
            {task.subtask_count ? <span>{task.subtask_count} subtasks</span> : null}
            {task.blocked_by_count ? <span>{task.blocked_by_count} blockers</span> : null}
        </div>
    );
}

function QuickAdd({
    taskListId,
    sectionId,
    onCreated,
}: {
    taskListId: number;
    sectionId: number | null;
    onCreated: () => Promise<void>;
}) {
    const [title, setTitle] = useState("");
    const [saving, setSaving] = useState(false);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!title.trim()) return;
        setSaving(true);
        try {
            await fetchAPI(AdminAPI.tasks.lists.quickTask(taskListId), {
                method: "POST",
                body: JSON.stringify({ title: title.trim(), section_id: sectionId }),
            });
            setTitle("");
            await onCreated();
        } finally {
            setSaving(false);
        }
    }

    return (
        <form onSubmit={(event) => void submit(event)} className="flex gap-2">
            <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Add task..."
                className="h-9"
            />
            <Button type="submit" variant="outline" disabled={saving || !title.trim()}>
                Add
            </Button>
        </form>
    );
}

export function TaskListWorkspaceView({ taskListId }: { taskListId: number }) {
    const [workspace, setWorkspace] = useState<Workspace | null>(null);
    const [view, setView] = useState<ViewMode>("list");
    const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);
    const [newSectionName, setNewSectionName] = useState("");
    const [creatingSection, setCreatingSection] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            setWorkspace(
                (await fetchAPI(AdminAPI.tasks.lists.workspace(taskListId))) as Workspace,
            );
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task list.");
        } finally {
            setLoading(false);
        }
    }, [taskListId]);

    useEffect(() => {
        const stored = window.localStorage.getItem(`task-list-view:${taskListId}`) as ViewMode | null;
        if (stored === "list" || stored === "board" || stored === "timeline") setView(stored);
        void load();
    }, [load, taskListId]);

    function changeView(next: ViewMode) {
        setView(next);
        window.localStorage.setItem(`task-list-view:${taskListId}`, next);
    }

    async function createSection(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!newSectionName.trim()) return;
        setCreatingSection(true);
        try {
            await fetchAPI(AdminAPI.tasks.lists.sections(taskListId), {
                method: "POST",
                body: JSON.stringify({ name: newSectionName.trim() }),
            });
            setNewSectionName("");
            await load();
        } catch (createError) {
            setError(createError instanceof Error ? createError.message : "Unable to add section.");
        } finally {
            setCreatingSection(false);
        }
    }

    async function moveTask(
        taskId: number,
        sectionId: number | null,
        beforeTaskId: number | null,
        afterTaskId: number | null,
    ) {
        if (!workspace) return;
        try {
            await fetchAPI(AdminAPI.tasks.move(taskId), {
                method: "POST",
                body: JSON.stringify({
                    task_list_id: workspace.id,
                    section_id: sectionId,
                    before_task_id: beforeTaskId,
                    after_task_id: afterTaskId,
                }),
            });
            await load();
        } catch (moveError) {
            setError(moveError instanceof Error ? moveError.message : "Unable to move task.");
        } finally {
            setDraggedTaskId(null);
        }
    }

    function handleDragStart(event: DragEvent, taskId: number) {
        setDraggedTaskId(taskId);
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(taskId));
    }

    function taskIdFromDrop(event: DragEvent) {
        event.preventDefault();
        return Number(event.dataTransfer.getData("text/plain") || draggedTaskId || 0);
    }

    async function dropAtEnd(event: DragEvent, sectionId: number | null, tasks: WorkspaceTask[]) {
        const taskId = taskIdFromDrop(event);
        if (!taskId) return;
        const remaining = tasks.filter((task) => task.id !== taskId);
        const previous = remaining.at(-1)?.id ?? null;
        await moveTask(taskId, sectionId, previous, null);
    }

    async function dropBefore(
        event: DragEvent,
        sectionId: number | null,
        tasks: WorkspaceTask[],
        targetId: number,
    ) {
        event.stopPropagation();
        const taskId = taskIdFromDrop(event);
        if (!taskId || taskId === targetId) return;
        const remaining = tasks.filter((task) => task.id !== taskId);
        const index = remaining.findIndex((task) => task.id === targetId);
        const previous = index > 0 ? remaining[index - 1].id : null;
        await moveTask(taskId, sectionId, previous, targetId);
    }

    const timeline = useMemo(() => {
        if (!workspace) return null;
        const tasks = allTopLevelTasks(workspace).filter((task) => task.start_date || task.due_date);
        if (!tasks.length) return null;
        const dates = tasks.flatMap((task) => [task.start_date, task.due_date]).filter(Boolean) as string[];
        const timestamps = dates.map((value) => new Date(`${value}T00:00:00`).getTime());
        let start = Math.min(...timestamps);
        let end = Math.max(...timestamps);
        if (start === end) end += 7 * 86_400_000;
        const padding = 2 * 86_400_000;
        start -= padding;
        end += padding;
        const duration = Math.max(86_400_000, end - start);
        return { tasks, start, end, duration };
    }, [workspace]);

    if (loading && !workspace) return <DataLoading label="Loading task workspace..." />;
    if (error && !workspace) return <DataError message={error} onRetry={() => void load()} />;
    if (!workspace) return null;

    const contextName = workspace.project_name || workspace.client_name || "ADB Internal";
    const sectionsForRender = [
        ...workspace.sections,
        {
            id: 0,
            name: "Unsectioned",
            sort_order: "0",
            tasks: workspace.unsectioned_tasks,
        },
    ];

    return (
        <div className="space-y-6">
            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <div className="text-xs font-medium text-adb-cyan-400">{contextName}</div>
                    <h1 className="mt-1 text-2xl font-semibold text-white">{workspace.name}</h1>
                    {workspace.description ? (
                        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                            {workspace.description}
                        </p>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                        <span>{workspace.open_tasks} open</span>
                        <span>·</span>
                        <span>{workspace.total_tasks} total</span>
                    </div>
                </div>
                <div className="flex flex-wrap gap-2">
                    <ButtonLink href={`/admin/tasks/new?task_list_id=${workspace.id}`}>Add task</ButtonLink>
                    {workspace.project_id ? (
                        <ButtonLink href={`/admin/projects/${workspace.project_id}`} variant="outline">
                            Project
                        </ButtonLink>
                    ) : null}
                </div>
            </div>

            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="inline-flex w-fit rounded-lg border border-slate-800 bg-slate-900 p-1">
                    {(["list", "board", "timeline"] as ViewMode[]).map((mode) => (
                        <button
                            key={mode}
                            type="button"
                            onClick={() => changeView(mode)}
                            className={`rounded-md px-4 py-2 text-sm font-medium capitalize transition ${
                                view === mode
                                    ? "bg-slate-700 text-white"
                                    : "text-slate-400 hover:text-slate-200"
                            }`}
                        >
                            {mode}
                        </button>
                    ))}
                </div>

                {workspace.can_change ? (
                    <form onSubmit={(event) => void createSection(event)} className="flex max-w-sm gap-2">
                        <Input
                            value={newSectionName}
                            onChange={(event) => setNewSectionName(event.target.value)}
                            placeholder="New section"
                            className="h-9"
                        />
                        <Button
                            type="submit"
                            variant="outline"
                            disabled={creatingSection || !newSectionName.trim()}
                        >
                            Add section
                        </Button>
                    </form>
                ) : null}
            </div>

            {view === "list" ? (
                <div className="space-y-5">
                    {sectionsForRender.map((section) => {
                        const sectionId = section.id || null;
                        return (
                            <Card
                                key={section.id || "unsectioned"}
                                className="overflow-hidden"
                                onDragOver={(event) => event.preventDefault()}
                                onDrop={(event) => void dropAtEnd(event, sectionId, section.tasks)}
                            >
                                <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                                    <h2 className="text-sm font-semibold text-white">{section.name}</h2>
                                    <span className="text-xs text-slate-500">{section.tasks.length}</span>
                                </div>
                                {section.tasks.length ? (
                                    <div className="divide-y divide-slate-800">
                                        {section.tasks.map((task) => (
                                            <div
                                                key={task.id}
                                                draggable
                                                onDragStart={(event) => handleDragStart(event, task.id)}
                                                onDragOver={(event) => event.preventDefault()}
                                                onDrop={(event) =>
                                                    void dropBefore(event, sectionId, section.tasks, task.id)
                                                }
                                                className="group grid cursor-grab gap-3 px-4 py-3 active:cursor-grabbing md:grid-cols-[minmax(0,1fr)_9rem_7rem] md:items-center"
                                            >
                                                <div className="min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-slate-600 opacity-0 transition group-hover:opacity-100">⋮⋮</span>
                                                        <Link
                                                            href={`/admin/tasks/${task.id}`}
                                                            className="truncate text-sm font-medium text-slate-200 hover:text-adb-cyan-300"
                                                        >
                                                            {task.title}
                                                        </Link>
                                                        {task.blocked_by_count ? <Badge>Blocked</Badge> : null}
                                                    </div>
                                                    <div className="mt-1 pl-6">
                                                        <TaskMeta task={task} />
                                                    </div>
                                                </div>
                                                <span className="text-xs text-slate-400">{task.status}</span>
                                                <span className="text-xs text-slate-500">
                                                    {priorityLabels[task.priority] || "Medium"}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="px-4 py-5 text-sm text-slate-600">Drop tasks here or add one below.</div>
                                )}
                                <div className="border-t border-slate-800 bg-slate-950/40 p-3">
                                    <QuickAdd
                                        taskListId={workspace.id}
                                        sectionId={sectionId}
                                        onCreated={load}
                                    />
                                </div>
                            </Card>
                        );
                    })}
                </div>
            ) : null}

            {view === "board" ? (
                <div className="overflow-x-auto pb-3">
                    <div className="flex min-w-max gap-4">
                        {sectionsForRender.map((section) => {
                            const sectionId = section.id || null;
                            return (
                                <div
                                    key={section.id || "unsectioned"}
                                    className="w-80 shrink-0 rounded-xl border border-slate-800 bg-slate-900/50"
                                    onDragOver={(event) => event.preventDefault()}
                                    onDrop={(event) => void dropAtEnd(event, sectionId, section.tasks)}
                                >
                                    <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                                        <h2 className="text-sm font-semibold text-white">{section.name}</h2>
                                        <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                                            {section.tasks.length}
                                        </span>
                                    </div>
                                    <div className="space-y-3 p-3">
                                        {section.tasks.map((task) => (
                                            <div
                                                key={task.id}
                                                draggable
                                                onDragStart={(event) => handleDragStart(event, task.id)}
                                                onDragOver={(event) => event.preventDefault()}
                                                onDrop={(event) =>
                                                    void dropBefore(event, sectionId, section.tasks, task.id)
                                                }
                                                className="cursor-grab rounded-lg border border-slate-800 bg-slate-950 p-4 shadow-sm shadow-black/20 active:cursor-grabbing"
                                            >
                                                <Link
                                                    href={`/admin/tasks/${task.id}`}
                                                    className="text-sm font-medium text-slate-100 hover:text-adb-cyan-300"
                                                >
                                                    {task.title}
                                                </Link>
                                                <div className="mt-3">
                                                    <TaskMeta task={task} />
                                                </div>
                                                <div className="mt-3 flex items-center justify-between gap-3">
                                                    <Badge>{task.status}</Badge>
                                                    <span className="text-[11px] text-slate-600">
                                                        {priorityLabels[task.priority]}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                        <QuickAdd
                                            taskListId={workspace.id}
                                            sectionId={sectionId}
                                            onCreated={load}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            ) : null}

            {view === "timeline" ? (
                timeline ? (
                    <Card className="overflow-hidden">
                        <div className="grid grid-cols-[16rem_minmax(44rem,1fr)] border-b border-slate-800 bg-slate-900/60">
                            <div className="border-r border-slate-800 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Task
                            </div>
                            <div className="flex items-center justify-between px-4 py-3 text-xs text-slate-500">
                                <span>{formatDate(new Date(timeline.start).toISOString().slice(0, 10))}</span>
                                <span>{formatDate(new Date(timeline.end).toISOString().slice(0, 10))}</span>
                            </div>
                        </div>
                        <div className="divide-y divide-slate-800">
                            {timeline.tasks.map((task) => {
                                const startValue = task.start_date || task.due_date;
                                const endValue = task.due_date || task.start_date;
                                if (!startValue || !endValue) return null;
                                const taskStart = new Date(`${startValue}T00:00:00`).getTime();
                                const taskEnd = new Date(`${endValue}T00:00:00`).getTime() + 86_400_000;
                                const left = ((taskStart - timeline.start) / timeline.duration) * 100;
                                const width = Math.max(
                                    1.2,
                                    ((taskEnd - taskStart) / timeline.duration) * 100,
                                );
                                return (
                                    <div key={task.id} className="grid grid-cols-[16rem_minmax(44rem,1fr)]">
                                        <div className="border-r border-slate-800 px-4 py-3">
                                            <Link
                                                href={`/admin/tasks/${task.id}`}
                                                className="block truncate text-sm font-medium text-slate-200 hover:text-adb-cyan-300"
                                            >
                                                {task.title}
                                            </Link>
                                            <div className="mt-1 text-[11px] text-slate-600">
                                                {task.assigned_to_name || "Unassigned"}
                                            </div>
                                        </div>
                                        <div className="relative min-h-14 bg-[linear-gradient(to_right,rgba(51,65,85,0.22)_1px,transparent_1px)] bg-[size:8.333%_100%] px-4 py-3">
                                            <div
                                                className="absolute top-4 h-6 rounded-md border border-adb-cyan-500/40 bg-adb-cyan-500/20 px-2 text-[11px] leading-6 text-adb-cyan-200"
                                                style={{
                                                    left: `calc(${Math.max(0, left)}% + 1rem)`,
                                                    width: `${Math.min(100 - Math.max(0, left), width)}%`,
                                                }}
                                                title={`${formatDate(task.start_date)} – ${formatDate(task.due_date)}`}
                                            >
                                                <span className="block truncate">{task.title}</span>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </Card>
                ) : (
                    <EmptyState
                        title="No dated tasks for the timeline"
                        description="Add start and due dates to tasks to build a delivery timeline."
                    />
                )
            ) : null}
        </div>
    );
}

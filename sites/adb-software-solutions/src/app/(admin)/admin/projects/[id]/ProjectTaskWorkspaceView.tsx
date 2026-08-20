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
import {
    DragEvent,
    FormEvent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

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
    sort_order: string;
    subtask_count: number;
    blocked_by_count: number;
}

interface WorkspaceSection {
    id: number;
    name: string;
    tasks: WorkspaceTask[];
}

interface TaskListWorkspace {
    id: number;
    name: string;
    sections: WorkspaceSection[];
    unsectioned_tasks: WorkspaceTask[];
    total_tasks: number;
    open_tasks: number;
}

interface ProjectTaskWorkspace {
    project_id: number;
    project_name: string;
    ownership_type: "client" | "internal";
    client_id: number | null;
    client_name: string | null;
    task_lists: TaskListWorkspace[];
    unlisted_tasks: WorkspaceTask[];
    can_add_task: boolean;
    can_add_task_list: boolean;
    can_change_task: boolean;
    can_view_task_lists: boolean;
}

interface BoardColumn {
    key: string;
    taskListId: number | null;
    sectionId: number | null;
    title: string;
    subtitle: string | null;
    tasks: WorkspaceTask[];
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

function allTasks(workspace: ProjectTaskWorkspace) {
    return [
        ...workspace.unlisted_tasks,
        ...workspace.task_lists.flatMap((taskList) => [
            ...taskList.unsectioned_tasks,
            ...taskList.sections.flatMap((section) => section.tasks),
        ]),
    ];
}

function BoardQuickAdd({
    projectId,
    workspace,
    column,
    onCreated,
}: {
    projectId: number;
    workspace: ProjectTaskWorkspace;
    column: BoardColumn;
    onCreated: () => Promise<void>;
}) {
    const [title, setTitle] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!title.trim()) return;
        setSaving(true);
        setError(null);
        try {
            if (column.taskListId !== null) {
                await fetchAPI(AdminAPI.tasks.lists.quickTask(column.taskListId), {
                    method: "POST",
                    body: JSON.stringify({
                        title: title.trim(),
                        section_id: column.sectionId,
                    }),
                });
            } else {
                await fetchAPI(AdminAPI.tasks.create(), {
                    method: "POST",
                    body: JSON.stringify({
                        title: title.trim(),
                        description: "",
                        ownership_type: workspace.ownership_type,
                        client_id: workspace.client_id,
                        project_id: projectId,
                        priority: 2,
                        recurrence_frequency: "none",
                    }),
                });
            }
            setTitle("");
            await onCreated();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to add task.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <form onSubmit={(event) => void submit(event)} className="space-y-2">
            <div className="flex gap-2">
                <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="Add task..."
                    className="h-9"
                />
                <Button
                    type="submit"
                    variant="ghost"
                    size="sm"
                    disabled={saving || !title.trim()}
                >
                    {saving ? "…" : "+"}
                </Button>
            </div>
            {error ? <p className="text-xs text-red-300">{error}</p> : null}
        </form>
    );
}

export function ProjectTaskWorkspaceView({ projectId }: { projectId: number }) {
    const [workspace, setWorkspace] = useState<ProjectTaskWorkspace | null>(null);
    const [view, setView] = useState<ViewMode>("list");
    const [draggedTaskId, setDraggedTaskId] = useState<number | null>(null);
    const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            setWorkspace(
                (await fetchAPI(AdminAPI.projects.taskWorkspace(projectId))) as ProjectTaskWorkspace,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load project task workspace.",
            );
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        const stored = window.localStorage.getItem(`project-task-view:${projectId}`) as ViewMode | null;
        if (stored === "list" || stored === "board" || stored === "timeline") setView(stored);
        void load();
    }, [load, projectId]);

    function changeView(next: ViewMode) {
        setView(next);
        window.localStorage.setItem(`project-task-view:${projectId}`, next);
    }

    const boardColumns = useMemo<BoardColumn[]>(() => {
        if (!workspace) return [];
        const columns: BoardColumn[] = [];
        for (const taskList of workspace.task_lists) {
            for (const section of taskList.sections) {
                columns.push({
                    key: `${taskList.id}:${section.id}`,
                    taskListId: taskList.id,
                    sectionId: section.id,
                    title: section.name,
                    subtitle: taskList.name,
                    tasks: section.tasks,
                });
            }
            if (
                taskList.unsectioned_tasks.length ||
                taskList.sections.length === 0 ||
                workspace.can_add_task
            ) {
                columns.push({
                    key: `${taskList.id}:none`,
                    taskListId: taskList.id,
                    sectionId: null,
                    title: taskList.sections.length ? "Unsectioned" : taskList.name,
                    subtitle: taskList.sections.length ? taskList.name : null,
                    tasks: taskList.unsectioned_tasks,
                });
            }
        }
        if (workspace.unlisted_tasks.length || workspace.can_add_task || workspace.can_change_task) {
            columns.push({
                key: "unlisted",
                taskListId: null,
                sectionId: null,
                title: "No task list",
                subtitle: "Project tasks not organised into a list",
                tasks: workspace.unlisted_tasks,
            });
        }
        return columns;
    }, [workspace]);

    const timeline = useMemo(() => {
        if (!workspace) return null;
        const tasks = allTasks(workspace).filter((task) => task.start_date || task.due_date);
        if (!tasks.length) return null;
        const dates = tasks.flatMap((task) => [task.start_date, task.due_date]).filter(Boolean) as string[];
        const stamps = dates.map((value) => new Date(`${value}T00:00:00`).getTime());
        let start = Math.min(...stamps) - 2 * 86_400_000;
        let end = Math.max(...stamps) + 2 * 86_400_000;
        if (start === end) end += 7 * 86_400_000;
        return { tasks, start, end, duration: Math.max(86_400_000, end - start) };
    }, [workspace]);

    function taskIdFromDrop(event: DragEvent) {
        event.preventDefault();
        return Number(event.dataTransfer.getData("text/plain") || draggedTaskId || 0);
    }

    async function moveTask(
        taskId: number,
        column: BoardColumn,
        beforeTaskId: number | null,
        afterTaskId: number | null,
    ) {
        if (!workspace?.can_change_task) return;
        try {
            await fetchAPI(AdminAPI.tasks.move(taskId), {
                method: "POST",
                body: JSON.stringify({
                    task_list_id: column.taskListId,
                    section_id: column.sectionId,
                    before_task_id: beforeTaskId,
                    after_task_id: afterTaskId,
                }),
            });
            await load();
        } catch (moveError) {
            setError(moveError instanceof Error ? moveError.message : "Unable to move task.");
        } finally {
            setDraggedTaskId(null);
            setDragOverColumn(null);
        }
    }

    async function dropAtEnd(event: DragEvent, column: BoardColumn) {
        if (!workspace?.can_change_task) return;
        const taskId = taskIdFromDrop(event);
        if (!taskId) return;
        const remaining = column.tasks.filter((task) => task.id !== taskId);
        await moveTask(taskId, column, remaining.at(-1)?.id ?? null, null);
    }

    async function dropBefore(
        event: DragEvent,
        column: BoardColumn,
        targetTaskId: number,
    ) {
        if (!workspace?.can_change_task) return;
        event.stopPropagation();
        const taskId = taskIdFromDrop(event);
        if (!taskId || taskId === targetTaskId) return;
        const remaining = column.tasks.filter((task) => task.id !== taskId);
        const targetIndex = remaining.findIndex((task) => task.id === targetTaskId);
        const previousTaskId = targetIndex > 0 ? remaining[targetIndex - 1].id : null;
        await moveTask(taskId, column, previousTaskId, targetTaskId);
    }

    if (loading && !workspace) return <DataLoading label="Loading project work..." />;
    if (error && !workspace) return <DataError message={error} onRetry={() => void load()} />;
    if (!workspace) return null;

    const projectTasks = allTasks(workspace);
    const totalTasks = projectTasks.length;
    const openTasks = projectTasks.filter((task) => !task.completed).length;

    return (
        <section className="space-y-5 border-t border-slate-800 pt-8">
            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">Project work</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        {openTasks} open of {totalTasks} tasks across {workspace.task_lists.length} task list
                        {workspace.task_lists.length === 1 ? "" : "s"}.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {workspace.can_add_task ? (
                        <ButtonLink href={`/admin/tasks/new?project_id=${projectId}`}>
                            Add task
                        </ButtonLink>
                    ) : null}
                    {workspace.can_view_task_lists ? (
                        <ButtonLink href="/admin/task-lists" variant="outline">
                            {workspace.can_add_task_list ? "Manage task lists" : "Task lists"}
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
                {workspace.can_view_task_lists && workspace.task_lists.length ? (
                    <div className="flex flex-wrap gap-2">
                        {workspace.task_lists.map((taskList) => (
                            <Link
                                key={taskList.id}
                                href={`/admin/task-lists/${taskList.id}`}
                                className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-400 transition hover:border-slate-700 hover:text-white"
                            >
                                {taskList.name} · {taskList.open_tasks}
                            </Link>
                        ))}
                    </div>
                ) : null}
            </div>

            {totalTasks === 0 && view !== "board" ? (
                <EmptyState
                    title="No project tasks yet"
                    description={
                        workspace.can_add_task
                            ? "Add a task directly or switch to Board to build the project in place."
                            : "No tasks are currently recorded for this project."
                    }
                />
            ) : null}

            {view === "list" && totalTasks > 0 ? (
                <div className="space-y-5">
                    {workspace.task_lists.map((taskList) => (
                        <Card key={taskList.id} className="overflow-hidden">
                            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
                                <div>
                                    {workspace.can_view_task_lists ? (
                                        <Link
                                            href={`/admin/task-lists/${taskList.id}`}
                                            className="text-sm font-semibold text-white hover:text-adb-cyan-300"
                                        >
                                            {taskList.name}
                                        </Link>
                                    ) : (
                                        <h3 className="text-sm font-semibold text-white">{taskList.name}</h3>
                                    )}
                                    <p className="mt-1 text-xs text-slate-500">
                                        {taskList.open_tasks} open · {taskList.total_tasks} total
                                    </p>
                                </div>
                                {workspace.can_view_task_lists ? (
                                    <ButtonLink href={`/admin/task-lists/${taskList.id}`} variant="outline">
                                        Open list
                                    </ButtonLink>
                                ) : null}
                            </div>
                            <div className="divide-y divide-slate-800">
                                {[
                                    ...taskList.sections,
                                    {
                                        id: 0,
                                        name: "Unsectioned",
                                        tasks: taskList.unsectioned_tasks,
                                    },
                                ]
                                    .filter((section) => section.tasks.length)
                                    .map((section) => (
                                        <div key={section.id || "none"}>
                                            <div className="bg-slate-950/40 px-5 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                                                {section.name}
                                            </div>
                                            <div className="divide-y divide-slate-800">
                                                {section.tasks.map((task) => (
                                                    <Link
                                                        key={task.id}
                                                        href={`/admin/tasks/${task.id}`}
                                                        className="grid gap-2 px-5 py-3 transition hover:bg-slate-900/60 md:grid-cols-[minmax(0,1fr)_9rem_6rem] md:items-center"
                                                    >
                                                        <div className="min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className="truncate text-sm font-medium text-slate-200">
                                                                    {task.title}
                                                                </span>
                                                                {task.blocked_by_count ? <Badge>Blocked</Badge> : null}
                                                            </div>
                                                            <div className="mt-1 text-xs text-slate-600">
                                                                {task.assigned_to_name || "Unassigned"}
                                                                {task.subtask_count
                                                                    ? ` · ${task.subtask_count} subtasks`
                                                                    : ""}
                                                            </div>
                                                        </div>
                                                        <span className="text-xs text-slate-400">{task.status}</span>
                                                        <span className="text-xs text-slate-500">
                                                            {formatDate(task.due_date)}
                                                        </span>
                                                    </Link>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        </Card>
                    ))}

                    {workspace.unlisted_tasks.length ? (
                        <Card className="overflow-hidden">
                            <div className="border-b border-slate-800 px-5 py-4">
                                <h3 className="text-sm font-semibold text-white">No task list</h3>
                            </div>
                            <div className="divide-y divide-slate-800">
                                {workspace.unlisted_tasks.map((task) => (
                                    <Link
                                        key={task.id}
                                        href={`/admin/tasks/${task.id}`}
                                        className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-slate-900/60"
                                    >
                                        <span className="text-sm font-medium text-slate-200">{task.title}</span>
                                        <span className="text-xs text-slate-500">{formatDate(task.due_date)}</span>
                                    </Link>
                                ))}
                            </div>
                        </Card>
                    ) : null}
                </div>
            ) : null}

            {view === "board" ? (
                boardColumns.length ? (
                    <div className="overflow-x-auto pb-3">
                        <div className="flex min-w-max gap-4">
                            {boardColumns.map((column) => {
                                const highlighted = dragOverColumn === column.key;
                                return (
                                    <div
                                        key={column.key}
                                        onDragOver={
                                            workspace.can_change_task
                                                ? (event) => {
                                                      event.preventDefault();
                                                      setDragOverColumn(column.key);
                                                  }
                                                : undefined
                                        }
                                        onDrop={
                                            workspace.can_change_task
                                                ? (event) => void dropAtEnd(event, column)
                                                : undefined
                                        }
                                        className={`w-80 shrink-0 rounded-xl border bg-slate-900/50 transition ${
                                            highlighted
                                                ? "border-adb-cyan-500/60 bg-adb-cyan-500/5"
                                                : "border-slate-800"
                                        }`}
                                    >
                                        <div className="border-b border-slate-800 px-4 py-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <h3 className="text-sm font-semibold text-white">{column.title}</h3>
                                                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                                                    {column.tasks.length}
                                                </span>
                                            </div>
                                            {column.subtitle ? (
                                                <div className="mt-1 text-[11px] text-slate-600">
                                                    {column.subtitle}
                                                </div>
                                            ) : null}
                                        </div>
                                        <div className="min-h-24 space-y-3 p-3">
                                            {column.tasks.map((task) => (
                                                <div
                                                    key={task.id}
                                                    draggable={workspace.can_change_task}
                                                    onDragStart={
                                                        workspace.can_change_task
                                                            ? (event) => {
                                                                  setDraggedTaskId(task.id);
                                                                  event.dataTransfer.effectAllowed = "move";
                                                                  event.dataTransfer.setData(
                                                                      "text/plain",
                                                                      String(task.id),
                                                                  );
                                                              }
                                                            : undefined
                                                    }
                                                    onDragEnd={() => {
                                                        setDraggedTaskId(null);
                                                        setDragOverColumn(null);
                                                    }}
                                                    onDragOver={
                                                        workspace.can_change_task
                                                            ? (event) => {
                                                                  event.preventDefault();
                                                                  event.stopPropagation();
                                                                  setDragOverColumn(column.key);
                                                              }
                                                            : undefined
                                                    }
                                                    onDrop={
                                                        workspace.can_change_task
                                                            ? (event) =>
                                                                  void dropBefore(event, column, task.id)
                                                            : undefined
                                                    }
                                                    className={`rounded-lg border bg-slate-950 p-4 transition ${
                                                        draggedTaskId === task.id
                                                            ? "border-adb-cyan-500/40 opacity-40"
                                                            : "border-slate-800 hover:border-slate-700"
                                                    } ${
                                                        workspace.can_change_task
                                                            ? "cursor-grab active:cursor-grabbing"
                                                            : ""
                                                    }`}
                                                >
                                                    <Link
                                                        href={`/admin/tasks/${task.id}`}
                                                        className="text-sm font-medium text-slate-100 hover:text-adb-cyan-300"
                                                    >
                                                        {task.title}
                                                    </Link>
                                                    <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                                                        <span>
                                                            {task.assigned_to_name || "Unassigned"}
                                                        </span>
                                                        {task.due_date ? (
                                                            <span>{formatDate(task.due_date)}</span>
                                                        ) : null}
                                                        {task.blocked_by_count ? <span>Blocked</span> : null}
                                                        {task.subtask_count ? (
                                                            <span>{task.subtask_count} subtasks</span>
                                                        ) : null}
                                                    </div>
                                                    <div className="mt-3 flex items-center justify-between gap-3">
                                                        <Badge>{task.status}</Badge>
                                                        <span className="text-[11px] text-slate-600">
                                                            {priorityLabels[task.priority]}
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                            {column.tasks.length === 0 && !workspace.can_add_task ? (
                                                <div className="rounded-lg border border-dashed border-slate-800 px-3 py-6 text-center text-xs text-slate-600">
                                                    Drop a task here
                                                </div>
                                            ) : null}
                                            {workspace.can_add_task ? (
                                                <div className="border-t border-slate-800 pt-3">
                                                    <BoardQuickAdd
                                                        projectId={projectId}
                                                        workspace={workspace}
                                                        column={column}
                                                        onCreated={load}
                                                    />
                                                </div>
                                            ) : null}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ) : (
                    <EmptyState
                        title="No board columns yet"
                        description="Create a task list and sections to build out this project's workflow."
                    />
                )
            ) : null}

            {view === "timeline" && totalTasks > 0 ? (
                timeline ? (
                    <Card className="overflow-hidden">
                        <div className="grid grid-cols-[17rem_minmax(46rem,1fr)] border-b border-slate-800 bg-slate-900/60">
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
                                    <div key={task.id} className="grid grid-cols-[17rem_minmax(46rem,1fr)]">
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
                                        <div className="relative min-h-14 bg-[linear-gradient(to_right,rgba(51,65,85,0.22)_1px,transparent_1px)] bg-[size:8.333%_100%]">
                                            <div
                                                className="absolute top-4 h-6 rounded-md border border-adb-cyan-500/40 bg-adb-cyan-500/20 px-2 text-[11px] leading-6 text-adb-cyan-200"
                                                style={{
                                                    left: `calc(${Math.max(0, left)}% + 1rem)`,
                                                    width: `${Math.min(100 - Math.max(0, left), width)}%`,
                                                }}
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
                        title="No dated project tasks"
                        description="Add start and due dates to tasks to build a project timeline."
                    />
                )
            ) : null}
        </section>
    );
}

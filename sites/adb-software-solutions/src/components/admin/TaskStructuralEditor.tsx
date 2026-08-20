"use client";

import { Button, Card, DataLoading, Select } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { useEffect, useMemo, useState } from "react";

type Ownership = "client" | "internal";
type Recurrence = "none" | "daily" | "weekly" | "monthly";

interface TaskDetail {
    id: number;
    title: string;
    description: string;
    status_id: number | null;
    priority: number;
    start_date: string | null;
    due_date: string | null;
    completed_at: string | null;
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
    task_list_id: number | null;
    assigned_to_id: string | null;
    recurrence_frequency: Recurrence;
    can_change: boolean;
}

interface StatusOption {
    id: number;
    name: string;
}

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

interface TaskListOption {
    id: number;
    name: string;
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
}

interface TaskOptions {
    statuses: StatusOption[];
    clients: ClientOption[];
    projects: ProjectOption[];
    task_lists: TaskListOption[];
}

interface StructuralState {
    project_id: number | null;
    ownership_type: Ownership;
    client_id: number | null;
    task_list_id: number | null;
    status_id: number | null;
    recurrence_frequency: Recurrence;
}

function optionalNumber(value: string) {
    return value ? Number(value) : null;
}

function stateFromTask(task: TaskDetail): StructuralState {
    return {
        project_id: task.project_id,
        ownership_type: task.ownership_type,
        client_id: task.client_id,
        task_list_id: task.task_list_id,
        status_id: task.status_id,
        recurrence_frequency: task.recurrence_frequency,
    };
}

export function TaskStructuralEditor({
    taskId,
    onChanged,
}: {
    taskId: number;
    onChanged?: () => void;
}) {
    const [task, setTask] = useState<TaskDetail | null>(null);
    const [options, setOptions] = useState<TaskOptions | null>(null);
    const [form, setForm] = useState<StructuralState | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            try {
                setLoading(true);
                setError(null);
                const [loadedTask, loadedOptions] = await Promise.all([
                    fetchAPI(AdminAPI.tasks.get(taskId)) as Promise<TaskDetail>,
                    fetchAPI(AdminAPI.tasks.options()) as Promise<TaskOptions>,
                ]);
                if (cancelled) return;
                setTask(loadedTask);
                setOptions(loadedOptions);
                setForm(stateFromTask(loadedTask));
            } catch (loadError) {
                if (!cancelled) {
                    setError(
                        loadError instanceof Error
                            ? loadError.message
                            : "Unable to load additional task fields.",
                    );
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }
        void load();
        return () => {
            cancelled = true;
        };
    }, [taskId]);

    const selectedProject = useMemo(
        () => options?.projects.find((project) => project.id === form?.project_id) ?? null,
        [form?.project_id, options],
    );
    const effectiveOwnership = selectedProject?.ownership_type ?? form?.ownership_type ?? "internal";
    const effectiveClientId = selectedProject?.client_id ?? form?.client_id ?? null;

    const availableTaskLists = useMemo(() => {
        if (!options || !form) return [];
        return options.task_lists.filter((taskList) => {
            if (taskList.project_id !== null) {
                return taskList.project_id === form.project_id;
            }
            if (taskList.ownership_type !== effectiveOwnership) return false;
            if (effectiveOwnership === "client") return taskList.client_id === effectiveClientId;
            return taskList.client_id === null;
        });
    }, [effectiveClientId, effectiveOwnership, form, options]);

    function updateProject(value: string) {
        if (!form || !options) return;
        const projectId = optionalNumber(value);
        const project = options.projects.find((candidate) => candidate.id === projectId);
        setForm({
            ...form,
            project_id: projectId,
            ownership_type: project?.ownership_type ?? form.ownership_type,
            client_id: project ? project.client_id : form.client_id,
            task_list_id: null,
        });
    }

    function updateOwner(value: string) {
        if (!form) return;
        if (value === "internal") {
            setForm({
                ...form,
                ownership_type: "internal",
                client_id: null,
                task_list_id: null,
            });
            return;
        }
        setForm({
            ...form,
            ownership_type: "client",
            client_id: Number(value.replace("client:", "")),
            task_list_id: null,
        });
    }

    async function save() {
        if (!task || !form || !options || task.completed_at || !task.can_change) return;
        setSaving(true);
        setError(null);
        try {
            const latest = (await fetchAPI(AdminAPI.tasks.get(taskId))) as TaskDetail;
            const currentProject = options.projects.find((project) => project.id === form.project_id);
            const ownership = currentProject?.ownership_type ?? form.ownership_type;
            const clientId = currentProject?.client_id ?? form.client_id;
            const updated = (await fetchAPI(AdminAPI.tasks.update(taskId), {
                method: "PUT",
                body: JSON.stringify({
                    title: latest.title,
                    description: latest.description,
                    project_id: form.project_id,
                    ownership_type: ownership,
                    client_id: ownership === "client" ? clientId : null,
                    task_list_id: form.task_list_id,
                    status_id: form.status_id,
                    priority: latest.priority,
                    start_date: latest.start_date,
                    due_date: latest.due_date,
                    assigned_to_id: latest.assigned_to_id,
                    recurrence_frequency: form.recurrence_frequency,
                }),
            })) as TaskDetail;
            setTask(updated);
            setForm(stateFromTask(updated));
            onChanged?.();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to save task fields.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <Card id="task-advanced-fields" data-task-advanced-editor className="scroll-mt-6 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h2 className="text-sm font-semibold text-white">Planning & organisation</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        Project, ownership, task list, workflow status and recurrence can all be changed without leaving the Task.
                    </p>
                </div>
                {task?.completed_at ? (
                    <span className="text-xs text-slate-500">Reopen this Task before changing these fields.</span>
                ) : null}
            </div>

            {loading ? <div className="mt-4"><DataLoading label="Loading task fields..." /></div> : null}
            {error ? (
                <div className="mt-4 rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            {!loading && form && options ? (
                <div className="mt-5 space-y-5">
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label className="space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Project</span>
                            <Select
                                value={form.project_id ?? ""}
                                disabled={saving || Boolean(task?.completed_at)}
                                onChange={(event) => updateProject(event.target.value)}
                            >
                                <option value="">No project</option>
                                {options.projects.map((project) => (
                                    <option key={project.id} value={project.id}>
                                        {project.name} — {project.client_name || "ADB Internal"}
                                    </option>
                                ))}
                            </Select>
                        </label>

                        <label className="space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Owner</span>
                            <Select
                                value={
                                    effectiveOwnership === "internal"
                                        ? "internal"
                                        : `client:${effectiveClientId ?? ""}`
                                }
                                disabled={saving || Boolean(task?.completed_at) || selectedProject !== null}
                                onChange={(event) => updateOwner(event.target.value)}
                            >
                                <option value="internal">ADB Internal</option>
                                {options.clients.map((client) => (
                                    <option key={client.id} value={`client:${client.id}`}>
                                        {client.name}
                                    </option>
                                ))}
                            </Select>
                        </label>

                        <label className="space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Task list</span>
                            <Select
                                value={form.task_list_id ?? ""}
                                disabled={saving || Boolean(task?.completed_at)}
                                onChange={(event) =>
                                    setForm({
                                        ...form,
                                        task_list_id: optionalNumber(event.target.value),
                                    })
                                }
                            >
                                <option value="">No task list</option>
                                {availableTaskLists.map((taskList) => (
                                    <option key={taskList.id} value={taskList.id}>
                                        {taskList.name}
                                    </option>
                                ))}
                            </Select>
                        </label>

                        <label className="space-y-1.5 text-xs font-medium text-slate-500">
                            <span>Status</span>
                            <Select
                                value={form.status_id ?? ""}
                                disabled={saving || Boolean(task?.completed_at)}
                                onChange={(event) =>
                                    setForm({ ...form, status_id: optionalNumber(event.target.value) })
                                }
                            >
                                <option value="">Unassigned</option>
                                {options.statuses
                                    .filter((status) => !["done", "completed"].includes(status.name.toLowerCase()))
                                    .map((status) => (
                                        <option key={status.id} value={status.id}>
                                            {status.name}
                                        </option>
                                    ))}
                            </Select>
                            <span className="block font-normal text-slate-600">
                                Use the completion control for Done so completion time and recurrence remain correct.
                            </span>
                        </label>

                        <label className="space-y-1.5 text-xs font-medium text-slate-500 sm:col-span-2">
                            <span>Recurrence</span>
                            <Select
                                value={form.recurrence_frequency}
                                disabled={saving || Boolean(task?.completed_at)}
                                onChange={(event) =>
                                    setForm({
                                        ...form,
                                        recurrence_frequency: event.target.value as Recurrence,
                                    })
                                }
                            >
                                <option value="none">Does not repeat</option>
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="monthly">Monthly</option>
                            </Select>
                        </label>
                    </div>

                    <div className="flex justify-end border-t border-slate-800 pt-4">
                        <Button
                            type="button"
                            disabled={saving || Boolean(task?.completed_at) || !task?.can_change}
                            onClick={() => void save()}
                        >
                            {saving ? "Saving…" : "Save planning fields"}
                        </Button>
                    </div>
                </div>
            ) : null}
        </Card>
    );
}

"use client";

import { Button, ButtonLink, DataLoading, Input, Select, Textarea } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";

type Ownership = "client" | "internal";
type Recurrence = "none" | "daily" | "weekly" | "monthly";

interface StatusOption {
    id: number;
    name: string;
}

interface StaffOption {
    id: string;
    name: string;
    email: string;
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
    staff: StaffOption[];
    clients: ClientOption[];
    projects: ProjectOption[];
    task_lists: TaskListOption[];
}

interface TaskResponse {
    id: number;
    title: string;
    description: string;
    status_id: number | null;
    priority: number;
    due_date: string | null;
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
    task_list_id: number | null;
    assigned_to_id: string | null;
    recurrence_frequency: Recurrence;
}

interface TaskFormState {
    title: string;
    description: string;
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
    task_list_id: number | null;
    status_id: number | null;
    priority: number;
    due_date: string;
    assigned_to_id: string | null;
    recurrence_frequency: Recurrence;
}

const EMPTY_FORM: TaskFormState = {
    title: "",
    description: "",
    ownership_type: "internal",
    client_id: null,
    project_id: null,
    task_list_id: null,
    status_id: null,
    priority: 2,
    due_date: "",
    assigned_to_id: null,
    recurrence_frequency: "none",
};

const labelClasses = "space-y-1.5 text-sm font-medium text-slate-300";

function optionalNumber(value: string) {
    return value ? Number(value) : null;
}

function validQueryId(value: string | null) {
    if (!value) return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function initialCreateState(
    options: TaskOptions,
    projectId: number | null,
    clientId: number | null,
    taskListId: number | null,
): TaskFormState {
    const todo = options.statuses.find((status) => status.name.toLowerCase() === "to do");
    const initial: TaskFormState = {
        ...EMPTY_FORM,
        status_id: todo?.id ?? null,
    };

    const taskList = taskListId
        ? options.task_lists.find((candidate) => candidate.id === taskListId)
        : null;
    if (taskList) {
        const project = taskList.project_id
            ? options.projects.find((candidate) => candidate.id === taskList.project_id)
            : null;
        return {
            ...initial,
            ownership_type: project?.ownership_type ?? taskList.ownership_type,
            client_id: project?.client_id ?? taskList.client_id,
            project_id: project?.id ?? null,
            task_list_id: taskList.id,
        };
    }

    const project = projectId
        ? options.projects.find((candidate) => candidate.id === projectId)
        : null;
    if (project) {
        return {
            ...initial,
            ownership_type: project.ownership_type,
            client_id: project.client_id,
            project_id: project.id,
        };
    }

    const client = clientId ? options.clients.find((candidate) => candidate.id === clientId) : null;
    if (client) {
        return {
            ...initial,
            ownership_type: "client",
            client_id: client.id,
        };
    }

    return initial;
}

export function TaskForm({ taskId }: { taskId?: number }) {
    const router = useRouter();
    const searchParams = useSearchParams();
    const projectQueryId = validQueryId(searchParams.get("project_id"));
    const clientQueryId = validQueryId(searchParams.get("client_id"));
    const taskListQueryId = validQueryId(searchParams.get("task_list_id"));
    const [form, setForm] = useState<TaskFormState>(EMPTY_FORM);
    const [options, setOptions] = useState<TaskOptions | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function load() {
            try {
                setIsLoading(true);
                setError(null);
                const [loadedOptions, task] = await Promise.all([
                    fetchAPI(AdminAPI.tasks.options()) as Promise<TaskOptions>,
                    taskId
                        ? (fetchAPI(AdminAPI.tasks.get(taskId)) as Promise<TaskResponse>)
                        : Promise.resolve(null),
                ]);
                setOptions(loadedOptions);
                if (task) {
                    setForm({
                        title: task.title,
                        description: task.description,
                        ownership_type: task.ownership_type,
                        client_id: task.client_id,
                        project_id: task.project_id,
                        task_list_id: task.task_list_id,
                        status_id: task.status_id,
                        priority: task.priority,
                        due_date: task.due_date ?? "",
                        assigned_to_id: task.assigned_to_id,
                        recurrence_frequency: task.recurrence_frequency,
                    });
                } else {
                    setForm(
                        initialCreateState(
                            loadedOptions,
                            projectQueryId,
                            clientQueryId,
                            taskListQueryId,
                        ),
                    );
                }
            } catch (loadError) {
                setError(loadError instanceof Error ? loadError.message : "Unable to load task details.");
            } finally {
                setIsLoading(false);
            }
        }

        void load();
    }, [clientQueryId, projectQueryId, taskId, taskListQueryId]);

    const selectedProject = useMemo(
        () => options?.projects.find((project) => project.id === form.project_id) ?? null,
        [form.project_id, options],
    );

    const effectiveOwnership = selectedProject?.ownership_type ?? form.ownership_type;
    const effectiveClientId = selectedProject?.client_id ?? form.client_id;

    const availableTaskLists = useMemo(() => {
        if (!options) return [];
        return options.task_lists.filter((taskList) => {
            if (taskList.project_id !== null) {
                return taskList.project_id === form.project_id;
            }
            if (taskList.ownership_type !== effectiveOwnership) return false;
            if (effectiveOwnership === "client") {
                return taskList.client_id === effectiveClientId;
            }
            return taskList.client_id === null;
        });
    }, [effectiveClientId, effectiveOwnership, form.project_id, options]);

    function update<K extends keyof TaskFormState>(key: K, value: TaskFormState[K]) {
        setForm((current) => ({ ...current, [key]: value }));
    }

    function updateProject(value: string) {
        const projectId = optionalNumber(value);
        const project = options?.projects.find((candidate) => candidate.id === projectId);
        setForm((current) => ({
            ...current,
            project_id: projectId,
            task_list_id: null,
            ownership_type: project?.ownership_type ?? current.ownership_type,
            client_id: project ? project.client_id : current.client_id,
        }));
    }

    function updateOwnership(value: Ownership) {
        setForm((current) => ({
            ...current,
            ownership_type: value,
            client_id: value === "internal" ? null : current.client_id,
            task_list_id: null,
        }));
    }

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);

        try {
            const task = (await fetchAPI(
                taskId ? AdminAPI.tasks.update(taskId) : AdminAPI.tasks.create(),
                {
                    method: taskId ? "PUT" : "POST",
                    body: JSON.stringify({
                        ...form,
                        due_date: form.due_date || null,
                        ownership_type: effectiveOwnership,
                        client_id: effectiveOwnership === "client" ? effectiveClientId : null,
                    }),
                },
            )) as TaskResponse;
            router.push(`/admin/tasks/${task.id}`);
            router.refresh();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to save the task.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading || !options) return <DataLoading label="Loading task details..." />;

    return (
        <form onSubmit={(event) => void save(event)} className="space-y-6">
            {error ? (
                <div
                    role="alert"
                    className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200"
                >
                    {error}
                </div>
            ) : null}

            <div className="grid gap-5 md:grid-cols-2">
                <label className={`${labelClasses} md:col-span-2`}>
                    <span>Task title</span>
                    <Input
                        value={form.title}
                        onChange={(event) => update("title", event.target.value)}
                        required
                        maxLength={200}
                    />
                </label>

                <label className={labelClasses}>
                    <span>Project</span>
                    <Select value={form.project_id ?? ""} onChange={(event) => updateProject(event.target.value)}>
                        <option value="">No project</option>
                        {options.projects.map((project) => (
                            <option key={project.id} value={project.id}>
                                {project.name} — {project.client_name || "ADB Internal"}
                            </option>
                        ))}
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Task list</span>
                    <Select
                        value={form.task_list_id ?? ""}
                        onChange={(event) => update("task_list_id", optionalNumber(event.target.value))}
                    >
                        <option value="">No task list</option>
                        {availableTaskLists.map((taskList) => (
                            <option key={taskList.id} value={taskList.id}>
                                {taskList.name}
                            </option>
                        ))}
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Ownership</span>
                    <Select
                        value={effectiveOwnership}
                        onChange={(event) => updateOwnership(event.target.value as Ownership)}
                        disabled={selectedProject !== null}
                    >
                        <option value="internal">ADB internal</option>
                        <option value="client">Client</option>
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Client</span>
                    <Select
                        value={effectiveClientId ?? ""}
                        onChange={(event) => {
                            update("client_id", optionalNumber(event.target.value));
                            update("task_list_id", null);
                        }}
                        disabled={selectedProject !== null || effectiveOwnership === "internal"}
                        required={selectedProject === null && effectiveOwnership === "client"}
                    >
                        <option value="">
                            {effectiveOwnership === "internal" ? "Not applicable" : "Select a client"}
                        </option>
                        {options.clients.map((client) => (
                            <option key={client.id} value={client.id}>
                                {client.name}
                            </option>
                        ))}
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Status</span>
                    <Select
                        value={form.status_id ?? ""}
                        onChange={(event) => update("status_id", optionalNumber(event.target.value))}
                    >
                        <option value="">Unassigned</option>
                        {options.statuses.map((status) => (
                            <option key={status.id} value={status.id}>
                                {status.name}
                            </option>
                        ))}
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Priority</span>
                    <Select
                        value={String(form.priority)}
                        onChange={(event) => update("priority", Number(event.target.value))}
                    >
                        <option value="1">Low</option>
                        <option value="2">Medium</option>
                        <option value="3">High</option>
                        <option value="4">Critical</option>
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Assigned to</span>
                    <Select
                        value={form.assigned_to_id ?? ""}
                        onChange={(event) => update("assigned_to_id", event.target.value || null)}
                    >
                        <option value="">Unassigned</option>
                        {options.staff.map((staff) => (
                            <option key={staff.id} value={staff.id}>
                                {staff.name}
                            </option>
                        ))}
                    </Select>
                </label>

                <label className={labelClasses}>
                    <span>Due date</span>
                    <Input
                        type="date"
                        value={form.due_date}
                        onChange={(event) => update("due_date", event.target.value)}
                        required={form.recurrence_frequency !== "none"}
                    />
                </label>

                <label className={labelClasses}>
                    <span>Recurrence</span>
                    <Select
                        value={form.recurrence_frequency}
                        onChange={(event) =>
                            update("recurrence_frequency", event.target.value as Recurrence)
                        }
                    >
                        <option value="none">Does not repeat</option>
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                    </Select>
                </label>
            </div>

            <div className="border-t border-slate-800 pt-6">
                <label className={labelClasses}>
                    <span>Description</span>
                    <Textarea
                        value={form.description}
                        onChange={(event) => update("description", event.target.value)}
                        rows={8}
                        placeholder="Task details, acceptance criteria and useful context."
                    />
                </label>
            </div>

            <div className="flex flex-wrap gap-3 border-t border-slate-800 pt-6">
                <Button type="submit" disabled={isSaving}>
                    {isSaving ? "Saving..." : taskId ? "Save changes" : "Create task"}
                </Button>
                <ButtonLink
                    href={taskId ? `/admin/tasks/${taskId}` : "/admin/tasks"}
                    variant="outline"
                >
                    Cancel
                </ButtonLink>
            </div>
        </form>
    );
}

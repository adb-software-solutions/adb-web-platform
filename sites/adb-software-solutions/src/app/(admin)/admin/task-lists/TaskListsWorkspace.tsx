"use client";

import {
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    Select,
    Textarea,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Ownership = "client" | "internal";

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

interface TaskOptions {
    clients: ClientOption[];
    projects: ProjectOption[];
    can_add_task_list: boolean;
}

interface TaskListRow {
    id: number;
    name: string;
    description: string;
    ownership_type: Ownership;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
    task_count: number;
    open_task_count: number;
}

interface FormState {
    name: string;
    description: string;
    ownership_type: Ownership;
    client_id: number | null;
    project_id: number | null;
}

const EMPTY_FORM: FormState = {
    name: "",
    description: "",
    ownership_type: "internal",
    client_id: null,
    project_id: null,
};

function optionalNumber(value: string) {
    return value ? Number(value) : null;
}

export function TaskListsWorkspace() {
    const [rows, setRows] = useState<TaskListRow[]>([]);
    const [options, setOptions] = useState<TaskOptions | null>(null);
    const [form, setForm] = useState<FormState>(EMPTY_FORM);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [loadedRows, loadedOptions] = await Promise.all([
                fetchAPI(AdminAPI.tasks.lists.list()) as Promise<TaskListRow[]>,
                fetchAPI(AdminAPI.tasks.options()) as Promise<TaskOptions>,
            ]);
            setRows(loadedRows);
            setOptions(loadedOptions);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task lists.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void load();
    }, [load]);

    const selectedProject = useMemo(
        () => options?.projects.find((project) => project.id === form.project_id) ?? null,
        [form.project_id, options],
    );

    function updateProject(value: string) {
        const projectId = optionalNumber(value);
        const project = options?.projects.find((candidate) => candidate.id === projectId);
        setForm((current) => ({
            ...current,
            project_id: projectId,
            ownership_type: project?.ownership_type ?? current.ownership_type,
            client_id: project ? project.client_id : current.client_id,
        }));
    }

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setIsSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.tasks.lists.create(), {
                method: "POST",
                body: JSON.stringify({
                    ...form,
                    ownership_type: selectedProject?.ownership_type ?? form.ownership_type,
                    client_id:
                        selectedProject?.client_id ??
                        (form.ownership_type === "client" ? form.client_id : null),
                }),
            });
            setForm(EMPTY_FORM);
            await load();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to create task list.");
        } finally {
            setIsSaving(false);
        }
    }

    if (isLoading && !options) return <DataLoading label="Loading task lists..." />;
    if (error && !options) return <DataError message={error} onRetry={() => void load()} />;
    if (!options) return null;

    return (
        <div className="space-y-6">
            <div className="flex justify-end">
                <ButtonLink href="/admin/tasks" variant="outline">
                    Back to tasks
                </ButtonLink>
            </div>

            {error ? (
                <div
                    role="alert"
                    className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200"
                >
                    {error}
                </div>
            ) : null}

            {rows.length === 0 ? (
                <EmptyState
                    title="No task lists in your scope"
                    description="Create a task list for recurring admin work, client work or a project."
                />
            ) : (
                <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                    {rows.map((row) => (
                        <Card key={row.id} className="group p-5 transition hover:border-slate-700 hover:bg-slate-900/80">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <Link
                                        href={`/admin/task-lists/${row.id}`}
                                        className="font-medium text-white hover:text-adb-cyan-300"
                                    >
                                        {row.name}
                                    </Link>
                                    <p className="mt-1 truncate text-xs text-slate-500">
                                        {row.project_name || row.client_name || "ADB Internal"}
                                    </p>
                                </div>
                                <span className="shrink-0 rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-400">
                                    {row.open_task_count} open
                                </span>
                            </div>
                            {row.description ? (
                                <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">
                                    {row.description}
                                </p>
                            ) : null}
                            <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-4 text-xs">
                                <span className="text-slate-600">{row.task_count} total tasks</span>
                                <Link
                                    href={`/admin/task-lists/${row.id}`}
                                    className="font-medium text-slate-400 transition group-hover:text-adb-cyan-300"
                                >
                                    Open workspace →
                                </Link>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            {options.can_add_task_list ? (
                <Card className="p-5">
                    <h2 className="text-sm font-semibold text-white">Create task list</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Lists can stand alone, belong to a client, or sit inside a project.
                    </p>
                    <form onSubmit={(event) => void save(event)} className="mt-4 space-y-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <label className="space-y-1.5 text-sm font-medium text-slate-300">
                                <span>Name</span>
                                <Input
                                    value={form.name}
                                    onChange={(event) =>
                                        setForm((current) => ({ ...current, name: event.target.value }))
                                    }
                                    required
                                    maxLength={200}
                                />
                            </label>
                            <label className="space-y-1.5 text-sm font-medium text-slate-300">
                                <span>Project</span>
                                <Select
                                    value={form.project_id ?? ""}
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
                            <label className="space-y-1.5 text-sm font-medium text-slate-300">
                                <span>Ownership</span>
                                <Select
                                    value={selectedProject?.ownership_type ?? form.ownership_type}
                                    disabled={selectedProject !== null}
                                    onChange={(event) =>
                                        setForm((current) => ({
                                            ...current,
                                            ownership_type: event.target.value as Ownership,
                                            client_id:
                                                event.target.value === "internal"
                                                    ? null
                                                    : current.client_id,
                                        }))
                                    }
                                >
                                    <option value="internal">ADB internal</option>
                                    <option value="client">Client</option>
                                </Select>
                            </label>
                            <label className="space-y-1.5 text-sm font-medium text-slate-300">
                                <span>Client</span>
                                <Select
                                    value={selectedProject?.client_id ?? form.client_id ?? ""}
                                    disabled={
                                        selectedProject !== null || form.ownership_type === "internal"
                                    }
                                    required={
                                        selectedProject === null && form.ownership_type === "client"
                                    }
                                    onChange={(event) =>
                                        setForm((current) => ({
                                            ...current,
                                            client_id: optionalNumber(event.target.value),
                                        }))
                                    }
                                >
                                    <option value="">
                                        {form.ownership_type === "internal"
                                            ? "Not applicable"
                                            : "Select a client"}
                                    </option>
                                    {options.clients.map((client) => (
                                        <option key={client.id} value={client.id}>
                                            {client.name}
                                        </option>
                                    ))}
                                </Select>
                            </label>
                        </div>
                        <label className="block space-y-1.5 text-sm font-medium text-slate-300">
                            <span>Description</span>
                            <Textarea
                                value={form.description}
                                onChange={(event) =>
                                    setForm((current) => ({
                                        ...current,
                                        description: event.target.value,
                                    }))
                                }
                                rows={3}
                            />
                        </label>
                        <Button type="submit" disabled={isSaving}>
                            {isSaving ? "Creating..." : "Create task list"}
                        </Button>
                    </form>
                </Card>
            ) : null}
        </div>
    );
}

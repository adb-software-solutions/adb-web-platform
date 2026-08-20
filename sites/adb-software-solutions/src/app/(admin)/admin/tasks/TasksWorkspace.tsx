"use client";

import { Button, ButtonLink, Card, Input, Select } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { TaskList } from "./TaskList";

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
}

function localDate(offsetDays: number) {
    const date = new Date();
    date.setDate(date.getDate() + offsetDays);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export function TasksWorkspace() {
    const { user, hasPermission } = useAuth();
    const [version, setVersion] = useState(0);
    const [options, setOptions] = useState<TaskOptions | null>(null);
    const [title, setTitle] = useState("");
    const [context, setContext] = useState("internal");
    const [due, setDue] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const canAddTask = hasPermission("tasks.add_task");

    useEffect(() => {
        if (!canAddTask) return;
        let cancelled = false;
        void fetchAPI(AdminAPI.tasks.options())
            .then((data) => {
                if (!cancelled) setOptions(data as TaskOptions);
            })
            .catch(() => {
                if (!cancelled) setOptions(null);
            });
        return () => {
            cancelled = true;
        };
    }, [canAddTask]);

    const contextOptions = useMemo(() => {
        if (!options) return [];
        return [
            ...options.projects.map((project) => ({
                value: `project:${project.id}`,
                label: project.client_name
                    ? `${project.name} — ${project.client_name}`
                    : `${project.name} — ADB Internal`,
            })),
            ...options.clients.map((client) => ({
                value: `client:${client.id}`,
                label: `${client.name} — Client`,
            })),
        ];
    }, [options]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!title.trim() || !user) return;

        let ownershipType: Ownership = "internal";
        let projectId: number | null = null;
        let clientId: number | null = null;
        if (context.startsWith("project:")) {
            projectId = Number(context.split(":")[1]);
        } else if (context.startsWith("client:")) {
            ownershipType = "client";
            clientId = Number(context.split(":")[1]);
        }

        setSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.tasks.create(), {
                method: "POST",
                body: JSON.stringify({
                    title: title.trim(),
                    description: "",
                    ownership_type: ownershipType,
                    project_id: projectId,
                    client_id: clientId,
                    priority: 2,
                    due_date: due || null,
                    assigned_to_id: user.id,
                    recurrence_frequency: "none",
                }),
            });
            setTitle("");
            setDue("");
            setVersion((value) => value + 1);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to create the task.");
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-5">
            {canAddTask ? (
                <Card className="p-4">
                    <form onSubmit={(event) => void submit(event)} className="space-y-3">
                        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                            <div className="min-w-0 flex-1">
                                <Input
                                    value={title}
                                    onChange={(event) => setTitle(event.target.value)}
                                    placeholder="Quickly add a task and press Enter..."
                                    aria-label="Quick task title"
                                />
                            </div>
                            <Select
                                value={context}
                                onChange={(event) => setContext(event.target.value)}
                                className="xl:w-72"
                                aria-label="Task context"
                            >
                                <option value="internal">ADB Internal</option>
                                {contextOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </Select>
                            <Select
                                value={due}
                                onChange={(event) => setDue(event.target.value)}
                                className="xl:w-40"
                                aria-label="Task due date"
                            >
                                <option value="">No due date</option>
                                <option value={localDate(0)}>Today</option>
                                <option value={localDate(1)}>Tomorrow</option>
                                <option value={localDate(7)}>In one week</option>
                            </Select>
                            <Button type="submit" disabled={saving || !title.trim()}>
                                {saving ? "Adding..." : "Add task"}
                            </Button>
                            <ButtonLink href="/admin/tasks/new" variant="ghost">
                                More details
                            </ButtonLink>
                        </div>
                        {error ? <div className="text-sm text-red-300">{error}</div> : null}
                    </form>
                </Card>
            ) : null}

            <TaskList key={version} />
        </div>
    );
}

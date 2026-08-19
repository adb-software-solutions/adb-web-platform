"use client";

import {
    Badge,
    ButtonLink,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    Pagination,
    Select,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeaderCell,
    TableRow,
} from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

interface TaskSummary {
    id: number;
    title: string;
    status: string;
    priority: number;
    due_date: string | null;
    completed_at: string | null;
    ownership_type: string;
    client_name: string | null;
    project_name: string | null;
    task_list_name: string | null;
    assigned_to_name: string | null;
    recurrence_frequency: string;
}

interface TaskPage {
    items: TaskSummary[];
    total: number;
    page: number;
    page_size: number;
}

const PAGE_SIZE = 25;

const priorityLabels: Record<number, string> = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Critical",
};

function priorityClasses(priority: number) {
    if (priority === 4) return "border-red-950 bg-red-950/30 text-red-300";
    if (priority === 3) return "border-amber-900/70 bg-amber-950/40 text-amber-300";
    return "border-slate-700 bg-slate-900 text-slate-400";
}

function formatDate(value: string | null) {
    if (!value) return "No due date";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function isOverdue(task: TaskSummary) {
    if (!task.due_date || task.completed_at) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return new Date(`${task.due_date}T00:00:00`) < today;
}

export function TaskList() {
    const [pageData, setPageData] = useState<TaskPage | null>(null);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [ownership, setOwnership] = useState("");
    const [completion, setCompletion] = useState("open");
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const query = useMemo(() => {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(PAGE_SIZE),
        });
        if (search.trim()) params.set("search", search.trim());
        if (ownership) params.set("ownership_type", ownership);
        if (completion === "open") params.set("completed", "false");
        if (completion === "completed") params.set("completed", "true");
        return params.toString();
    }, [completion, ownership, page, search]);

    const loadTasks = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const data = (await fetchAPI(AdminAPI.tasks.list(query))) as TaskPage;
            setPageData(data);
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "An unexpected error occurred while loading tasks.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [query]);

    useEffect(() => {
        void loadTasks();
    }, [loadTasks]);

    function resetPage() {
        setPage(1);
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div className="grid flex-1 gap-3 sm:grid-cols-3">
                    <label className="space-y-1 text-xs font-medium text-slate-400">
                        <span>Search</span>
                        <Input
                            value={search}
                            onChange={(event) => {
                                setSearch(event.target.value);
                                resetPage();
                            }}
                            placeholder="Search tasks..."
                        />
                    </label>
                    <label className="space-y-1 text-xs font-medium text-slate-400">
                        <span>Ownership</span>
                        <Select
                            value={ownership}
                            onChange={(event) => {
                                setOwnership(event.target.value);
                                resetPage();
                            }}
                        >
                            <option value="">All work</option>
                            <option value="internal">Internal</option>
                            <option value="client">Client</option>
                        </Select>
                    </label>
                    <label className="space-y-1 text-xs font-medium text-slate-400">
                        <span>State</span>
                        <Select
                            value={completion}
                            onChange={(event) => {
                                setCompletion(event.target.value);
                                resetPage();
                            }}
                        >
                            <option value="open">Open</option>
                            <option value="completed">Completed</option>
                            <option value="all">All</option>
                        </Select>
                    </label>
                </div>
                <div className="flex flex-wrap gap-2">
                    <ButtonLink href="/admin/task-lists" variant="outline">
                        Task lists
                    </ButtonLink>
                    <ButtonLink href="/admin/tasks/new">Add task</ButtonLink>
                </div>
            </div>

            {isLoading && !pageData ? <DataLoading label="Loading operational tasks..." /> : null}
            {error ? <DataError message={error} onRetry={() => void loadTasks()} /> : null}

            {!error && pageData && pageData.items.length === 0 ? (
                <EmptyState
                    title="No tasks match these filters"
                    description="Create a client, project or standalone internal task to start planning work."
                />
            ) : null}

            {!error && pageData && pageData.items.length > 0 ? (
                <div className="overflow-hidden rounded-lg border border-slate-800">
                    <Table>
                        <TableHead>
                            <tr>
                                <TableHeaderCell>Task</TableHeaderCell>
                                <TableHeaderCell>Status</TableHeaderCell>
                                <TableHeaderCell>Priority</TableHeaderCell>
                                <TableHeaderCell>Context</TableHeaderCell>
                                <TableHeaderCell>Assigned</TableHeaderCell>
                                <TableHeaderCell>Due</TableHeaderCell>
                            </tr>
                        </TableHead>
                        <TableBody>
                            {pageData.items.map((task) => {
                                const overdue = isOverdue(task);
                                return (
                                    <TableRow key={task.id}>
                                        <TableCell>
                                            <Link
                                                href={`/admin/tasks/${task.id}`}
                                                className="font-medium text-slate-100 hover:text-adb-cyan-300"
                                            >
                                                {task.title}
                                            </Link>
                                            <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                                                {task.task_list_name ? <span>{task.task_list_name}</span> : null}
                                                {task.recurrence_frequency !== "none" ? (
                                                    <span className="capitalize">
                                                        {task.recurrence_frequency} recurring
                                                    </span>
                                                ) : null}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-slate-400">{task.status}</TableCell>
                                        <TableCell>
                                            <Badge className={priorityClasses(task.priority)}>
                                                {priorityLabels[task.priority] ?? "Unknown"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <div className="text-slate-300">
                                                {task.project_name || task.client_name || "ADB Internal"}
                                            </div>
                                            <div className="mt-1 text-xs text-slate-500">
                                                {task.ownership_type === "internal" ? "Internal" : "Client"}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-slate-400">
                                            {task.assigned_to_name || "Unassigned"}
                                        </TableCell>
                                        <TableCell
                                            className={
                                                overdue ? "font-medium text-red-300" : "text-slate-400"
                                            }
                                        >
                                            {formatDate(task.due_date)}
                                            {overdue ? (
                                                <div className="mt-1 text-xs text-red-400/70">Overdue</div>
                                            ) : null}
                                        </TableCell>
                                    </TableRow>
                                );
                            })}
                        </TableBody>
                    </Table>
                    <Pagination
                        page={pageData.page}
                        pageSize={pageData.page_size}
                        totalItems={pageData.total}
                        onPageChange={setPage}
                        disabled={isLoading}
                    />
                </div>
            ) : null}
        </div>
    );
}

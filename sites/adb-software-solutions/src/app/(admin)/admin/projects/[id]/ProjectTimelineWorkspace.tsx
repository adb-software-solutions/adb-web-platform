"use client";

import { Badge, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type Zoom = "day" | "week" | "month";

interface TimelineTask {
    id: number;
    title: string;
    start_date: string | null;
    due_date: string | null;
    completed: boolean;
    priority: number;
    assigned_to_name: string | null;
    parent_task_id: number | null;
    blocked_by_ids: number[];
}

interface TimelineResponse {
    project_id: number;
    project_name: string;
    tasks: TimelineTask[];
}

interface PositionedTask {
    task: TimelineTask;
    left: number;
    width: number;
    row: number;
}

const DAY_MS = 86_400_000;
const LABEL_WIDTH = 280;
const ROW_HEIGHT = 58;

const zoomOptions: Array<{
    value: Zoom;
    label: string;
    pixelsPerDay: number;
    tickDays: number;
}> = [
    { value: "day", label: "Day", pixelsPerDay: 42, tickDays: 1 },
    { value: "week", label: "Week", pixelsPerDay: 18, tickDays: 7 },
    { value: "month", label: "Month", pixelsPerDay: 7, tickDays: 30 },
];

function dayStamp(value: string) {
    return new Date(`${value}T00:00:00`).getTime();
}

function isoDate(stamp: number) {
    const date = new Date(stamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function formatDate(value: string | null) {
    if (!value) return "—";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatTick(stamp: number, zoom: Zoom) {
    return new Intl.DateTimeFormat("en-GB", {
        day: zoom === "month" ? undefined : "2-digit",
        month: "short",
        year: zoom === "month" ? "2-digit" : undefined,
    }).format(new Date(stamp));
}

function priorityLabel(priority: number) {
    return ["", "Low", "Medium", "High", "Critical"][priority] || "Medium";
}

export function ProjectTimelineWorkspace({ projectId }: { projectId: number }) {
    const [data, setData] = useState<TimelineResponse | null>(null);
    const [zoom, setZoom] = useState<Zoom>("week");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            setData(
                (await fetchAPI(
                    `${API_URL}/api/admin/task-timeline/projects/${projectId}`,
                )) as TimelineResponse,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load project timeline.",
            );
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        const stored = window.localStorage.getItem(`project-timeline-zoom:${projectId}`);
        if (stored === "day" || stored === "week" || stored === "month") setZoom(stored);
        void load();
    }, [load, projectId]);

    function changeZoom(next: Zoom) {
        setZoom(next);
        window.localStorage.setItem(`project-timeline-zoom:${projectId}`, next);
    }

    const timeline = useMemo(() => {
        if (!data?.tasks.length) return null;
        const dateValues = data.tasks.flatMap((task) => [task.start_date, task.due_date]).filter(Boolean) as string[];
        const stamps = dateValues.map(dayStamp);
        const start = Math.min(...stamps) - 3 * DAY_MS;
        const end = Math.max(...stamps) + 4 * DAY_MS;
        const totalDays = Math.max(7, Math.ceil((end - start) / DAY_MS));
        const zoomConfig = zoomOptions.find((option) => option.value === zoom) ?? zoomOptions[1];
        const width = Math.max(900, totalDays * zoomConfig.pixelsPerDay);
        const pixelsPerDay = width / totalDays;

        const positioned = data.tasks.map<PositionedTask>((task, row) => {
            const taskStart = dayStamp(task.start_date || task.due_date || isoDate(start));
            const taskEnd = dayStamp(task.due_date || task.start_date || isoDate(start)) + DAY_MS;
            return {
                task,
                row,
                left: ((taskStart - start) / DAY_MS) * pixelsPerDay,
                width: Math.max(12, ((taskEnd - taskStart) / DAY_MS) * pixelsPerDay),
            };
        });
        const positions = new Map(positioned.map((item) => [item.task.id, item]));
        const connectors = positioned.flatMap((target) =>
            target.task.blocked_by_ids.flatMap((blockingId) => {
                const source = positions.get(blockingId);
                return source ? [{ source, target }] : [];
            }),
        );
        const ticks: Array<{ stamp: number; left: number }> = [];
        for (let day = 0; day <= totalDays; day += zoomConfig.tickDays) {
            ticks.push({
                stamp: start + day * DAY_MS,
                left: day * pixelsPerDay,
            });
        }
        return {
            start,
            end,
            totalDays,
            width,
            pixelsPerDay,
            tickDays: zoomConfig.tickDays,
            positioned,
            connectors,
            ticks,
        };
    }, [data, zoom]);

    if (loading && !data) return <DataLoading label="Loading project timeline..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <section className="space-y-5">
            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-white">Project timeline</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        Plan dated work and see blocker relationships across the delivery sequence.
                    </p>
                </div>
                <div className="inline-flex w-fit rounded-lg border border-slate-800 bg-slate-900 p-1">
                    {zoomOptions.map((option) => (
                        <button
                            key={option.value}
                            type="button"
                            onClick={() => changeZoom(option.value)}
                            className={`rounded-md px-3 py-2 text-xs font-medium transition ${
                                zoom === option.value
                                    ? "bg-slate-700 text-white"
                                    : "text-slate-500 hover:text-slate-200"
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>

            {!timeline || !data?.tasks.length ? (
                <EmptyState
                    title="No dated project tasks"
                    description="Add a start date, due date or both to tasks to build the project timeline."
                />
            ) : (
                <Card className="overflow-hidden">
                    <div className="overflow-x-auto">
                        <div style={{ width: `${LABEL_WIDTH + timeline.width}px` }}>
                            <div className="flex h-12 border-b border-slate-800 bg-slate-900/80">
                                <div
                                    className="sticky left-0 z-30 flex shrink-0 items-center border-r border-slate-800 bg-slate-900 px-4 text-xs font-semibold uppercase tracking-wide text-slate-500"
                                    style={{ width: `${LABEL_WIDTH}px` }}
                                >
                                    Task
                                </div>
                                <div className="relative h-12" style={{ width: `${timeline.width}px` }}>
                                    {timeline.ticks.map((tick) => (
                                        <div
                                            key={tick.stamp}
                                            className="absolute inset-y-0 border-l border-slate-800/80 px-2 pt-3 text-[10px] text-slate-600"
                                            style={{ left: `${tick.left}px` }}
                                        >
                                            {formatTick(tick.stamp, zoom)}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div
                                className="relative"
                                style={{ height: `${timeline.positioned.length * ROW_HEIGHT}px` }}
                            >
                                <svg
                                    className="pointer-events-none absolute z-10"
                                    style={{
                                        left: `${LABEL_WIDTH}px`,
                                        top: 0,
                                        width: `${timeline.width}px`,
                                        height: `${timeline.positioned.length * ROW_HEIGHT}px`,
                                    }}
                                    width={timeline.width}
                                    height={timeline.positioned.length * ROW_HEIGHT}
                                    aria-hidden="true"
                                >
                                    <defs>
                                        <marker
                                            id={`timeline-arrow-${projectId}`}
                                            viewBox="0 0 10 10"
                                            refX="9"
                                            refY="5"
                                            markerWidth="6"
                                            markerHeight="6"
                                            orient="auto-start-reverse"
                                        >
                                            <path d="M 0 0 L 10 5 L 0 10 z" className="fill-slate-500" />
                                        </marker>
                                    </defs>
                                    {timeline.connectors.map(({ source, target }) => {
                                        const sourceX = source.left + source.width;
                                        const sourceY = source.row * ROW_HEIGHT + ROW_HEIGHT / 2;
                                        const targetX = target.left;
                                        const targetY = target.row * ROW_HEIGHT + ROW_HEIGHT / 2;
                                        const elbowX =
                                            targetX > sourceX + 24
                                                ? sourceX + (targetX - sourceX) / 2
                                                : sourceX + 24;
                                        return (
                                            <path
                                                key={`${source.task.id}:${target.task.id}`}
                                                d={`M ${sourceX} ${sourceY} H ${elbowX} V ${targetY} H ${targetX}`}
                                                className="fill-none stroke-slate-600"
                                                strokeWidth="1.5"
                                                markerEnd={`url(#timeline-arrow-${projectId})`}
                                            />
                                        );
                                    })}
                                </svg>

                                {timeline.positioned.map(({ task, left, width, row }) => (
                                    <div
                                        key={task.id}
                                        className="absolute left-0 flex border-b border-slate-800/80"
                                        style={{
                                            top: `${row * ROW_HEIGHT}px`,
                                            width: `${LABEL_WIDTH + timeline.width}px`,
                                            height: `${ROW_HEIGHT}px`,
                                        }}
                                    >
                                        <div
                                            className="sticky left-0 z-30 flex shrink-0 items-center gap-3 border-r border-slate-800 bg-slate-950 px-4"
                                            style={{ width: `${LABEL_WIDTH}px` }}
                                        >
                                            <div className="min-w-0 flex-1">
                                                <Link
                                                    href={`/admin/tasks/${task.id}`}
                                                    className={`block truncate text-sm font-medium hover:text-adb-cyan-300 ${
                                                        task.completed
                                                            ? "text-slate-600 line-through"
                                                            : "text-slate-200"
                                                    }`}
                                                >
                                                    {task.parent_task_id ? "↳ " : ""}
                                                    {task.title}
                                                </Link>
                                                <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-600">
                                                    <span>{task.assigned_to_name || "Unassigned"}</span>
                                                    <span>· {priorityLabel(task.priority)}</span>
                                                    {task.blocked_by_ids.length ? (
                                                        <Badge className="px-1.5 py-0 text-[9px]">Blocked</Badge>
                                                    ) : null}
                                                </div>
                                            </div>
                                        </div>
                                        <div
                                            className="relative z-20 shrink-0 bg-[linear-gradient(to_right,rgba(51,65,85,0.18)_1px,transparent_1px)]"
                                            style={{
                                                width: `${timeline.width}px`,
                                                backgroundSize: `${timeline.pixelsPerDay * timeline.tickDays}px 100%`,
                                            }}
                                        >
                                            <Link
                                                href={`/admin/tasks/${task.id}`}
                                                className={`absolute top-4 flex h-7 items-center rounded-md border px-2 text-[11px] shadow-sm transition hover:brightness-125 ${
                                                    task.completed
                                                        ? "border-emerald-900/60 bg-emerald-950/60 text-emerald-400"
                                                        : task.blocked_by_ids.length
                                                          ? "border-amber-800/60 bg-amber-950/70 text-amber-300"
                                                          : "border-adb-cyan-500/40 bg-adb-cyan-500/20 text-adb-cyan-200"
                                                }`}
                                                style={{
                                                    left: `${left}px`,
                                                    width: `${width}px`,
                                                    minWidth: "12px",
                                                }}
                                                title={`${formatDate(task.start_date)} – ${formatDate(task.due_date)}`}
                                            >
                                                <span className="truncate">{task.title}</span>
                                            </Link>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </Card>
            )}
        </section>
    );
}

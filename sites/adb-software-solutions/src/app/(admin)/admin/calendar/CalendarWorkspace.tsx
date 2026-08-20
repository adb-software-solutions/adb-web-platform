"use client";

import { Badge, Button, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type CalendarKind = "task" | "project";
type CalendarFilter = "all" | CalendarKind;

interface CalendarItem {
    kind: CalendarKind;
    id: number;
    title: string;
    start_date: string;
    end_date: string;
    status: string;
    completed: boolean;
    client_id: number | null;
    client_name: string | null;
    project_id: number | null;
    project_name: string | null;
}

interface CalendarResponse {
    date_from: string;
    date_to: string;
    items: CalendarItem[];
    task_count: number;
    project_count: number;
}

const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function localDate(year: number, month: number, day: number) {
    return new Date(year, month, day, 12, 0, 0, 0);
}

function isoDate(value: Date) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, "0");
    const day = String(value.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function addDays(value: Date, days: number) {
    const next = new Date(value);
    next.setDate(next.getDate() + days);
    return next;
}

function monthGrid(anchor: Date) {
    const first = localDate(anchor.getFullYear(), anchor.getMonth(), 1);
    const mondayOffset = (first.getDay() + 6) % 7;
    const start = addDays(first, -mondayOffset);
    return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

function itemHref(item: CalendarItem) {
    return item.kind === "task" ? `/admin/tasks/${item.id}` : `/admin/projects/${item.id}`;
}

function itemContext(item: CalendarItem) {
    if (item.kind === "task" && item.project_name) return item.project_name;
    return item.client_name || "ADB Internal";
}

export function CalendarWorkspace() {
    const [anchor, setAnchor] = useState(() => new Date());
    const [filter, setFilter] = useState<CalendarFilter>("all");
    const [data, setData] = useState<CalendarResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const days = useMemo(() => monthGrid(anchor), [anchor]);
    const dateFrom = isoDate(days[0]);
    const dateTo = isoDate(days[days.length - 1]);
    const currentMonth = anchor.getMonth();
    const today = isoDate(new Date());

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const query = new URLSearchParams({
                date_from: dateFrom,
                date_to: dateTo,
            });
            setData(
                (await fetchAPI(`${API_URL}/api/admin/calendar?${query.toString()}`)) as CalendarResponse,
            );
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load the calendar.");
        } finally {
            setLoading(false);
        }
    }, [dateFrom, dateTo]);

    useEffect(() => {
        void load();
    }, [load]);

    const visibleItems = useMemo(
        () => data?.items.filter((item) => filter === "all" || item.kind === filter) ?? [],
        [data, filter],
    );

    function moveMonth(offset: number) {
        setAnchor((current) => localDate(current.getFullYear(), current.getMonth() + offset, 1));
    }

    if (loading && !data) return <DataLoading label="Loading work calendar..." />;
    if (error && !data) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <div className="space-y-5">
            {error ? (
                <div className="rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}

            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                    <Button variant="outline" onClick={() => moveMonth(-1)} aria-label="Previous month">
                        ←
                    </Button>
                    <div className="min-w-48 text-center text-xl font-semibold text-white">
                        {new Intl.DateTimeFormat("en-GB", {
                            month: "long",
                            year: "numeric",
                        }).format(anchor)}
                    </div>
                    <Button variant="outline" onClick={() => moveMonth(1)} aria-label="Next month">
                        →
                    </Button>
                    <Button variant="ghost" onClick={() => setAnchor(new Date())}>
                        Today
                    </Button>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {(
                        [
                            ["all", "All work"],
                            ["task", `Tasks (${data?.task_count ?? 0})`],
                            ["project", `Projects (${data?.project_count ?? 0})`],
                        ] as Array<[CalendarFilter, string]>
                    ).map(([value, label]) => (
                        <button
                            key={value}
                            type="button"
                            onClick={() => setFilter(value)}
                            className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                                filter === value
                                    ? "border-adb-cyan-700 bg-adb-cyan-950/30 text-adb-cyan-200"
                                    : "border-slate-800 bg-slate-900 text-slate-500 hover:text-slate-300"
                            }`}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            <Card className="overflow-hidden">
                <div className="grid grid-cols-7 border-b border-slate-800 bg-slate-900/70">
                    {weekdayLabels.map((label) => (
                        <div
                            key={label}
                            className="border-r border-slate-800 px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-500 last:border-r-0"
                        >
                            {label}
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-7">
                    {days.map((day, index) => {
                        const dateKey = isoDate(day);
                        const items = visibleItems.filter(
                            (item) => item.start_date <= dateKey && item.end_date >= dateKey,
                        );
                        const inMonth = day.getMonth() === currentMonth;
                        const isToday = dateKey === today;
                        return (
                            <div
                                key={dateKey}
                                className={`min-h-36 border-b border-r border-slate-800 p-2 ${
                                    index % 7 === 6 ? "border-r-0" : ""
                                } ${index >= 35 ? "border-b-0" : ""} ${
                                    inMonth ? "bg-slate-950" : "bg-slate-950/45"
                                }`}
                            >
                                <div className="mb-2 flex items-center justify-between">
                                    <span
                                        className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
                                            isToday
                                                ? "bg-adb-cyan-500 text-slate-950"
                                                : inMonth
                                                  ? "text-slate-300"
                                                  : "text-slate-700"
                                        }`}
                                    >
                                        {day.getDate()}
                                    </span>
                                </div>
                                <div className="space-y-1">
                                    {items.slice(0, 4).map((item) => (
                                        <Link
                                            key={`${item.kind}-${item.id}`}
                                            href={itemHref(item)}
                                            title={`${item.title} · ${itemContext(item)}`}
                                            className={`block truncate rounded-md border px-2 py-1.5 text-[11px] transition hover:brightness-125 ${
                                                item.kind === "project"
                                                    ? "border-indigo-900/70 bg-indigo-950/35 text-indigo-200"
                                                    : item.completed
                                                      ? "border-emerald-900/50 bg-emerald-950/20 text-emerald-400 line-through"
                                                      : "border-slate-700 bg-slate-900 text-slate-300"
                                            }`}
                                        >
                                            <span className="mr-1 text-[9px] font-bold uppercase opacity-60">
                                                {item.kind === "project" ? "P" : "T"}
                                            </span>
                                            {item.title}
                                        </Link>
                                    ))}
                                    {items.length > 4 ? (
                                        <div className="px-2 py-1 text-[10px] text-slate-600">
                                            +{items.length - 4} more
                                        </div>
                                    ) : null}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </Card>

            {!loading && visibleItems.length === 0 ? (
                <EmptyState
                    title="Nothing scheduled in this view"
                    description="Dated Tasks and Projects will appear here. Change month or filter to inspect another part of the schedule."
                />
            ) : null}

            <div className="flex flex-wrap gap-2 text-xs text-slate-600">
                <Badge>Task</Badge>
                <Badge>Project</Badge>
                <span>
                    Task spans use start and due dates. Project spans use project start and end dates.
                </span>
            </div>
        </div>
    );
}

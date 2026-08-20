"use client";

import { ButtonLink, Card, DataError, DataLoading, EmptyState } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { useCallback, useEffect, useState } from "react";

type TimeContextType = "task" | "ticket";

interface RelatedTimeEntry {
    id: number;
    date: string;
    duration_hours: string;
    description: string;
    billable: boolean;
    user_name: string | null;
}

interface RelatedTimePage {
    items: RelatedTimeEntry[];
    total: number;
    tracked_hours: string;
    billable_hours: string;
}

interface TimeOptions {
    can_add_time: boolean;
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T00:00:00`));
}

function formatHours(value: string) {
    return `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}h`;
}

export function RelatedTimePanel({
    contextType,
    contextId,
    title = "Time tracked",
}: {
    contextType: TimeContextType;
    contextId: number;
    title?: string;
}) {
    const [data, setData] = useState<RelatedTimePage | null>(null);
    const [canAddTicketTime, setCanAddTicketTime] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const params = new URLSearchParams({
                [`${contextType}_id`]: String(contextId),
                page_size: "5",
            });
            const timeData = (await fetchAPI(
                AdminAPI.timeEntries.list(params.toString()),
            )) as RelatedTimePage;
            setData(timeData);

            if (contextType === "ticket") {
                const options = (await fetchAPI(AdminAPI.timeEntries.options())) as TimeOptions;
                setCanAddTicketTime(options.can_add_time);
            } else {
                setCanAddTicketTime(false);
            }
        } catch (loadError) {
            setError(
                loadError instanceof Error ? loadError.message : "Unable to load related time entries.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [contextId, contextType]);

    useEffect(() => {
        void load();
    }, [load]);

    if (isLoading) return <DataLoading label="Loading tracked time..." />;
    if (error) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <Card className="overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-slate-800 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-sm font-semibold text-white">{title}</h2>
                    <p className="mt-1 text-xs text-slate-500">
                        {formatHours(data?.tracked_hours ?? "0")} tracked · {formatHours(
                            data?.billable_hours ?? "0",
                        )} billable
                    </p>
                </div>
                {canAddTicketTime ? (
                    <ButtonLink
                        href={`/admin/time-tracking?ticket_id=${contextId}&mode=manual#record-time`}
                        variant="outline"
                    >
                        Add time
                    </ButtonLink>
                ) : null}
            </div>

            {!data || data.items.length === 0 ? (
                <EmptyState
                    title="No time recorded"
                    description="Manual entries and stopped timers for this work item will appear here."
                />
            ) : (
                <div className="divide-y divide-slate-800">
                    {data.items.map((entry) => (
                        <div key={entry.id} className="flex items-start justify-between gap-4 px-5 py-4">
                            <div className="min-w-0">
                                <div className="text-sm font-medium text-slate-200">
                                    {entry.description || "Tracked work"}
                                </div>
                                <div className="mt-1 text-xs text-slate-500">
                                    {formatDate(entry.date)} · {entry.user_name || "Unknown staff"} · {entry.billable ? "Billable" : "Non-billable"}
                                </div>
                            </div>
                            <div className="shrink-0 font-semibold tabular-nums text-slate-200">
                                {formatHours(entry.duration_hours)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </Card>
    );
}

"use client";

import { Button, ButtonLink, Card } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { useCallback, useEffect, useMemo, useState } from "react";

interface RunningTimer {
    id: number;
    started_at: string;
    elapsed_seconds: number;
    description: string;
    task_id: number | null;
    task_title: string | null;
    ticket_reference: string | null;
    ticket_subject: string | null;
    project_name: string | null;
    client_name: string | null;
}

function formatElapsed(seconds: number) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remaining = seconds % 60;
    return [hours, minutes, remaining]
        .map((value) => String(value).padStart(2, "0"))
        .join(":");
}

function timerContext(timer: RunningTimer) {
    if (timer.task_title) return timer.task_title;
    if (timer.ticket_reference) {
        return `${timer.ticket_reference}${timer.ticket_subject ? ` · ${timer.ticket_subject}` : ""}`;
    }
    return timer.project_name || timer.client_name || timer.description || "Internal work";
}

export function TaskTimerControl({
    taskId,
    onTimeChanged,
}: {
    taskId: number;
    onTimeChanged?: () => void;
}) {
    const { hasPermission } = useAuth();
    const [timer, setTimer] = useState<RunningTimer | null>(null);
    const [now, setNow] = useState(() => Date.now());
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const canViewTime = hasPermission("clients.view_timeentry");
    const canAddTime = hasPermission("clients.add_timeentry");

    const load = useCallback(async () => {
        if (!canViewTime) {
            setLoading(false);
            return;
        }
        try {
            setError(null);
            setTimer((await fetchAPI(AdminAPI.timeEntries.timer.current())) as RunningTimer | null);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load the current timer.");
        } finally {
            setLoading(false);
        }
    }, [canViewTime]);

    useEffect(() => {
        void load();
    }, [load]);

    useEffect(() => {
        if (!timer) return;
        const interval = window.setInterval(() => setNow(Date.now()), 1000);
        return () => window.clearInterval(interval);
    }, [timer]);

    const elapsed = useMemo(() => {
        if (!timer) return 0;
        const startedAt = new Date(timer.started_at).getTime();
        if (Number.isNaN(startedAt)) return timer.elapsed_seconds;
        return Math.max(timer.elapsed_seconds, Math.floor((now - startedAt) / 1000));
    }, [now, timer]);

    async function start() {
        setSaving(true);
        setError(null);
        try {
            const data = (await fetchAPI(AdminAPI.timeEntries.timer.start(), {
                method: "POST",
                body: JSON.stringify({
                    ownership_type: "internal",
                    task_id: taskId,
                    billable: true,
                    description: "",
                }),
            })) as RunningTimer;
            setTimer(data);
            setNow(Date.now());
            onTimeChanged?.();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to start the timer.");
            await load();
        } finally {
            setSaving(false);
        }
    }

    async function stop() {
        setSaving(true);
        setError(null);
        try {
            await fetchAPI(AdminAPI.timeEntries.timer.stop(), {
                method: "POST",
                body: JSON.stringify({}),
            });
            setTimer(null);
            onTimeChanged?.();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to stop the timer.");
            await load();
        } finally {
            setSaving(false);
        }
    }

    if (!canViewTime) return null;

    const runningForTask = timer?.task_id === taskId;

    return (
        <Card className="p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Active timer
                    </div>
                    {loading ? (
                        <div className="mt-1 text-sm text-slate-600">Checking timer…</div>
                    ) : runningForTask && timer ? (
                        <div className="mt-1 flex items-baseline gap-3">
                            <span className="font-mono text-2xl font-semibold tabular-nums text-white">
                                {formatElapsed(elapsed)}
                            </span>
                            <span className="text-sm text-emerald-400">Tracking this task</span>
                        </div>
                    ) : timer ? (
                        <div className="mt-1 text-sm text-slate-300">
                            Already tracking <span className="font-medium text-white">{timerContext(timer)}</span>
                        </div>
                    ) : (
                        <div className="mt-1 text-sm text-slate-500">
                            Start tracking without leaving the task.
                        </div>
                    )}
                    {error ? <div className="mt-2 text-xs text-red-300">{error}</div> : null}
                </div>

                <div className="flex shrink-0 gap-2">
                    {runningForTask ? (
                        <Button type="button" disabled={saving} onClick={() => void stop()}>
                            {saving ? "Stopping…" : "Stop timer"}
                        </Button>
                    ) : timer ? (
                        <ButtonLink href="/admin/time-tracking" variant="outline">
                            View running timer
                        </ButtonLink>
                    ) : canAddTime ? (
                        <Button type="button" disabled={saving || loading} onClick={() => void start()}>
                            {saving ? "Starting…" : "Start timer"}
                        </Button>
                    ) : null}
                </div>
            </div>
        </Card>
    );
}

"use client";

import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { MouseEvent, useState } from "react";

export function TaskCompletionToggle({
    taskId,
    completed,
    canChange,
    onChanged,
    onError,
    size = "md",
}: {
    taskId: number;
    completed: boolean;
    canChange: boolean;
    onChanged: () => Promise<void> | void;
    onError?: (message: string) => void;
    size?: "sm" | "md";
}) {
    const [saving, setSaving] = useState(false);
    const dimension = size === "sm" ? "h-6 w-6 text-[10px]" : "h-7 w-7 text-xs";

    async function toggle(event: MouseEvent<HTMLButtonElement>) {
        event.preventDefault();
        event.stopPropagation();
        if (!canChange || saving) return;

        setSaving(true);
        try {
            await fetchAPI(
                completed ? AdminAPI.tasks.reopen(taskId) : AdminAPI.tasks.complete(taskId),
                { method: "POST" },
            );
            await onChanged();
        } catch (toggleError) {
            const message =
                toggleError instanceof Error
                    ? toggleError.message
                    : "Unable to update task completion.";
            if (onError) onError(message);
            else window.alert(message);
        } finally {
            setSaving(false);
        }
    }

    if (!canChange) {
        return completed ? (
            <span
                className={`flex shrink-0 items-center justify-center rounded-full border border-emerald-900/60 bg-emerald-950/40 text-emerald-400 ${dimension}`}
                title="Completed"
            >
                ✓
            </span>
        ) : null;
    }

    return (
        <button
            type="button"
            onClick={(event) => void toggle(event)}
            disabled={saving}
            className={`flex shrink-0 items-center justify-center rounded-full border transition ${dimension} ${
                completed
                    ? "border-emerald-700 bg-emerald-950/50 text-emerald-300 hover:border-emerald-500"
                    : "border-slate-700 text-transparent hover:border-emerald-500 hover:bg-emerald-500/10 hover:text-emerald-300"
            } disabled:cursor-wait disabled:opacity-50`}
            aria-label={completed ? "Reopen task" : "Complete task"}
            title={completed ? "Reopen task" : "Mark complete"}
        >
            ✓
        </button>
    );
}

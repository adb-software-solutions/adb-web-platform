"use client";

import { Button, Card, DataError, DataLoading, EmptyState, Textarea } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { FormEvent, useCallback, useEffect, useState } from "react";

interface TaskComment {
    id: number;
    task_id: number;
    author_id: string | null;
    author_name: string;
    body: string;
    created_at: string;
    updated_at: string;
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

function initials(name: string) {
    return name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("") || "?";
}

export function TaskDiscussionPanel({
    taskId,
    onChanged,
}: {
    taskId: number;
    onChanged?: () => void;
}) {
    const { hasPermission } = useAuth();
    const [comments, setComments] = useState<TaskComment[]>([]);
    const [body, setBody] = useState("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const endpoint = `${API_URL}/api/admin/task-comments/tasks/${taskId}`;
    const canComment = hasPermission("tasks.change_task");

    const load = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            setComments((await fetchAPI(endpoint)) as TaskComment[]);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load task discussion.");
        } finally {
            setLoading(false);
        }
    }, [endpoint]);

    useEffect(() => {
        void load();
    }, [load]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!body.trim()) return;
        setSaving(true);
        setError(null);
        try {
            const created = (await fetchAPI(endpoint, {
                method: "POST",
                body: JSON.stringify({ body: body.trim() }),
            })) as TaskComment;
            setComments((current) => [...current, created]);
            setBody("");
            onChanged?.();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to add comment.");
        } finally {
            setSaving(false);
        }
    }

    if (loading && comments.length === 0) return <DataLoading label="Loading discussion..." />;
    if (error && comments.length === 0) {
        return <DataError message={error} onRetry={() => void load()} />;
    }

    return (
        <Card className="overflow-hidden">
            <div className="border-b border-slate-800 px-5 py-4">
                <div className="flex items-center justify-between gap-3">
                    <div>
                        <h2 className="text-sm font-semibold text-white">Discussion</h2>
                        <p className="mt-1 text-xs text-slate-500">
                            Keep delivery decisions and task context with the work itself.
                        </p>
                    </div>
                    <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs tabular-nums text-slate-500">
                        {comments.length}
                    </span>
                </div>
            </div>

            {error ? <div className="border-b border-red-900/40 px-5 py-3 text-xs text-red-300">{error}</div> : null}

            {comments.length ? (
                <div className="divide-y divide-slate-800">
                    {comments.map((comment) => (
                        <article key={comment.id} className="flex gap-3 px-5 py-4">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-300">
                                {initials(comment.author_name)}
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                                    <span className="text-sm font-medium text-slate-200">{comment.author_name}</span>
                                    <span className="text-[11px] text-slate-600">{formatDate(comment.created_at)}</span>
                                </div>
                                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-300">
                                    {comment.body}
                                </p>
                            </div>
                        </article>
                    ))}
                </div>
            ) : (
                <EmptyState
                    title="No discussion yet"
                    description="Comments, delivery notes and decisions can stay attached to this task."
                />
            )}

            {canComment ? (
                <form onSubmit={(event) => void submit(event)} className="border-t border-slate-800 bg-slate-950/40 p-4">
                    <Textarea
                        value={body}
                        onChange={(event) => setBody(event.target.value)}
                        rows={3}
                        placeholder="Add a comment or delivery note..."
                    />
                    <div className="mt-3 flex justify-end">
                        <Button type="submit" disabled={saving || !body.trim()}>
                            {saving ? "Posting..." : "Comment"}
                        </Button>
                    </div>
                </form>
            ) : null}
        </Card>
    );
}

"use client";

import { Input } from "@/components/ui";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import { DragEvent, useCallback, useEffect, useState } from "react";

interface Section {
    id: number;
    name: string;
    sort_order: string;
}

interface Workspace {
    sections: Section[];
    can_change: boolean;
}

export function TaskListSectionManager({
    taskListId,
    onChanged,
}: {
    taskListId: number;
    onChanged: () => void;
}) {
    const [sections, setSections] = useState<Section[]>([]);
    const [names, setNames] = useState<Record<number, string>>({});
    const [canChange, setCanChange] = useState(false);
    const [draggedId, setDraggedId] = useState<number | null>(null);
    const [savingId, setSavingId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setError(null);
            const data = (await fetchAPI(AdminAPI.tasks.lists.workspace(taskListId))) as Workspace;
            setSections(data.sections);
            setNames(Object.fromEntries(data.sections.map((section) => [section.id, section.name])));
            setCanChange(data.can_change);
        } catch (loadError) {
            setError(loadError instanceof Error ? loadError.message : "Unable to load workflow columns.");
        }
    }, [taskListId]);

    useEffect(() => {
        void load();
    }, [load]);

    async function rename(section: Section) {
        const name = names[section.id]?.trim() ?? "";
        if (!name) {
            setNames((current) => ({ ...current, [section.id]: section.name }));
            return;
        }
        if (name === section.name) return;

        setSavingId(section.id);
        setError(null);
        try {
            await fetchAPI(`${AdminAPI.tasks.lists.sections(taskListId)}/${section.id}`, {
                method: "PATCH",
                body: JSON.stringify({ name }),
            });
            await load();
            onChanged();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to rename section.");
            setNames((current) => ({ ...current, [section.id]: section.name }));
        } finally {
            setSavingId(null);
        }
    }

    async function move(
        sectionId: number,
        beforeSectionId: number | null,
        afterSectionId: number | null,
    ) {
        setSavingId(sectionId);
        setError(null);
        try {
            await fetchAPI(`${AdminAPI.tasks.lists.sections(taskListId)}/${sectionId}/move`, {
                method: "POST",
                body: JSON.stringify({
                    before_section_id: beforeSectionId,
                    after_section_id: afterSectionId,
                }),
            });
            await load();
            onChanged();
        } catch (moveError) {
            setError(moveError instanceof Error ? moveError.message : "Unable to reorder sections.");
        } finally {
            setSavingId(null);
            setDraggedId(null);
        }
    }

    async function dropBefore(event: DragEvent, targetId: number) {
        event.preventDefault();
        event.stopPropagation();
        if (!draggedId || draggedId === targetId) return;
        const remaining = sections.filter((section) => section.id !== draggedId);
        const targetIndex = remaining.findIndex((section) => section.id === targetId);
        const previousId = targetIndex > 0 ? remaining[targetIndex - 1].id : null;
        await move(draggedId, previousId, targetId);
    }

    async function dropAtEnd(event: DragEvent) {
        event.preventDefault();
        if (!draggedId) return;
        const remaining = sections.filter((section) => section.id !== draggedId);
        await move(draggedId, remaining.at(-1)?.id ?? null, null);
    }

    if (!canChange || sections.length === 0) return null;

    return (
        <section className="rounded-xl border border-slate-800 bg-slate-900/35 p-4">
            <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-sm font-semibold text-white">Workflow columns</h2>
                    <p className="mt-0.5 text-xs text-slate-600">
                        Rename stages inline or drag them into the order this list should flow.
                    </p>
                </div>
                {savingId ? <span className="text-xs text-slate-600">Saving…</span> : null}
            </div>

            {error ? <div className="mb-3 text-xs text-red-300">{error}</div> : null}

            <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => void dropAtEnd(event)}
                className="flex min-w-0 gap-2 overflow-x-auto pb-1"
            >
                {sections.map((section) => (
                    <div
                        key={section.id}
                        draggable
                        onDragStart={(event) => {
                            setDraggedId(section.id);
                            event.dataTransfer.effectAllowed = "move";
                            event.dataTransfer.setData("text/plain", String(section.id));
                        }}
                        onDragEnd={() => setDraggedId(null)}
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={(event) => void dropBefore(event, section.id)}
                        className={`flex w-56 shrink-0 items-center gap-2 rounded-lg border bg-slate-950/70 px-2 py-2 transition ${
                            draggedId === section.id
                                ? "border-adb-cyan-500/50 opacity-40"
                                : "border-slate-800 hover:border-slate-700"
                        }`}
                    >
                        <span
                            className="cursor-grab select-none text-xs text-slate-600 active:cursor-grabbing"
                            title="Drag column"
                        >
                            ⋮⋮
                        </span>
                        <Input
                            value={names[section.id] ?? section.name}
                            disabled={savingId === section.id}
                            onChange={(event) =>
                                setNames((current) => ({
                                    ...current,
                                    [section.id]: event.target.value,
                                }))
                            }
                            onBlur={() => void rename(section)}
                            onKeyDown={(event) => {
                                if (event.key === "Enter") event.currentTarget.blur();
                                if (event.key === "Escape") {
                                    setNames((current) => ({
                                        ...current,
                                        [section.id]: section.name,
                                    }));
                                    event.currentTarget.blur();
                                }
                            }}
                            className="h-8 min-w-0 border-transparent bg-transparent px-1 text-sm font-medium text-slate-200 focus:border-slate-700 focus:bg-slate-900"
                            aria-label={`Rename ${section.name}`}
                        />
                    </div>
                ))}
                <div className="flex w-20 shrink-0 items-center justify-center rounded-lg border border-dashed border-slate-800 text-[11px] text-slate-700">
                    Drop end
                </div>
            </div>
        </section>
    );
}

"use client";

import { TaskRelationsPanel } from "@/app/(admin)/admin/tasks/TaskRelationsPanel";
import { TaskWorkspace } from "@/app/(admin)/admin/tasks/TaskWorkspace";
import { RelatedTimePanel } from "@/components/admin/RelatedTimePanel";
import { useEffect } from "react";

export function TaskDetailDrawer({
    taskId,
    onClose,
    onChanged,
}: {
    taskId: number | null;
    onClose: () => void;
    onChanged?: () => void;
}) {
    useEffect(() => {
        if (!taskId) return;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        function handleKeyDown(event: KeyboardEvent) {
            if (event.key === "Escape") onClose();
        }

        window.addEventListener("keydown", handleKeyDown);
        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [onClose, taskId]);

    if (!taskId) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <button
                type="button"
                aria-label="Close task details"
                onClick={onClose}
                className="absolute inset-0 bg-black/65 backdrop-blur-[1px]"
            />
            <aside className="relative h-full w-full overflow-y-auto border-l border-slate-800 bg-slate-950 shadow-2xl shadow-black/50 sm:max-w-3xl 2xl:max-w-5xl">
                <div className="space-y-6 p-5 sm:p-7">
                    <TaskWorkspace
                        taskId={taskId}
                        presentation="drawer"
                        onClose={onClose}
                        onChanged={onChanged}
                    />
                    <TaskRelationsPanel taskId={taskId} onChanged={onChanged} />
                    <RelatedTimePanel contextType="task" contextId={taskId} />
                </div>
            </aside>
        </div>
    );
}

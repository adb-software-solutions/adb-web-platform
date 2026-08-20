"use client";

import { ReactNode, useCallback, useEffect, useState } from "react";
import { TaskDetailDrawer } from "./TaskDetailDrawer";

const taskPathPattern = /^\/admin\/tasks\/(\d+)\/?$/;
const taskEditPathPattern = /^\/admin\/tasks\/(\d+)\/edit\/?$/;

export function TaskDrawerProvider({ children }: { children: ReactNode }) {
    const [taskId, setTaskId] = useState<number | null>(null);
    const [changed, setChanged] = useState(false);
    const [workspaceVersion, setWorkspaceVersion] = useState(0);

    const close = useCallback(() => {
        setTaskId(null);
        if (changed) {
            setWorkspaceVersion((version) => version + 1);
            setChanged(false);
        }
    }, [changed]);

    useEffect(() => {
        function handleClick(event: MouseEvent) {
            if (
                event.defaultPrevented ||
                event.button !== 0 ||
                event.metaKey ||
                event.ctrlKey ||
                event.shiftKey ||
                event.altKey
            ) {
                return;
            }

            const target = event.target;
            if (!(target instanceof Element)) return;
            const anchor = target.closest("a");
            if (!anchor || anchor.target === "_blank") return;

            const url = new URL(anchor.href, window.location.origin);
            if (url.origin !== window.location.origin) return;

            const editMatch = taskEditPathPattern.exec(url.pathname);
            if (
                editMatch &&
                Number(editMatch[1]) === taskId &&
                anchor.closest("[data-task-detail-drawer]") !== null
            ) {
                const editor = document.querySelector("[data-task-advanced-editor]");
                if (editor instanceof HTMLElement) {
                    event.preventDefault();
                    editor.scrollIntoView({ behavior: "smooth", block: "start" });
                }
                return;
            }

            const match = taskPathPattern.exec(url.pathname);
            if (!match) return;

            const linkedTaskId = Number(match[1]);
            if (
                linkedTaskId === taskId &&
                anchor.closest("[data-task-detail-drawer]") !== null
            ) {
                return;
            }

            event.preventDefault();
            setChanged(false);
            setTaskId(linkedTaskId);
        }

        document.addEventListener("click", handleClick, true);
        return () => document.removeEventListener("click", handleClick, true);
    }, [taskId]);

    return (
        <>
            <div key={workspaceVersion} className="contents">
                {children}
            </div>
            <TaskDetailDrawer
                taskId={taskId}
                onClose={close}
                onChanged={() => setChanged(true)}
            />
        </>
    );
}

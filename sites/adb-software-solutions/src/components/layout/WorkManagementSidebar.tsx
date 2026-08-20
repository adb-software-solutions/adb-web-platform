"use client";

import { useAuth } from "@/contexts/AuthContext";
import { AdminAPI } from "@/lib/api/endpoints";
import { fetchAPI } from "@/lib/api/fetch";
import {
    BanknotesIcon,
    FolderIcon,
    ListBulletIcon,
    RectangleStackIcon,
} from "@heroicons/react/24/outline";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

interface TaskListShortcut {
    id: number;
    name: string;
    project_name: string | null;
    client_name: string | null;
    open_task_count: number;
}

const primaryLinks = [
    { label: "Projects", href: "/admin/projects", icon: FolderIcon },
    { label: "My tasks", href: "/admin/tasks", icon: ListBulletIcon },
    { label: "Task lists", href: "/admin/task-lists", icon: RectangleStackIcon },
    { label: "Time tracking", href: "/admin/time-tracking", icon: BanknotesIcon },
];

const taskViews = [
    { label: "Today", href: "/admin/tasks?view=today" },
    { label: "Upcoming", href: "/admin/tasks?view=upcoming" },
    { label: "Overdue", href: "/admin/tasks?view=overdue" },
    { label: "Completed", href: "/admin/tasks?view=completed" },
    { label: "All tasks", href: "/admin/tasks?view=all" },
];

function active(pathname: string, href: string) {
    const hrefPath = href.split("?")[0];
    return pathname === hrefPath || pathname.startsWith(`${hrefPath}/`);
}

export function WorkManagementSidebar() {
    const pathname = usePathname();
    const { hasPermission } = useAuth();
    const [taskLists, setTaskLists] = useState<TaskListShortcut[]>([]);

    useEffect(() => {
        if (!hasPermission("tasks.view_tasklist")) return;

        let cancelled = false;
        void fetchAPI(AdminAPI.tasks.lists.list())
            .then((rows) => {
                if (!cancelled) setTaskLists(rows as TaskListShortcut[]);
            })
            .catch(() => {
                if (!cancelled) setTaskLists([]);
            });
        return () => {
            cancelled = true;
        };
    }, [hasPermission]);

    return (
        <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-800 bg-slate-950/70 xl:flex">
            <div className="border-b border-slate-800 px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Work management
                </div>
                <div className="mt-1 text-sm font-semibold text-white">Plan & deliver</div>
            </div>

            <nav className="flex-1 overflow-y-auto p-3">
                <div className="space-y-1">
                    {primaryLinks.map((item) => {
                        const Icon = item.icon;
                        const isActive = active(pathname, item.href);
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                                    isActive
                                        ? "bg-slate-800 text-white"
                                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                                }`}
                            >
                                <Icon
                                    className={`h-4 w-4 ${
                                        isActive ? "text-adb-cyan-400" : "text-slate-500"
                                    }`}
                                />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </div>

                {hasPermission("tasks.view_task") ? (
                    <div className="mt-6 border-t border-slate-900 pt-5">
                        <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600">
                            Task views
                        </div>
                        <div className="space-y-0.5">
                            {taskViews.map((view) => (
                                <Link
                                    key={view.href}
                                    href={view.href}
                                    className="block rounded-lg px-3 py-1.5 text-sm text-slate-500 transition hover:bg-slate-900 hover:text-slate-200"
                                >
                                    {view.label}
                                </Link>
                            ))}
                        </div>
                    </div>
                ) : null}

                {taskLists.length > 0 ? (
                    <div className="mt-7">
                        <div className="mb-2 flex items-center justify-between px-3">
                            <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-600">
                                Task lists
                            </span>
                            <Link
                                href="/admin/task-lists"
                                className="text-[11px] text-slate-500 hover:text-slate-300"
                            >
                                View all
                            </Link>
                        </div>
                        <div className="space-y-1">
                            {taskLists.slice(0, 12).map((taskList) => {
                                const href = `/admin/task-lists/${taskList.id}`;
                                const isActive = active(pathname, href);
                                return (
                                    <Link
                                        key={taskList.id}
                                        href={href}
                                        className={`block rounded-lg px-3 py-2 transition ${
                                            isActive
                                                ? "bg-slate-800 text-white"
                                                : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                                        }`}
                                    >
                                        <div className="truncate text-sm font-medium">{taskList.name}</div>
                                        <div className="mt-0.5 flex items-center justify-between gap-2 text-[11px] text-slate-600">
                                            <span className="truncate">
                                                {taskList.project_name || taskList.client_name || "ADB Internal"}
                                            </span>
                                            <span className="shrink-0">{taskList.open_task_count}</span>
                                        </div>
                                    </Link>
                                );
                            })}
                        </div>
                    </div>
                ) : null}
            </nav>
        </aside>
    );
}

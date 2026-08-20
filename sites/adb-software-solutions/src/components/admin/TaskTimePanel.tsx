"use client";

import { useState } from "react";
import { RelatedTimePanel } from "./RelatedTimePanel";
import { TaskTimerControl } from "./TaskTimerControl";

export function TaskTimePanel({
    taskId,
    onChanged,
}: {
    taskId: number;
    onChanged?: () => void;
}) {
    const [version, setVersion] = useState(0);

    function handleTimeChanged() {
        setVersion((value) => value + 1);
        onChanged?.();
    }

    return (
        <div className="space-y-6">
            <TaskTimerControl taskId={taskId} onTimeChanged={handleTimeChanged} />
            <RelatedTimePanel key={version} contextType="task" contextId={taskId} />
        </div>
    );
}

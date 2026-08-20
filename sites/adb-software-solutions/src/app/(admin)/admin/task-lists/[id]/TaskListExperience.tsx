"use client";

import { useState } from "react";
import { TaskListSectionManager } from "./TaskListSectionManager";
import { TaskListWorkspaceView } from "./TaskListWorkspaceView";

export function TaskListExperience({ taskListId }: { taskListId: number }) {
    const [version, setVersion] = useState(0);

    return (
        <div className="space-y-6">
            <TaskListSectionManager
                taskListId={taskListId}
                onChanged={() => setVersion((value) => value + 1)}
            />
            <TaskListWorkspaceView key={version} taskListId={taskListId} />
        </div>
    );
}

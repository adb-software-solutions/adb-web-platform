import { RelatedTimePanel } from "@/components/admin/RelatedTimePanel";
import { Container } from "@/components/ui";
import { TaskRelationsPanel } from "../TaskRelationsPanel";
import { TaskWorkspace } from "../TaskWorkspace";

export const metadata = {
    title: "Task",
};

export default async function TaskPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const taskId = Number(id);

    return (
        <Container className="py-8">
            <div className="space-y-6">
                <TaskWorkspace taskId={taskId} />
                <TaskRelationsPanel taskId={taskId} />
                <RelatedTimePanel contextType="task" contextId={taskId} />
            </div>
        </Container>
    );
}

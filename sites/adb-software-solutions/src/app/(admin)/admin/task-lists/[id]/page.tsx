import { Container } from "@/components/ui";
import { TaskListWorkspaceView } from "./TaskListWorkspaceView";

export const metadata = {
    title: "Task List",
};

export default async function TaskListPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    return (
        <Container className="py-8">
            <TaskListWorkspaceView taskListId={Number(id)} />
        </Container>
    );
}

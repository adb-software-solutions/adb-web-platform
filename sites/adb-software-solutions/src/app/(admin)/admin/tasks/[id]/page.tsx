import { Container } from "@/components/ui";
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
    return (
        <Container className="py-8">
            <TaskWorkspace taskId={Number(id)} />
        </Container>
    );
}

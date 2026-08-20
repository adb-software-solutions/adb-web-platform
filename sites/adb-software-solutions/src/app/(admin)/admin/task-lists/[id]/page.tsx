import { Container } from "@/components/ui";
import { TaskListExperience } from "./TaskListExperience";

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
            <TaskListExperience taskListId={Number(id)} />
        </Container>
    );
}

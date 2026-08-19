import { Container, PageHeader } from "@/components/ui";
import { TaskListsWorkspace } from "./TaskListsWorkspace";

export const metadata = {
    title: "Task Lists",
};

export default function TaskListsPage() {
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Tasks"
                title="Task lists"
                description="Organise standalone, client and project tasks without requiring every task to belong to a project."
            />
            <div className="mt-6">
                <TaskListsWorkspace />
            </div>
        </Container>
    );
}

import { ButtonLink, Container, PageHeader } from "@/components/ui";
import { TaskList } from "./TaskList";

export const metadata = {
    title: "Tasks",
};

export default function TasksPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Tasks"
                description="Plan client delivery, internal work and recurring operational tasks."
                actions={<ButtonLink href="/admin/tasks/new">Add task</ButtonLink>}
            />
            <div className="mt-6">
                <TaskList />
            </div>
        </Container>
    );
}

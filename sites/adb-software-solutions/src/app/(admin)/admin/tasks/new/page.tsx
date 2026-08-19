import { Card, Container, PageHeader } from "@/components/ui";
import { TaskForm } from "../TaskForm";

export const metadata = {
    title: "New Task",
};

export default function NewTaskPage() {
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Tasks"
                title="Create task"
                description="Create client delivery work, an internal task or a recurring operational task."
            />
            <Card className="mt-6 p-6">
                <TaskForm />
            </Card>
        </Container>
    );
}

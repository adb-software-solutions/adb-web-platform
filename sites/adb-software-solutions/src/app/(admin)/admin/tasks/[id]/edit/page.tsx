import { Card, Container, DataLoading, PageHeader } from "@/components/ui";
import { Suspense } from "react";
import { TaskForm } from "../../TaskForm";

export const metadata = {
    title: "Edit Task",
};

export default async function EditTaskPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Tasks"
                title="Edit task"
                description="Update task context, assignment, priority, due date and recurrence."
            />
            <Card className="mt-6 p-6">
                <Suspense fallback={<DataLoading label="Loading task details..." />}>
                    <TaskForm taskId={Number(id)} />
                </Suspense>
            </Card>
        </Container>
    );
}

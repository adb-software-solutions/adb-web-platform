import { Container, DataLoading, PageHeader } from "@/components/ui";
import { Suspense } from "react";
import { TaskList } from "./TaskList";

export const metadata = {
    title: "Tasks",
};

export default function TasksPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Tasks"
                description="Focus on your work first, then move out into project, client and business-wide planning when you need it."
            />
            <div className="mt-6">
                <Suspense fallback={<DataLoading label="Loading task workspace..." />}>
                    <TaskList />
                </Suspense>
            </div>
        </Container>
    );
}

import { Container, DataLoading, PageHeader } from "@/components/ui";
import { Suspense } from "react";
import { TimeTrackingWorkspace } from "./TimeTrackingWorkspace";

export const metadata = {
    title: "Time Tracking",
};

export default function TimeTrackingPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Time tracking"
                description="Record time quickly, then review delivery by Client, Project or ADB internal work for the period that matters."
            />
            <div className="mt-6">
                <Suspense fallback={<DataLoading label="Loading time tracking..." />}>
                    <TimeTrackingWorkspace />
                </Suspense>
            </div>
        </Container>
    );
}

import { Container, PageHeader } from "@/components/ui";
import { TimeTrackingWorkspace } from "./TimeTrackingWorkspace";

export const metadata = {
    title: "Time Tracking",
};

export default function TimeTrackingPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Time tracking"
                description="Record client and internal work manually or with a persistent timer, including Project, Task and Ticket context."
            />
            <div className="mt-6">
                <TimeTrackingWorkspace />
            </div>
        </Container>
    );
}

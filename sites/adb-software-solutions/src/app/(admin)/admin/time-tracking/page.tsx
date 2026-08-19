import { Container, DataLoading, PageHeader } from "@/components/ui";
import { Suspense } from "react";
import { TimeReportOverview } from "./TimeReportOverview";
import { TimeTrackingWorkspace } from "./TimeTrackingWorkspace";

export const metadata = {
    title: "Time Tracking",
};

export default function TimeTrackingPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Time tracking"
                description="Understand where time goes across the business, then record client or internal work manually or with a persistent timer."
            />
            <div className="mt-6 space-y-10">
                <TimeReportOverview />
                <div className="border-t border-slate-800 pt-8">
                    <Suspense fallback={<DataLoading label="Loading time tracking..." />}>
                        <TimeTrackingWorkspace />
                    </Suspense>
                </div>
            </div>
        </Container>
    );
}

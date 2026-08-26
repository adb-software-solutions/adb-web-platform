import { Container, PageHeader } from "@/components/ui";
import { MonitoringAddAction } from "./MonitoringAddAction";
import { MonitoringWorkspace } from "./MonitoringWorkspace";

export const metadata = {
    title: "Monitoring",
};

export default function MonitoringPage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Monitoring"
                description="Current technical health and active incidents across managed infrastructure."
                actions={<MonitoringAddAction />}
            />
            <div className="mt-6">
                <MonitoringWorkspace />
            </div>
        </Container>
    );
}

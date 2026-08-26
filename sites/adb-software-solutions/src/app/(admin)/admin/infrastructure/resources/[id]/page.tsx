import { MonitoringHealthPanel } from "@/components/admin/MonitoringHealthPanel";
import { Container } from "@/components/ui";
import { InfrastructureResourceWorkspace } from "./InfrastructureResourceWorkspace";

export default async function InfrastructureResourcePage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const resourceId = Number(id);

    return (
        <Container className="py-8">
            <div className="space-y-6">
                <InfrastructureResourceWorkspace resourceId={resourceId} />
                <MonitoringHealthPanel
                    resourceId={resourceId}
                    title="Resource technical health"
                    description="Current monitoring state for this infrastructure resource."
                />
            </div>
        </Container>
    );
}

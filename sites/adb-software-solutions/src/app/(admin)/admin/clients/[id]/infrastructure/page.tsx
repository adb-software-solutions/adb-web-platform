import { MonitoringHealthPanel } from "@/components/admin/MonitoringHealthPanel";
import { Container } from "@/components/ui";
import { ClientInfrastructureWorkspace } from "./ClientInfrastructureWorkspace";

export default async function ClientInfrastructurePage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const clientId = Number(id);

    return (
        <Container className="py-8">
            <div className="space-y-6">
                <ClientInfrastructureWorkspace clientId={clientId} />
                <MonitoringHealthPanel
                    clientId={clientId}
                    title="Client technical health"
                    description="Current monitoring state for infrastructure owned by this client."
                />
            </div>
        </Container>
    );
}

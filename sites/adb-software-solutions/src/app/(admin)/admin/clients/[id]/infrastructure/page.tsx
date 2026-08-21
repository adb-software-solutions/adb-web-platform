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
            <ClientInfrastructureWorkspace clientId={clientId} />
        </Container>
    );
}

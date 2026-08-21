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
            <InfrastructureResourceWorkspace resourceId={resourceId} />
        </Container>
    );
}

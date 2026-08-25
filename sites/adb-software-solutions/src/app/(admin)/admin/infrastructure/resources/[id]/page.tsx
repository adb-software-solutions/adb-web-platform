import { CredentialVault } from "@/app/(admin)/admin/credentials/CredentialVault";
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
            <div className="mt-8 border-t border-slate-800 pt-8">
                <CredentialVault initialResourceId={resourceId} compact />
            </div>
        </Container>
    );
}

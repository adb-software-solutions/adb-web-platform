import { Container } from "@/components/ui";
import { CredentialWorkspace } from "../CredentialWorkspace";

export default async function CredentialPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    return (
        <Container className="py-8">
            <CredentialWorkspace credentialId={Number(id)} />
        </Container>
    );
}

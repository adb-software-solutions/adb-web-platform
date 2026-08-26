import { Container, PageHeader } from "@/components/ui";
import { KnowledgeDocumentForm } from "../../KnowledgeDocumentForm";

export default async function NewKnowledgeDocumentPage({
    searchParams,
}: {
    searchParams: Promise<{ client_id?: string }>;
}) {
    const { client_id: clientIdParam } = await searchParams;
    const initialClientId = clientIdParam ? Number(clientIdParam) : undefined;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Knowledge Base"
                title="New document"
                description="Create scoped operational documentation with immutable Markdown revision history."
            />
            <div className="mt-6">
                <KnowledgeDocumentForm initialClientId={initialClientId} />
            </div>
        </Container>
    );
}

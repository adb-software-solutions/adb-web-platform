import { Container, PageHeader } from "@/components/ui";
import { KnowledgeDocumentForm } from "../../../KnowledgeDocumentForm";

export default async function EditKnowledgeDocumentPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Knowledge Base"
                title="Edit document"
                description="Save a controlled revision while preserving immutable document history."
            />
            <div className="mt-6">
                <KnowledgeDocumentForm documentId={Number(id)} />
            </div>
        </Container>
    );
}

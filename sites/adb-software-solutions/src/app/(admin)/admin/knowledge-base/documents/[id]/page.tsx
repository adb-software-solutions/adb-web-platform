import { ButtonLink, Container, PageHeader } from "@/components/ui";
import { KnowledgeDocumentWorkspace } from "../../KnowledgeDocumentWorkspace";

export default async function KnowledgeDocumentPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Knowledge Base"
                title="Document"
                description="Read operational documentation, inspect immutable revisions and follow scoped platform links."
                actions={
                    <ButtonLink href="/admin/knowledge-base" variant="secondary">
                        Back to Knowledge Base
                    </ButtonLink>
                }
            />
            <div className="mt-6">
                <KnowledgeDocumentWorkspace documentId={Number(id)} />
            </div>
        </Container>
    );
}

import { Container, PageHeader } from "@/components/ui";
import { KnowledgeBaseWorkspace } from "./KnowledgeBaseWorkspace";

export default function KnowledgeBasePage() {
    return (
        <Container className="py-8">
            <PageHeader
                title="Knowledge Base"
                description="Search and maintain scoped internal and client runbooks, documentation and operational knowledge."
            />
            <div className="mt-6">
                <KnowledgeBaseWorkspace />
            </div>
        </Container>
    );
}

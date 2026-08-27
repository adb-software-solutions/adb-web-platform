import { Container, PageHeader } from "@/components/ui";
import { SpecialistOperationsWorkspace } from "./SpecialistOperationsWorkspace";

export default function SpecialistOperationsPage() {
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Infrastructure"
                title="Specialist operations"
                description="Manage storage, backups, container stacks, Kubernetes, system services and scheduled jobs as structured operational records."
            />
            <div className="mt-6">
                <SpecialistOperationsWorkspace />
            </div>
        </Container>
    );
}

import { Container, PageHeader } from "@/components/ui";
import { StaffAccessWorkspace } from "./StaffAccessWorkspace";

export default function StaffAccessPage() {
    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Administration"
                title="Users & Access"
                description="Manage staff capability bundles, direct permissions and Client/Ticket Queue scope without relying on Django superuser access."
            />
            <div className="mt-6">
                <StaffAccessWorkspace />
            </div>
        </Container>
    );
}

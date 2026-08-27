import { Container, PageHeader } from "@/components/ui";
import { DashboardWorkspace } from "./DashboardWorkspace";

export default function AdminDashboard() {
    return (
        <Container className="py-6 lg:py-8">
            <PageHeader
                eyebrow="Operations"
                title="My Work"
                description="A permission-aware personal starting point for the work and operational health that need your attention."
            />
            <div className="mt-6">
                <DashboardWorkspace />
            </div>
        </Container>
    );
}

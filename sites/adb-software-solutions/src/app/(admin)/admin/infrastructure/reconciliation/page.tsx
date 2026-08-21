import { Container } from "@/components/ui";
import { InfrastructureReconciliationWorkspace } from "./InfrastructureReconciliationWorkspace";

export const metadata = {
    title: "Infrastructure Reconciliation",
};

export default function InfrastructureReconciliationPage() {
    return (
        <Container className="py-8">
            <InfrastructureReconciliationWorkspace />
        </Container>
    );
}

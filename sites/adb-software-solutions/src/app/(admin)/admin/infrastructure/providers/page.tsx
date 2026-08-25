import { PageHeader } from "@/components/ui";
import { ProviderWorkspace } from "./ProviderWorkspace";

export default function ProvidersPage() {
    return (
        <div className="space-y-6">
            <PageHeader
                eyebrow="Infrastructure"
                title="Providers"
                description="Service catalogue and scoped provider accounts connected to infrastructure, credentials and operational context."
            />
            <ProviderWorkspace />
        </div>
    );
}

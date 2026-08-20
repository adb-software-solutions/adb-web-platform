import { LeadEmailPanel } from "@/app/(admin)/admin/leads/LeadEmailPanel";
import { Container } from "@/components/ui";
import { LeadWorkspace } from "./LeadWorkspace";

export default async function LeadPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const leadId = Number(id);
    return (
        <Container className="py-8">
            <div className="space-y-6">
                <LeadWorkspace leadId={leadId} />
                <LeadEmailPanel leadId={leadId} />
            </div>
        </Container>
    );
}

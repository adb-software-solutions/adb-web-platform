import { Container, PageHeader } from "@/components/ui";
import { MonitoringCheckForm } from "../../MonitoringCheckForm";

export default async function EditMonitoringCheckPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const checkId = Number(id);

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Monitoring"
                title="Edit monitoring check"
                description="Update probe configuration while retaining historical observations and incidents."
            />
            <div className="mt-6">
                <MonitoringCheckForm checkId={checkId} />
            </div>
        </Container>
    );
}

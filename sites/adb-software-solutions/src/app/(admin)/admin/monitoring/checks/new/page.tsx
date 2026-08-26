import { Container, PageHeader } from "@/components/ui";
import { MonitoringCheckForm } from "../MonitoringCheckForm";

export default async function NewMonitoringCheckPage({
    searchParams,
}: {
    searchParams: Promise<{ resource_id?: string }>;
}) {
    const { resource_id: resourceIdParam } = await searchParams;
    const initialResourceId = resourceIdParam ? Number(resourceIdParam) : undefined;

    return (
        <Container className="py-8">
            <PageHeader
                eyebrow="Monitoring"
                title="Add monitoring check"
                description="Attach a scheduled technical-health check to a structured infrastructure resource."
            />
            <div className="mt-6">
                <MonitoringCheckForm initialResourceId={initialResourceId} />
            </div>
        </Container>
    );
}

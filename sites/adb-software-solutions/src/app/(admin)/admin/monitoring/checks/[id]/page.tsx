import { Container } from "@/components/ui";
import { MonitoringCheckWorkspace } from "./MonitoringCheckWorkspace";

export default async function MonitoringCheckPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const checkId = Number(id);

    return (
        <Container className="py-8">
            <MonitoringCheckWorkspace checkId={checkId} />
        </Container>
    );
}

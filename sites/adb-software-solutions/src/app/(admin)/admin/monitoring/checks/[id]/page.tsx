import { Container } from "@/components/ui";
import { MonitoringCheckEditAction } from "./MonitoringCheckEditAction";
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
            <div className="mt-6 flex justify-end">
                <MonitoringCheckEditAction checkId={checkId} />
            </div>
        </Container>
    );
}

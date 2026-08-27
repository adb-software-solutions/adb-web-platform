import { Container } from "@/components/ui";
import { ClientCommandCentre } from "./ClientCommandCentre";

const SECTIONS = new Set([
    "overview",
    "contacts",
    "projects",
    "tasks",
    "tickets",
    "time",
    "infrastructure",
    "credentials",
    "knowledge",
    "activity",
]);
const PERIODS = new Set([7, 30, 90, 365]);

type CommandCentreProps = Parameters<typeof ClientCommandCentre>[0];

export default async function ClientPage({
    params,
    searchParams,
}: {
    params: Promise<{ id: string }>;
    searchParams: Promise<{ section?: string; period_days?: string }>;
}) {
    const [{ id }, query] = await Promise.all([params, searchParams]);
    const clientId = Number(id);
    const initialSection = SECTIONS.has(query.section ?? "")
        ? (query.section as CommandCentreProps["initialSection"])
        : "overview";
    const requestedPeriod = Number(query.period_days ?? "30");
    const initialPeriodDays = PERIODS.has(requestedPeriod) ? requestedPeriod : 30;

    return (
        <Container className="py-8">
            <ClientCommandCentre
                clientId={clientId}
                initialSection={initialSection}
                initialPeriodDays={initialPeriodDays}
            />
        </Container>
    );
}

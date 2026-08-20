import { Container } from "@/components/ui";
import { TicketControls } from "./TicketControls";
import { TicketTimePanel } from "./TicketTimePanel";
import { TicketWorkspace } from "./TicketWorkspace";

export default async function TicketPage({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const ticketId = Number(id);

    return (
        <Container className="py-8">
            <div className="space-y-6">
                <TicketControls ticketId={ticketId} />
                <TicketTimePanel ticketId={ticketId} />
                <TicketWorkspace ticketId={ticketId} />
            </div>
        </Container>
    );
}

"use client";

import { RelatedTimePanel } from "@/components/admin/RelatedTimePanel";
import { useState } from "react";
import { TicketTimerControl } from "./TicketTimerControl";

export function TicketTimePanel({ ticketId }: { ticketId: number }) {
    const [version, setVersion] = useState(0);

    return (
        <div className="space-y-6">
            <TicketTimerControl
                ticketId={ticketId}
                onTimeChanged={() => setVersion((value) => value + 1)}
            />
            <RelatedTimePanel key={version} contextType="ticket" contextId={ticketId} />
        </div>
    );
}

"use client";

import { ButtonLink } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";

export function MonitoringCheckEditAction({ checkId }: { checkId: number }) {
    const { hasPermission } = useAuth();
    if (!hasPermission("monitoring.change_monitorcheck")) return null;

    return (
        <ButtonLink href={`/admin/monitoring/checks/${checkId}/edit`} variant="outline">
            Edit configuration
        </ButtonLink>
    );
}

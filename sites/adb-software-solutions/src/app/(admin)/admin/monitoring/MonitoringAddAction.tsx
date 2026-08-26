"use client";

import { ButtonLink } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";

export function MonitoringAddAction() {
    const { hasPermission } = useAuth();
    if (!hasPermission("monitoring.add_monitorcheck")) return null;

    return <ButtonLink href="/admin/monitoring/checks/new">Add check</ButtonLink>;
}

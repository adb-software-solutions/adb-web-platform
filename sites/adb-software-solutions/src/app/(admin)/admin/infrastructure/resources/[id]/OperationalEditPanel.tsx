"use client";

import { Button, Card } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import { useEffect, useState } from "react";
import {
    OperationalInfrastructureForm,
    type OperationalType,
} from "../OperationalInfrastructureForm";

interface ResourceMeta {
    resource_type: string;
}

const CHANGE_PERMISSIONS: Record<OperationalType, string> = {
    storage: "infrastructure.change_storageprofile",
    backup_plan: "infrastructure.change_backupplanprofile",
    container_stack: "infrastructure.change_containerstackprofile",
    kubernetes_cluster: "infrastructure.change_kubernetesclusterprofile",
    kubernetes_namespace: "infrastructure.change_kubernetesnamespaceprofile",
    kubernetes_workload: "infrastructure.change_kubernetesworkloadprofile",
    system_service: "infrastructure.change_systemserviceprofile",
    scheduled_job: "infrastructure.change_scheduledjobprofile",
};

function operationalType(value: string): OperationalType | null {
    if (value in CHANGE_PERMISSIONS) return value as OperationalType;
    return null;
}

export function OperationalEditPanel({ resourceId }: { resourceId: number }) {
    const { hasPermission } = useAuth();
    const [type, setType] = useState<OperationalType | null>(null);
    const [isEditing, setIsEditing] = useState(false);

    useEffect(() => {
        let cancelled = false;
        if (!hasPermission("infrastructure.view_infrastructureresource")) return;

        void fetchAPI(`${API_URL}/api/admin/infrastructure/resources/${resourceId}`)
            .then((value) => {
                if (cancelled) return;
                setType(operationalType((value as ResourceMeta).resource_type));
                setIsEditing(false);
            })
            .catch(() => {
                if (!cancelled) setType(null);
            });

        return () => {
            cancelled = true;
        };
    }, [hasPermission, resourceId]);

    if (
        type === null ||
        !hasPermission("infrastructure.change_infrastructureresource") ||
        !hasPermission(CHANGE_PERMISSIONS[type])
    ) {
        return null;
    }

    if (isEditing) {
        return (
            <OperationalInfrastructureForm
                allowedTypes={[type]}
                editResourceId={resourceId}
                onCancel={() => setIsEditing(false)}
                onSaved={() => setIsEditing(false)}
            />
        );
    }

    return (
        <Card className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div>
                <h2 className="text-sm font-semibold text-white">
                    Operational record
                </h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                    Edit the native specialist metadata attached to this resource.
                </p>
            </div>
            <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setIsEditing(true)}
            >
                Edit operational resource
            </Button>
        </Card>
    );
}

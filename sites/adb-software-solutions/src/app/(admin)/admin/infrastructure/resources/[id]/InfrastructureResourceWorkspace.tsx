"use client";

import {
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    Input,
    PageHeader,
    Select,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { CredentialVault } from "../../../credentials/CredentialVault";

interface SpecialistField {
    key: string;
    label: string;
    value: string;
    kind: "text" | "code" | "url" | "multiline";
}

interface LegacyReference {
    legacy_type: string;
    legacy_id: number;
    name: string;
    register_path: string;
    fields: SpecialistField[];
}

interface Relationship {
    id: number;
    direction: "outgoing" | "incoming";
    relationship_type: string;
    label: string;
    related_resource_id: number;
    related_resource_name: string;
    related_resource_type: string;
}

interface RelationshipTypeOption {
    value: string;
    label: string;
}

interface RelationshipTargetOption {
    id: number;
    name: string;
    resource_type: string;
    ownership_type: string;
    client_name: string | null;
}

interface RelationshipOptions {
    relationship_types: RelationshipTypeOption[];
    targets: RelationshipTargetOption[];
}

interface ResourceDetail {
    id: number;
    name: string;
    resource_type: string;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
    description: string;
    is_portal_visible: boolean;
    tags: { id: number; name: string; slug: string; colour: string }[];
    relationships: Relationship[];
    specialist_fields: SpecialistField[];
    legacy_reference: LegacyReference | null;
    created_at: string;
    updated_at: string;
}

interface InfrastructureResourceWorkspaceProps {
    resourceId: number;
    presentation?: "page" | "drawer";
}

function label(value: string): string {
    const special: Record<string, string> = {
        not_applicable: "Not applicable",
        database_instance: "Database instance",
        logical_database: "Logical database",
        application_environment: "Application environment",
        source_repository: "Source repository",
        website_endpoint: "Website endpoint",
        dns_zone: "DNS zone",
        tls_certificate: "TLS certificate",
        provider_account: "Provider account",
        backup_plan: "Backup plan",
        container_stack: "Container stack",
        kubernetes_cluster: "Kubernetes cluster",
        kubernetes_namespace: "Kubernetes namespace",
        kubernetes_workload: "Kubernetes workload",
        system_service: "System service",
        scheduled_job: "Scheduled job",
        mobile_app: "Mobile app",
        email_system: "Email system",
        network_device: "Network device",
        hosted_on: "Hosted on",
        depends_on: "Depends on",
        connects_to: "Connects to",
        managed_by: "Managed by",
        backed_up_to: "Backed up to",
        protected_by: "Protected by",
        routes_to: "Routes to",
        related_to: "Related to",
    };
    return special[value] ?? `${value.charAt(0).toUpperCase()}${value.slice(1).replaceAll("_", " ")}`;
}

function dateTime(value: string): string {
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function SpecialistValue({ field }: { field: SpecialistField }) {
    if (field.kind === "url") {
        return (
            <a
                href={field.value}
                target="_blank"
                rel="noreferrer"
                className="break-all text-adb-cyan-300 hover:text-adb-cyan-200 hover:underline"
            >
                {field.value}
            </a>
        );
    }
    if (field.kind === "code") {
        return (
            <code className="break-all rounded bg-slate-950 px-1.5 py-1 text-xs text-slate-200">
                {field.value}
            </code>
        );
    }
    if (field.kind === "multiline") {
        return <span className="whitespace-pre-wrap text-slate-300">{field.value}</span>;
    }
    return <span className="text-slate-300">{field.value}</span>;
}

export function InfrastructureResourceWorkspace({
    resourceId,
    presentation = "page",
}: InfrastructureResourceWorkspaceProps) {
    const { hasPermission } = useAuth();
    const canCreateRelationships = hasPermission(
        "infrastructure.add_resourcerelationship",
    );
    const canDeleteRelationships = hasPermission(
        "infrastructure.delete_resourcerelationship",
    );

    const [resource, setResource] = useState<ResourceDetail | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showRelationshipForm, setShowRelationshipForm] = useState(false);
    const [relationshipOptions, setRelationshipOptions] =
        useState<RelationshipOptions | null>(null);
    const [relationshipType, setRelationshipType] = useState("");
    const [relationshipTargetId, setRelationshipTargetId] = useState("");
    const [relationshipLabel, setRelationshipLabel] = useState("");
    const [relationshipError, setRelationshipError] = useState<string | null>(null);
    const [isSavingRelationship, setIsSavingRelationship] = useState(false);
    const [deletingRelationshipId, setDeletingRelationshipId] = useState<number | null>(
        null,
    );

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            setResource(
                (await fetchAPI(
                    `${API_URL}/api/admin/infrastructure/resources/${resourceId}`,
                )) as ResourceDetail,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load this infrastructure resource.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [resourceId]);

    useEffect(() => {
        void load();
    }, [load]);

    useEffect(() => {
        setShowRelationshipForm(false);
        setRelationshipOptions(null);
        setRelationshipType("");
        setRelationshipTargetId("");
        setRelationshipLabel("");
        setRelationshipError(null);
    }, [resourceId]);

    async function openRelationshipForm() {
        setShowRelationshipForm(true);
        setRelationshipError(null);
        if (relationshipOptions) return;

        try {
            const options = (await fetchAPI(
                `${API_URL}/api/admin/infrastructure/resources/${resourceId}/relationship-options`,
            )) as RelationshipOptions;
            setRelationshipOptions(options);
            setRelationshipType(options.relationship_types[0]?.value ?? "");
        } catch (loadError) {
            setRelationshipError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load relationship options.",
            );
        }
    }

    function closeRelationshipForm() {
        if (isSavingRelationship) return;
        setShowRelationshipForm(false);
        setRelationshipTargetId("");
        setRelationshipLabel("");
        setRelationshipError(null);
    }

    async function createRelationship() {
        if (!relationshipType || !relationshipTargetId) {
            setRelationshipError("Choose a relationship type and target resource.");
            return;
        }

        try {
            setIsSavingRelationship(true);
            setRelationshipError(null);
            await fetchAPI(
                `${API_URL}/api/admin/infrastructure/resources/${resourceId}/relationships`,
                {
                    method: "POST",
                    body: JSON.stringify({
                        target_resource_id: Number(relationshipTargetId),
                        relationship_type: relationshipType,
                        label: relationshipLabel.trim(),
                    }),
                },
            );
            setShowRelationshipForm(false);
            setRelationshipTargetId("");
            setRelationshipLabel("");
            await load();
        } catch (saveError) {
            setRelationshipError(
                saveError instanceof Error
                    ? saveError.message
                    : "Unable to create this relationship.",
            );
        } finally {
            setIsSavingRelationship(false);
        }
    }

    async function deleteRelationship(relationship: Relationship) {
        const confirmed = window.confirm(
            `Remove the relationship with ${relationship.related_resource_name}?`,
        );
        if (!confirmed) return;

        try {
            setDeletingRelationshipId(relationship.id);
            setRelationshipError(null);
            await fetchAPI(
                `${API_URL}/api/admin/infrastructure/resources/${resourceId}/relationships/${relationship.id}`,
                { method: "DELETE" },
            );
            await load();
        } catch (deleteError) {
            setRelationshipError(
                deleteError instanceof Error
                    ? deleteError.message
                    : "Unable to remove this relationship.",
            );
        } finally {
            setDeletingRelationshipId(null);
        }
    }

    if (isLoading && !resource) {
        return <DataLoading label="Loading infrastructure resource..." />;
    }
    if (error || !resource) {
        return (
            <DataError
                message={error || "Infrastructure resource is unavailable."}
                onRetry={() => void load()}
            />
        );
    }

    const technicalFields =
        resource.specialist_fields.length > 0
            ? resource.specialist_fields
            : (resource.legacy_reference?.fields ?? []);
    const showingNativeFields = resource.specialist_fields.length > 0;

    return (
        <div className="space-y-6">
            <PageHeader
                eyebrow={label(resource.resource_type)}
                title={resource.name}
                description={
                    resource.description ||
                    `${resource.client_name || "ADB Internal"} · ${label(resource.environment)} · ${label(resource.lifecycle_status)}`
                }
                actions={
                    presentation === "page" ? (
                        <ButtonLink href="/admin/infrastructure/resources" variant="secondary">
                            Back to resources
                        </ButtonLink>
                    ) : undefined
                }
            />

            <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300">
                    {resource.client_name || "ADB Internal"}
                </span>
                <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300">
                    {label(resource.environment)}
                </span>
                <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300">
                    {label(resource.lifecycle_status)}
                </span>
                <span
                    className={
                        resource.criticality === "critical"
                            ? "rounded-full border border-red-900 bg-red-950/40 px-3 py-1 text-xs text-red-300"
                            : resource.criticality === "high"
                              ? "rounded-full border border-amber-900 bg-amber-950/40 px-3 py-1 text-xs text-amber-300"
                              : "rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-300"
                    }
                >
                    {label(resource.criticality)} criticality
                </span>
                {resource.tags.map((tag) => (
                    <span
                        key={tag.id}
                        className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-400"
                    >
                        {tag.name}
                    </span>
                ))}
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(19rem,1fr)]">
                <div className="space-y-6">
                    <Card className="p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <h2 className="text-sm font-semibold text-white">Technical details</h2>
                                <p className="mt-1 text-xs leading-5 text-slate-500">
                                    {showingNativeFields
                                        ? "Native typed operational metadata attached to this resource identity."
                                        : "Operational metadata from the legacy specialist record while this resource family is migrated."}
                                </p>
                            </div>
                            {resource.legacy_reference ? (
                                <ButtonLink
                                    href={resource.legacy_reference.register_path}
                                    variant="ghost"
                                    size="sm"
                                >
                                    Open legacy register
                                </ButtonLink>
                            ) : null}
                        </div>

                        {technicalFields.length ? (
                            <dl className="mt-5 grid gap-x-6 gap-y-5 sm:grid-cols-2">
                                {technicalFields.map((field) => (
                                    <div
                                        key={field.key}
                                        className={
                                            field.kind === "multiline" ? "sm:col-span-2" : ""
                                        }
                                    >
                                        <dt className="text-[11px] font-semibold tracking-wide text-slate-600 uppercase">
                                            {field.label}
                                        </dt>
                                        <dd className="mt-1 text-sm leading-6">
                                            <SpecialistValue field={field} />
                                        </dd>
                                    </div>
                                ))}
                            </dl>
                        ) : (
                            <div className="mt-5 rounded-xl border border-dashed border-slate-800 p-5 text-sm text-slate-500">
                                No typed technical details have been recorded for this resource yet.
                            </div>
                        )}
                        {showingNativeFields && resource.legacy_reference ? (
                            <p className="mt-5 border-t border-slate-800 pt-4 text-xs leading-5 text-slate-600">
                                Native structured data is authoritative here. The legacy source remains intact and available during reconciliation.
                            </p>
                        ) : null}
                    </Card>

                    <Card className="p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <h2 className="text-sm font-semibold text-white">Relationships</h2>
                                <p className="mt-1 text-xs leading-5 text-slate-500">
                                    What this resource depends on and what depends on it across the visible infrastructure graph.
                                </p>
                            </div>
                            {canCreateRelationships ? (
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    onClick={() => void openRelationshipForm()}
                                >
                                    Add relationship
                                </Button>
                            ) : null}
                        </div>

                        {showRelationshipForm ? (
                            <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                                <div className="grid gap-3 md:grid-cols-2">
                                    <div>
                                        <label className="mb-2 block text-xs font-medium text-slate-400">
                                            Relationship
                                        </label>
                                        <Select
                                            value={relationshipType}
                                            onChange={(event) =>
                                                setRelationshipType(event.target.value)
                                            }
                                            disabled={!relationshipOptions || isSavingRelationship}
                                        >
                                            {relationshipOptions?.relationship_types.map(
                                                (option) => (
                                                    <option key={option.value} value={option.value}>
                                                        {option.label}
                                                    </option>
                                                ),
                                            )}
                                        </Select>
                                    </div>
                                    <div>
                                        <label className="mb-2 block text-xs font-medium text-slate-400">
                                            Target resource
                                        </label>
                                        <Select
                                            value={relationshipTargetId}
                                            onChange={(event) =>
                                                setRelationshipTargetId(event.target.value)
                                            }
                                            disabled={!relationshipOptions || isSavingRelationship}
                                        >
                                            <option value="">Choose resource</option>
                                            {relationshipOptions?.targets.map((target) => (
                                                <option key={target.id} value={target.id}>
                                                    {target.name} · {label(target.resource_type)} · {" "}
                                                    {target.client_name || "ADB Internal"}
                                                </option>
                                            ))}
                                        </Select>
                                    </div>
                                    <div className="md:col-span-2">
                                        <label className="mb-2 block text-xs font-medium text-slate-400">
                                            Label <span className="text-slate-600">(optional)</span>
                                        </label>
                                        <Input
                                            value={relationshipLabel}
                                            onChange={(event) =>
                                                setRelationshipLabel(event.target.value)
                                            }
                                            placeholder="e.g. Production database, primary host..."
                                            disabled={isSavingRelationship}
                                        />
                                    </div>
                                </div>

                                {relationshipOptions?.targets.length === 0 ? (
                                    <p className="mt-3 text-xs text-slate-500">
                                        There are no current resources in your access scope that can be related to this resource.
                                    </p>
                                ) : null}
                                {relationshipError ? (
                                    <p className="mt-3 text-sm text-red-300">
                                        {relationshipError}
                                    </p>
                                ) : null}

                                <div className="mt-4 flex justify-end gap-2">
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={closeRelationshipForm}
                                        disabled={isSavingRelationship}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        type="button"
                                        size="sm"
                                        onClick={() => void createRelationship()}
                                        disabled={
                                            isSavingRelationship ||
                                            !relationshipTargetId ||
                                            !relationshipType
                                        }
                                    >
                                        {isSavingRelationship ? "Adding..." : "Add relationship"}
                                    </Button>
                                </div>
                            </div>
                        ) : relationshipError ? (
                            <p className="mt-4 text-sm text-red-300">{relationshipError}</p>
                        ) : null}

                        {resource.relationships.length === 0 ? (
                            <p className="mt-5 text-sm text-slate-500">
                                No visible resource relationships yet.
                            </p>
                        ) : (
                            <div className="mt-4 divide-y divide-slate-800">
                                {resource.relationships.map((relationship) => (
                                    <div
                                        key={relationship.id}
                                        className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-2"
                                    >
                                        <Link
                                            href={`/admin/infrastructure/resources/${relationship.related_resource_id}`}
                                            className="min-w-0 flex-1 transition hover:text-adb-cyan-300"
                                        >
                                            <div className="text-sm font-medium text-slate-200">
                                                {relationship.related_resource_name}
                                            </div>
                                            <div className="mt-0.5 text-xs text-slate-500">
                                                {label(relationship.related_resource_type)}
                                            </div>
                                        </Link>
                                        <div className="flex shrink-0 items-center gap-2">
                                            <div className="text-xs text-slate-500">
                                                {relationship.direction === "outgoing" ? "→" : "←"}{" "}
                                                {relationship.label ||
                                                    label(relationship.relationship_type)}
                                            </div>
                                            {canDeleteRelationships ? (
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() =>
                                                        void deleteRelationship(relationship)
                                                    }
                                                    disabled={
                                                        deletingRelationshipId === relationship.id
                                                    }
                                                >
                                                    {deletingRelationshipId === relationship.id
                                                        ? "Removing..."
                                                        : "Remove"}
                                                </Button>
                                            ) : null}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>

                    <CredentialVault initialResourceId={resourceId} compact />
                </div>

                <div className="space-y-6">
                    <Card className="p-5">
                        <h2 className="text-sm font-semibold text-white">Resource context</h2>
                        <dl className="mt-4 space-y-4 text-sm">
                            <div>
                                <dt className="text-xs text-slate-600">Ownership</dt>
                                <dd className="mt-1 text-slate-300">
                                    {resource.client_name || "ADB Internal"}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-600">Resource type</dt>
                                <dd className="mt-1 text-slate-300">
                                    {label(resource.resource_type)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-600">Created</dt>
                                <dd className="mt-1 text-slate-300">
                                    {dateTime(resource.created_at)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-600">Last updated</dt>
                                <dd className="mt-1 text-slate-300">
                                    {dateTime(resource.updated_at)}
                                </dd>
                            </div>
                            <div>
                                <dt className="text-xs text-slate-600">Client portal</dt>
                                <dd className="mt-1 text-slate-300">
                                    {resource.is_portal_visible ? "Marked visible" : "Private"}
                                </dd>
                            </div>
                        </dl>
                    </Card>

                    {resource.legacy_reference ? (
                        <Card className="border-amber-950/70 bg-amber-950/10 p-5">
                            <h2 className="text-sm font-semibold text-amber-200">
                                Legacy source
                            </h2>
                            <p className="mt-2 text-xs leading-5 text-amber-200/60">
                                This resource is currently backed by the existing {" "}
                                {label(resource.legacy_reference.legacy_type)} record #{" "}
                                {resource.legacy_reference.legacy_id}. The structured identity is now the ownership and relationship anchor; the old row remains intact during migration.
                            </p>
                        </Card>
                    ) : null}

                    <Card className="p-5">
                        <h2 className="text-sm font-semibold text-white">Workspace roadmap</h2>
                        <div className="mt-4 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3 xl:grid-cols-1">
                            {["Monitoring", "Documentation", "Activity"].map((item) => (
                                <div
                                    key={item}
                                    className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-3 text-slate-500"
                                >
                                    {item}
                                </div>
                            ))}
                        </div>
                        <p className="mt-3 text-xs leading-5 text-slate-600">
                            Credentials are live in this workspace. Monitoring, documentation and activity will attach to the same resource identity in their planned technical slices.
                        </p>
                    </Card>
                </div>
            </div>
        </div>
    );
}

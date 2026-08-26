"use client";

import { ButtonLink, Card, DataError, DataLoading } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

interface KnowledgeDocumentSummary {
    id: number;
    title: string;
    summary: string;
    section_path: string;
    client_name: string | null;
    updated_at: string;
}

interface KnowledgeWorkspaceResponse {
    documents: KnowledgeDocumentSummary[];
    total_documents: number;
}

export function KnowledgeBasePanel({
    clientId,
    resourceId,
    title = "Knowledge Base",
    description = "Relevant operational documentation for this context.",
}: {
    clientId?: number;
    resourceId?: number;
    title?: string;
    description?: string;
}) {
    const { hasPermission } = useAuth();
    const canView = hasPermission("knowledge_base.view_knowledgebasedocument");
    const canAdd = hasPermission("knowledge_base.add_knowledgebasedocument");
    const [data, setData] = useState<KnowledgeWorkspaceResponse | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        if (!canView) {
            setIsLoading(false);
            return;
        }
        try {
            setIsLoading(true);
            setError(null);
            const params = new URLSearchParams({ view: "current", page_size: "5" });
            if (clientId) params.set("client_id", String(clientId));
            if (resourceId) params.set("resource_id", String(resourceId));
            setData(
                (await fetchAPI(
                    `${API_URL}/api/admin/knowledge-base/workspace?${params.toString()}`,
                )) as KnowledgeWorkspaceResponse,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load contextual Knowledge Base documents.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [canView, clientId, resourceId]);

    useEffect(() => {
        void load();
    }, [load]);

    if (!canView) return null;

    return (
        <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h2 className="font-semibold text-slate-100">{title}</h2>
                    <p className="mt-1 text-sm text-slate-500">{description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                    {clientId && canAdd ? (
                        <ButtonLink
                            size="sm"
                            href={`/admin/knowledge-base/documents/new?client_id=${clientId}`}
                        >
                            Add document
                        </ButtonLink>
                    ) : null}
                    <ButtonLink size="sm" variant="secondary" href="/admin/knowledge-base">
                        Open Knowledge Base
                    </ButtonLink>
                </div>
            </div>

            <div className="mt-4">
                {isLoading ? <DataLoading label="Loading documentation…" /> : null}
                {error ? <DataError message={error} onRetry={() => void load()} /> : null}
                {!isLoading && !error && data?.documents.length === 0 ? (
                    <p className="rounded-lg border border-dashed border-slate-800 p-5 text-sm text-slate-500">
                        No current documentation is linked to this context yet.
                    </p>
                ) : null}
                {!isLoading && !error && data?.documents.length ? (
                    <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                        {data.documents.map((document) => (
                            <Link
                                key={document.id}
                                href={`/admin/knowledge-base/documents/${document.id}`}
                                className="rounded-lg border border-slate-800 p-3 transition hover:border-slate-700 hover:bg-slate-900"
                            >
                                <p className="text-sm font-medium text-slate-200">{document.title}</p>
                                <p className="mt-1 text-xs text-adb-cyan-300">{document.section_path}</p>
                                {document.summary ? (
                                    <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                                        {document.summary}
                                    </p>
                                ) : null}
                            </Link>
                        ))}
                    </div>
                ) : null}
                {data && data.total_documents > data.documents.length ? (
                    <p className="mt-3 text-xs text-slate-600">
                        Showing {data.documents.length} of {data.total_documents} matching documents.
                    </p>
                ) : null}
            </div>
        </Card>
    );
}

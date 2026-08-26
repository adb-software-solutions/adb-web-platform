"use client";

import {
    Badge,
    Button,
    ButtonLink,
    Card,
    DataError,
    DataLoading,
    Input,
    Select,
} from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { fetchAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import type {
    KnowledgeOptionsResponse,
    KnowledgeSection,
    KnowledgeWorkspaceResponse,
} from "./types";

const BASE = `${API_URL}/api/admin/knowledge-base`;

function formatDate(value: string): string {
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

function sectionDepth(section: KnowledgeSection): number {
    return Math.max(section.path.split(" / ").length - 1, 0);
}

export function KnowledgeBaseWorkspace() {
    const { hasPermission } = useAuth();
    const canAddDocument = hasPermission("knowledge_base.add_knowledgebasedocument");
    const canAddSection = hasPermission("knowledge_base.add_knowledgebasesection");
    const [options, setOptions] = useState<KnowledgeOptionsResponse | null>(null);
    const [workspace, setWorkspace] = useState<KnowledgeWorkspaceResponse | null>(null);
    const [query, setQuery] = useState("");
    const [ownership, setOwnership] = useState("all");
    const [clientId, setClientId] = useState("");
    const [sectionId, setSectionId] = useState("");
    const [view, setView] = useState("current");
    const [page, setPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showFolderForm, setShowFolderForm] = useState(false);
    const [folderName, setFolderName] = useState("");
    const [folderParentId, setFolderParentId] = useState("");
    const [isSavingFolder, setIsSavingFolder] = useState(false);

    useEffect(() => {
        void (async () => {
            try {
                setOptions((await fetchAPI(`${BASE}/options`)) as KnowledgeOptionsResponse);
            } catch (loadError) {
                setError(
                    loadError instanceof Error
                        ? loadError.message
                        : "Unable to load Knowledge Base options.",
                );
            }
        })();
    }, []);

    const loadWorkspace = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const params = new URLSearchParams({
                view,
                page: String(page),
                page_size: "30",
            });
            if (query.trim()) params.set("q", query.trim());
            if (ownership !== "all") params.set("ownership_type", ownership);
            if (clientId) params.set("client_id", clientId);
            if (sectionId) params.set("section_id", sectionId);
            setWorkspace(
                (await fetchAPI(`${BASE}/workspace?${params.toString()}`)) as KnowledgeWorkspaceResponse,
            );
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load the Knowledge Base.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [clientId, ownership, page, query, sectionId, view]);

    useEffect(() => {
        const timer = window.setTimeout(() => void loadWorkspace(), 250);
        return () => window.clearTimeout(timer);
    }, [loadWorkspace]);

    const visibleSections = useMemo(() => {
        if (!workspace) return [];
        return workspace.sections.filter((section) => {
            if (ownership !== "all" && section.ownership_type !== ownership) return false;
            if (clientId && section.client_id !== Number(clientId)) return false;
            return true;
        });
    }, [clientId, ownership, workspace]);

    function changeOwnership(value: string) {
        setOwnership(value);
        setPage(1);
        setSectionId("");
        if (value === "internal") setClientId("");
    }

    function changeClient(value: string) {
        setClientId(value);
        setPage(1);
        setSectionId("");
        if (value) setOwnership("client");
    }

    async function createFolder(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!canAddSection || !folderName.trim()) return;
        const folderOwnership = clientId ? "client" : ownership === "client" ? "client" : "internal";
        if (folderOwnership === "client" && !clientId) {
            setError("Choose a client before creating a client Knowledge Base folder.");
            return;
        }
        try {
            setIsSavingFolder(true);
            setError(null);
            await fetchAPI(`${BASE}/sections`, {
                method: "POST",
                body: JSON.stringify({
                    ownership_type: folderOwnership,
                    client_id: clientId ? Number(clientId) : null,
                    parent_id: folderParentId ? Number(folderParentId) : null,
                    name: folderName.trim(),
                    description: "",
                    order: visibleSections.length,
                }),
            });
            setFolderName("");
            setFolderParentId("");
            setShowFolderForm(false);
            const refreshedOptions = (await fetchAPI(`${BASE}/options`)) as KnowledgeOptionsResponse;
            setOptions(refreshedOptions);
            await loadWorkspace();
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Unable to create folder.");
        } finally {
            setIsSavingFolder(false);
        }
    }

    const totalPages = workspace ? Math.max(Math.ceil(workspace.total_documents / workspace.page_size), 1) : 1;

    return (
        <div className="space-y-5">
            <Card className="p-4">
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_220px_160px_auto]">
                    <Input
                        value={query}
                        onChange={(event) => {
                            setQuery(event.target.value);
                            setPage(1);
                        }}
                        placeholder="Search titles, content and tags…"
                        aria-label="Search Knowledge Base"
                    />
                    <Select value={ownership} onChange={(event) => changeOwnership(event.target.value)}>
                        <option value="all">All ownership</option>
                        <option value="internal">ADB Internal</option>
                        <option value="client">Client</option>
                    </Select>
                    <Select value={clientId} onChange={(event) => changeClient(event.target.value)}>
                        <option value="">All clients</option>
                        {options?.clients.map((client) => (
                            <option key={client.id} value={client.id}>
                                {client.label}
                            </option>
                        ))}
                    </Select>
                    <Select
                        value={view}
                        onChange={(event) => {
                            setView(event.target.value);
                            setPage(1);
                        }}
                    >
                        <option value="current">Current</option>
                        <option value="archived">Archived</option>
                        <option value="all">All</option>
                    </Select>
                    {canAddDocument ? (
                        <ButtonLink
                            href={`/admin/knowledge-base/documents/new${clientId ? `?client_id=${clientId}` : ""}`}
                        >
                            New document
                        </ButtonLink>
                    ) : null}
                </div>
            </Card>

            {error ? <DataError message={error} /> : null}

            <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
                <Card className="h-fit p-4">
                    <div className="mb-4 flex items-center justify-between gap-3">
                        <div>
                            <h2 className="text-sm font-semibold text-slate-100">Folders</h2>
                            <p className="mt-1 text-xs text-slate-500">Scoped documentation tree</p>
                        </div>
                        {canAddSection ? (
                            <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                onClick={() => setShowFolderForm((value) => !value)}
                            >
                                {showFolderForm ? "Cancel" : "Add"}
                            </Button>
                        ) : null}
                    </div>

                    {showFolderForm ? (
                        <form className="mb-4 space-y-3 border-b border-slate-800 pb-4" onSubmit={createFolder}>
                            <Input
                                value={folderName}
                                onChange={(event) => setFolderName(event.target.value)}
                                placeholder="Folder name"
                                required
                            />
                            <Select
                                value={folderParentId}
                                onChange={(event) => setFolderParentId(event.target.value)}
                            >
                                <option value="">Top level</option>
                                {visibleSections.map((section) => (
                                    <option key={section.id} value={section.id}>
                                        {section.path}
                                    </option>
                                ))}
                            </Select>
                            <Button type="submit" size="sm" disabled={isSavingFolder}>
                                {isSavingFolder ? "Creating…" : "Create folder"}
                            </Button>
                        </form>
                    ) : null}

                    <button
                        type="button"
                        onClick={() => {
                            setSectionId("");
                            setPage(1);
                        }}
                        className={`mb-1 w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                            !sectionId
                                ? "bg-adb-cyan-500/10 text-adb-cyan-200"
                                : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                        }`}
                    >
                        All documents
                    </button>
                    <div className="space-y-1">
                        {visibleSections.map((section) => (
                            <button
                                key={section.id}
                                type="button"
                                onClick={() => {
                                    setSectionId(String(section.id));
                                    setPage(1);
                                }}
                                className={`w-full rounded-lg py-2 pr-2 text-left text-sm transition ${
                                    sectionId === String(section.id)
                                        ? "bg-adb-cyan-500/10 text-adb-cyan-200"
                                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                                }`}
                                style={{ paddingLeft: `${12 + sectionDepth(section) * 16}px` }}
                                title={section.path}
                            >
                                {section.name}
                            </button>
                        ))}
                    </div>
                </Card>

                <div className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                        <p className="text-sm text-slate-400">
                            {workspace?.total_documents ?? 0} document
                            {(workspace?.total_documents ?? 0) === 1 ? "" : "s"}
                        </p>
                        {workspace && totalPages > 1 ? (
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    disabled={page <= 1}
                                    onClick={() => setPage((value) => Math.max(value - 1, 1))}
                                >
                                    Previous
                                </Button>
                                <span>
                                    {page} / {totalPages}
                                </span>
                                <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    disabled={page >= totalPages}
                                    onClick={() => setPage((value) => Math.min(value + 1, totalPages))}
                                >
                                    Next
                                </Button>
                            </div>
                        ) : null}
                    </div>

                    {isLoading && !workspace ? <DataLoading /> : null}
                    {!isLoading && workspace?.documents.length === 0 ? (
                        <Card className="p-8 text-center">
                            <p className="text-sm font-medium text-slate-300">No documentation matches this view.</p>
                            <p className="mt-2 text-xs text-slate-500">
                                Change the filters or create a document in this scope.
                            </p>
                        </Card>
                    ) : null}
                    {workspace?.documents.map((document) => (
                        <Link key={document.id} href={`/admin/knowledge-base/documents/${document.id}`}>
                            <Card className="p-5 transition hover:border-slate-700 hover:bg-slate-900/70">
                                <div className="flex flex-wrap items-start justify-between gap-4">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h2 className="font-semibold text-slate-100">{document.title}</h2>
                                            {document.archived ? <Badge variant="warning">Archived</Badge> : null}
                                            <Badge variant="neutral">
                                                {document.ownership_type === "internal"
                                                    ? "ADB Internal"
                                                    : document.client_name ?? "Client"}
                                            </Badge>
                                        </div>
                                        <p className="mt-2 text-xs text-adb-cyan-300">{document.section_path}</p>
                                        {document.summary ? (
                                            <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">
                                                {document.summary}
                                            </p>
                                        ) : null}
                                        {document.tags.length ? (
                                            <div className="mt-3 flex flex-wrap gap-1.5">
                                                {document.tags.map((tag) => (
                                                    <span
                                                        key={tag}
                                                        className="rounded-md bg-slate-900 px-2 py-1 text-[11px] text-slate-400"
                                                    >
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                        ) : null}
                                    </div>
                                    <div className="text-right text-xs text-slate-500">
                                        <p>v{document.version_count}</p>
                                        <p className="mt-1">{formatDate(document.updated_at)}</p>
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}

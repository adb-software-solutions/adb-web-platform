"use client";

import {
    Badge,
    Button,
    Card,
    DataError,
    DataLoading,
    EmptyState,
    Input,
    Select,
    Textarea,
} from "@/components/ui";
import { fetchAPI } from "@/lib/api/fetch";
import { LeadEmailAPI } from "@/lib/api/leadEmail";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";

interface LeadMailbox {
    id: number;
    email_address: string;
    display_name: string;
    brand_name: string;
    purpose: string;
}

interface EmailOptions {
    can_email: boolean;
    mailboxes: LeadMailbox[];
}

interface Conversation {
    id: number;
    reference: string;
    subject: string;
    status: string;
    priority: string;
    queue_name: string;
    last_message_at: string | null;
}

interface SendResult {
    ticket_id: number;
    ticket_reference: string;
    message_id: number;
    delivery_status: string;
}

function label(value: string) {
    return value
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");
}

function formatDate(value: string | null) {
    if (!value) return "Queued";
    return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    }).format(new Date(value));
}

export function LeadEmailPanel({ leadId }: { leadId: number }) {
    const [options, setOptions] = useState<EmailOptions | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [showComposer, setShowComposer] = useState(false);
    const [mailboxId, setMailboxId] = useState("");
    const [subject, setSubject] = useState("Following up on your enquiry");
    const [body, setBody] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const [emailOptions, conversationRows] = await Promise.all([
                fetchAPI(LeadEmailAPI.options(leadId)) as Promise<EmailOptions>,
                fetchAPI(LeadEmailAPI.conversations(leadId)) as Promise<Conversation[]>,
            ]);
            setOptions(emailOptions);
            setConversations(conversationRows);
            setMailboxId((current) => current || String(emailOptions.mailboxes[0]?.id ?? ""));
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Unable to load lead email conversations.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [leadId]);

    useEffect(() => {
        void load();
    }, [load]);

    async function sendEmail(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!mailboxId || !subject.trim() || !body.trim() || isSending) return;

        try {
            setIsSending(true);
            setError(null);
            setMessage(null);
            const result = (await fetchAPI(LeadEmailAPI.send(leadId), {
                method: "POST",
                body: JSON.stringify({
                    mailbox_id: Number(mailboxId),
                    subject: subject.trim(),
                    body_text: body.trim(),
                }),
            })) as SendResult;
            setBody("");
            setShowComposer(false);
            setMessage(
                `${result.ticket_reference} queued through Microsoft 365 and added to the lead conversation history.`,
            );
            await load();
        } catch (sendError) {
            setError(sendError instanceof Error ? sendError.message : "Unable to queue lead email.");
        } finally {
            setIsSending(false);
        }
    }

    if (isLoading && !options) return <DataLoading label="Loading lead conversations..." />;
    if (error && !options) return <DataError message={error} onRetry={() => void load()} />;

    return (
        <Card id="lead-email" className="scroll-mt-6 p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h2 className="text-sm font-semibold text-white">Email & conversations</h2>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                        Sales email is sent through a configured Microsoft 365 mailbox and kept in the
                        ticket conversation history.
                    </p>
                </div>
                {options?.can_email && options.mailboxes.length > 0 ? (
                    <Button
                        type="button"
                        variant={showComposer ? "secondary" : "outline"}
                        onClick={() => setShowComposer((value) => !value)}
                    >
                        {showComposer ? "Close composer" : "Compose email"}
                    </Button>
                ) : null}
            </div>

            {error ? (
                <div className="mt-4 rounded-lg border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
                    {error}
                </div>
            ) : null}
            {message ? (
                <div className="mt-4 rounded-lg border border-emerald-900/70 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200">
                    {message}
                </div>
            ) : null}

            {options?.can_email && options.mailboxes.length === 0 ? (
                <div className="mt-4 rounded-lg border border-amber-900/50 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">
                    No background-capable Microsoft 365 mailbox is configured for this lead&apos;s brand
                    and your queue scope.
                </div>
            ) : null}

            {showComposer && options?.can_email ? (
                <form
                    onSubmit={(event) => void sendEmail(event)}
                    className="mt-5 space-y-4 border-t border-slate-800 pt-5"
                >
                    <div className="grid gap-4 sm:grid-cols-2">
                        <label className="space-y-1.5 text-sm font-medium text-slate-300 sm:col-span-2">
                            <span>From</span>
                            <Select
                                value={mailboxId}
                                onChange={(event) => setMailboxId(event.target.value)}
                                required
                            >
                                {options.mailboxes.map((mailbox) => (
                                    <option key={mailbox.id} value={mailbox.id}>
                                        {mailbox.display_name || mailbox.email_address} — {mailbox.email_address}
                                        {` · ${label(mailbox.purpose)}`}
                                    </option>
                                ))}
                            </Select>
                        </label>
                        <label className="space-y-1.5 text-sm font-medium text-slate-300 sm:col-span-2">
                            <span>Subject</span>
                            <Input
                                value={subject}
                                onChange={(event) => setSubject(event.target.value)}
                                required
                                maxLength={500}
                            />
                        </label>
                        <label className="space-y-1.5 text-sm font-medium text-slate-300 sm:col-span-2">
                            <span>Message</span>
                            <Textarea
                                value={body}
                                onChange={(event) => setBody(event.target.value)}
                                rows={9}
                                required
                                placeholder="Write your email to this lead..."
                            />
                        </label>
                    </div>
                    <div className="flex gap-2">
                        <Button type="submit" disabled={isSending}>
                            {isSending ? "Queueing…" : "Send through Microsoft 365"}
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => setShowComposer(false)}
                            disabled={isSending}
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            ) : null}

            <div className="mt-5 border-t border-slate-800 pt-5">
                {conversations.length === 0 ? (
                    <EmptyState
                        title="No email conversations yet"
                        description="Inbound enquiries and email you send from this lead will appear here."
                    />
                ) : (
                    <div className="divide-y divide-slate-800">
                        {conversations.map((conversation) => (
                            <Link
                                key={conversation.id}
                                href={`/admin/tickets/${conversation.id}`}
                                className="flex flex-col gap-2 px-2 py-3 transition hover:bg-slate-900/50 sm:flex-row sm:items-center sm:justify-between"
                            >
                                <div className="min-w-0">
                                    <div className="truncate text-sm font-medium text-slate-200">
                                        {conversation.subject}
                                    </div>
                                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                                        <span className="font-mono text-slate-400">
                                            {conversation.reference}
                                        </span>
                                        <span>{conversation.queue_name}</span>
                                        <span>{formatDate(conversation.last_message_at)}</span>
                                    </div>
                                </div>
                                <div className="flex shrink-0 gap-2">
                                    <Badge>{label(conversation.priority)}</Badge>
                                    <Badge>{label(conversation.status)}</Badge>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </Card>
    );
}

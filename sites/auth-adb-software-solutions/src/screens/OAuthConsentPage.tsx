"use client";

import Alert from "@/components/Alert";
import {useAuth} from "@/contexts/AuthContext";
import {OAuthAuthorizationRequest, oauthApi} from "@/utils/oauthApi";
import {ShieldCheckIcon} from "@heroicons/react/24/outline";
import {useEffect, useState} from "react";

type ConsentState =
    | {kind: "loading"}
    | {kind: "error"; message: string}
    | {kind: "forbidden"}
    | {kind: "ready"; request: OAuthAuthorizationRequest}
    | {kind: "redirecting"};

const ERROR_MESSAGES: Record<string, string> = {
    invalid_client: "This application is not registered or has been disabled.",
    invalid_request:
        "This sign-in link is invalid. Start the connection again from the application.",
};

export default function OAuthConsentPage() {
    const {user} = useAuth();
    const [requestId, setRequestId] = useState<string | null>(null);
    const [state, setState] = useState<ConsentState>({kind: "loading"});
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const error = params.get("error");
        const id = params.get("request");

        if (error) {
            setState({
                kind: "error",
                message:
                    ERROR_MESSAGES[error] ??
                    params.get("error_description") ??
                    "The authorisation request could not be processed.",
            });
            return;
        }
        if (!id) {
            setState({
                kind: "error",
                message: "No authorisation request was supplied.",
            });
            return;
        }

        setRequestId(id);
        void oauthApi.getAuthorizationRequest(id).then((result) => {
            if (result.status === "ok") {
                setState({kind: "ready", request: result.data});
            } else if (result.status === "forbidden") {
                setState({kind: "forbidden"});
            } else {
                setState({kind: "error", message: result.message});
            }
        });
    }, []);

    const decide = async (approve: boolean) => {
        if (!requestId) {
            return;
        }
        setIsSubmitting(true);
        const result = await oauthApi.decide(requestId, approve);
        if (result.status === "ok") {
            setState({kind: "redirecting"});
            window.location.href = result.data.redirectTo;
            return;
        }
        setIsSubmitting(false);
        setState(
            result.status === "forbidden"
                ? {kind: "forbidden"}
                : {kind: "error", message: result.message},
        );
    };

    return (
        <div className="mx-auto max-w-lg">
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <div className="mb-6 flex items-center gap-3">
                    <ShieldCheckIcon className="text-brand h-8 w-8" />
                    <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
                        Authorise application
                    </h1>
                </div>

                {state.kind === "loading" && (
                    <div className="flex justify-center py-8">
                        <div className="border-brand h-8 w-8 animate-spin rounded-full border-4 border-t-transparent" />
                    </div>
                )}

                {state.kind === "error" && (
                    <Alert type="error">{state.message}</Alert>
                )}

                {state.kind === "forbidden" && (
                    <Alert type="error">
                        Only platform owners can authorise applications. You are
                        signed in as {user?.email ?? "another account"}.{" "}
                        <a href="/logout" className="font-medium underline">
                            Sign out
                        </a>
                    </Alert>
                )}

                {state.kind === "redirecting" && (
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                        Returning you to the application…
                    </p>
                )}

                {state.kind === "ready" && (
                    <ConsentDetails
                        request={state.request}
                        email={user?.email}
                        isSubmitting={isSubmitting}
                        onDecide={decide}
                    />
                )}
            </div>
        </div>
    );
}

function ConsentDetails({
    request,
    email,
    isSubmitting,
    onDecide,
}: {
    request: OAuthAuthorizationRequest;
    email: string | undefined;
    isSubmitting: boolean;
    onDecide: (approve: boolean) => Promise<void>;
}) {
    return (
        <div className="space-y-5">
            <p className="text-sm text-slate-700 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">
                    {request.client_name}
                </span>{" "}
                wants to access{" "}
                <span className="font-semibold text-slate-900 dark:text-white">
                    {request.resource_name}
                </span>{" "}
                as <span className="font-medium">{email}</span>.
            </p>

            <dl className="divide-y divide-slate-200 rounded-md border border-slate-200 text-sm dark:divide-slate-700 dark:border-slate-700">
                <Detail label="Returns to">
                    <code className="break-all">{request.redirect_host}</code>
                    {request.redirect_is_loopback && (
                        <span className="ml-2 text-xs text-slate-500">
                            (this computer)
                        </span>
                    )}
                </Detail>
                <Detail label="Resource">
                    <code className="break-all">{request.resource}</code>
                </Detail>
                <Detail label="Permissions">{request.scopes.join(", ")}</Detail>
                <Detail label="Client ID">
                    <code className="break-all">{request.client_id}</code>
                </Detail>
            </dl>

            {!request.redirect_is_loopback && (
                <Alert type="warning">
                    Approving sends an access code to{" "}
                    <strong>{request.redirect_host}</strong>. Only continue if
                    you started this connection from that site.
                </Alert>
            )}

            <div className="flex gap-3">
                <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => void onDecide(true)}
                    className="bg-brand flex-1 rounded-md px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50"
                >
                    Approve
                </button>
                <button
                    type="button"
                    disabled={isSubmitting}
                    onClick={() => void onDecide(false)}
                    className="flex-1 rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                    Deny
                </button>
            </div>
        </div>
    );
}

function Detail({label, children}: {label: string; children: React.ReactNode}) {
    return (
        <div className="flex gap-4 px-3 py-2">
            <dt className="w-28 shrink-0 text-slate-500">{label}</dt>
            <dd className="min-w-0 text-slate-900 dark:text-slate-100">
                {children}
            </dd>
        </div>
    );
}

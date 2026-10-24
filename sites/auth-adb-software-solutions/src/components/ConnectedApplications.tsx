"use client";

import Alert from "@/components/Alert";
import {OAuthGrant, oauthApi} from "@/utils/oauthApi";
import {TrashIcon} from "@heroicons/react/24/outline";
import {useEffect, useState} from "react";

/**
 * Applications the user has authorised through OAuth. Renders nothing for
 * accounts that are not allowed to authorise applications.
 */
export default function ConnectedApplications() {
    const [grants, setGrants] = useState<OAuthGrant[] | null>(null);
    const [hidden, setHidden] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        void oauthApi.listGrants().then((result) => {
            if (result.status === "ok") {
                setGrants(result.data);
            } else if (result.status === "forbidden") {
                setHidden(true);
            } else {
                setError(result.message);
            }
        });
    }, []);

    const revoke = async (grant: OAuthGrant) => {
        if (!confirm(`Revoke access for ${grant.client_name}?`)) {
            return;
        }
        setError(null);
        const result = await oauthApi.revokeGrant(grant.id);
        if (result.status === "ok") {
            setGrants((current) =>
                (current ?? []).filter((g) => g.id !== grant.id),
            );
        } else {
            setError(
                result.status === "error"
                    ? result.message
                    : "Failed to revoke access.",
            );
        }
    };

    if (hidden) {
        return null;
    }

    return (
        <div className="space-y-3">
            {error && <Alert type="error">{error}</Alert>}
            <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
                <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-900 dark:text-white">
                        Connected Applications
                    </h3>
                    <p className="text-xs text-slate-500">
                        Applications you have authorised with OAuth, such as MCP
                        clients
                    </p>
                </div>
                <div className="divide-y divide-slate-200 dark:divide-slate-700">
                    {grants === null ? (
                        <div className="px-4 py-8 text-center text-slate-500">
                            Loading...
                        </div>
                    ) : grants.length === 0 ? (
                        <div className="px-4 py-8 text-center text-slate-500">
                            No connected applications
                        </div>
                    ) : (
                        grants.map((grant) => (
                            <div
                                key={grant.id}
                                className="flex items-center justify-between px-4 py-4"
                            >
                                <div>
                                    <div className="font-medium text-slate-900 dark:text-white">
                                        {grant.client_name}
                                    </div>
                                    <div className="text-sm text-slate-500">
                                        {grant.resource_name} •{" "}
                                        {grant.scopes.join(", ")}
                                    </div>
                                    <div className="text-xs text-slate-400">
                                        Authorised{" "}
                                        {new Date(
                                            grant.created_at,
                                        ).toLocaleDateString()}
                                        {grant.last_used_at &&
                                            ` • Last used ${new Date(grant.last_used_at).toLocaleString()}`}
                                    </div>
                                </div>
                                <button
                                    onClick={() => void revoke(grant)}
                                    className="rounded-md p-2 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                                    title="Revoke access"
                                >
                                    <TrashIcon className="h-5 w-5" />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}

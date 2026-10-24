import {API_URL} from "./config";
import {ensureCsrfToken, fetchWithCSRF} from "./api";

export interface OAuthAuthorizationRequest {
    client_name: string;
    client_id: string;
    client_registered_at: string;
    is_dynamically_registered: boolean;
    redirect_host: string;
    redirect_is_loopback: boolean;
    resource_name: string;
    resource: string;
    scopes: string[];
    expires_at: string;
}

export interface OAuthGrant {
    id: string;
    client_name: string;
    resource_name: string;
    scopes: string[];
    created_at: string;
    last_used_at: string | null;
    expires_at: string;
}

/**
 * Result of an OAuth API call. `forbidden` means the session is missing or
 * is not a superuser; only superusers may authorise OAuth clients.
 */
export type OAuthResult<T> =
    | {status: "ok"; data: T}
    | {status: "forbidden"}
    | {status: "error"; message: string};

interface RawResponse {
    success?: boolean;
    message?: string;
    detail?: string;
}

async function parse<T>(
    response: Response,
    pick: (body: RawResponse & Record<string, unknown>) => T,
): Promise<OAuthResult<T>> {
    if (response.status === 401) {
        return {status: "forbidden"};
    }

    let body: RawResponse & Record<string, unknown> = {};
    try {
        body = (await response.json()) as RawResponse & Record<string, unknown>;
    } catch {
        // Fall through to the generic error below.
    }

    if (!response.ok || body.success === false) {
        return {
            status: "error",
            message: body.message || body.detail || "The request failed.",
        };
    }

    return {status: "ok", data: pick(body)};
}

async function post(url: string, body?: unknown): Promise<Response> {
    await ensureCsrfToken();
    return fetchWithCSRF(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        ...(body === undefined ? {} : {body: JSON.stringify(body)}),
    });
}

export const oauthApi = {
    async getAuthorizationRequest(
        requestId: string,
    ): Promise<OAuthResult<OAuthAuthorizationRequest>> {
        const response = await fetchWithCSRF(
            `${API_URL}/api/oauth/requests/${encodeURIComponent(requestId)}`,
        );
        return parse(
            response,
            (body) => body.request as OAuthAuthorizationRequest,
        );
    },

    async decide(
        requestId: string,
        approve: boolean,
    ): Promise<OAuthResult<{redirectTo: string}>> {
        const response = await post(
            `${API_URL}/api/oauth/requests/${encodeURIComponent(requestId)}/decision`,
            {approve},
        );
        return parse(response, (body) => ({
            redirectTo: body.redirect_to as string,
        }));
    },

    async listGrants(): Promise<OAuthResult<OAuthGrant[]>> {
        const response = await fetchWithCSRF(`${API_URL}/api/oauth/grants`);
        return parse(response, (body) => body.grants as OAuthGrant[]);
    },

    async revokeGrant(grantId: string): Promise<OAuthResult<null>> {
        const response = await post(
            `${API_URL}/api/oauth/grants/${encodeURIComponent(grantId)}/revoke`,
        );
        return parse(response, () => null);
    },
};

import { fetchAPI, fetchRawAPI } from "@/lib/api/fetch";
import { API_URL } from "@/lib/config";

export type CredentialStatus = "active" | "inactive" | "archived";
export type CredentialOwnership = "internal" | "client";
export type CredentialFieldKind = "text" | "password" | "textarea" | "url";
export type CredentialFieldStorage = "username" | "url" | "metadata" | "secret";

export interface CredentialField {
    key: string;
    label: string;
    kind: CredentialFieldKind;
    storage: CredentialFieldStorage;
    required: boolean;
}

export interface CredentialType {
    id: number;
    slug: string;
    name: string;
    icon: string;
    description: string;
    fields: CredentialField[];
}

export interface CredentialClientOption {
    id: number;
    name: string;
}

export interface CredentialResourceOption {
    id: number;
    name: string;
    resource_type: string;
    ownership_type: string;
    client_id: number | null;
    client_name: string | null;
}

export interface CredentialOptions {
    types: CredentialType[];
    clients: CredentialClientOption[];
    resources: CredentialResourceOption[];
}

export interface CredentialResourceLink {
    id: number;
    resource_id: number;
    resource_name: string;
    resource_type: string;
    ownership_type: string;
    client_name: string | null;
    purpose: string;
    is_primary: boolean;
}

export interface CredentialResourceLinkInput {
    resource_id: number;
    purpose?: string;
    is_primary?: boolean;
}

export interface CredentialSummary {
    id: number;
    name: string;
    status: CredentialStatus;
    ownership_type: CredentialOwnership;
    client_id: number | null;
    client_name: string | null;
    credential_type_id: number | null;
    credential_type_slug: string | null;
    credential_type_name: string | null;
    username: string;
    url: string;
    expires_at: string | null;
    last_rotated_at: string | null;
    secret_field_keys: string[];
    resource_count: number;
    has_legacy_plaintext: boolean;
    updated_at: string;
}

export interface CredentialDetail extends CredentialSummary {
    description: string;
    metadata: Record<string, string>;
    fields: CredentialField[];
    resource_links: CredentialResourceLink[];
    created_by: string | null;
    updated_by: string | null;
    created_at: string;
}

export interface CredentialPage {
    items: CredentialSummary[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

export interface CredentialCreatePayload {
    name: string;
    credential_type_id: number;
    ownership_type: CredentialOwnership;
    client_id: number | null;
    status: CredentialStatus;
    description: string;
    expires_at: string | null;
    values: Record<string, string>;
    resource_links: CredentialResourceLinkInput[];
}

export interface CredentialUpdatePayload {
    name?: string;
    status?: CredentialStatus;
    description?: string;
    expires_at?: string | null;
    clear_expires_at?: boolean;
    values?: Record<string, string>;
    clear_secret_fields?: string[];
    resource_links?: CredentialResourceLinkInput[];
}

const BASE = `${API_URL}/api/admin`;

const credentialPath = (credentialId: number) =>
    `${BASE}/credentials/${credentialId}`;

const credentialSecretPath = (credentialId: number, fieldKey: string) =>
    `${credentialPath(credentialId)}/secrets/${encodeURIComponent(fieldKey)}`;

export const CredentialVaultAPI = {
    options: () => `${BASE}/credential-options`,
    list: (query = "") => `${BASE}/credentials${query ? `?${query}` : ""}`,
    get: credentialPath,
    create: () => `${BASE}/credentials`,
    update: credentialPath,
    archive: (credentialId: number) =>
        `${credentialPath(credentialId)}/archive`,
    reveal: (credentialId: number) => `${credentialPath(credentialId)}/reveal`,
    copy: (credentialId: number, fieldKey: string) =>
        `${credentialSecretPath(credentialId, fieldKey)}/copy`,
    download: (credentialId: number, fieldKey: string) =>
        `${credentialSecretPath(credentialId, fieldKey)}/download`,
    migrateLegacy: (credentialId: number) =>
        `${credentialPath(credentialId)}/migrate-legacy-secrets`,
};

export async function downloadCredentialSecret(
    credentialId: number,
    fieldKey: string,
): Promise<void> {
    const response = await fetchRawAPI(
        CredentialVaultAPI.download(credentialId, fieldKey),
        {
            method: "POST",
        },
    );
    if (!response.ok) {
        const error = (await response.json().catch(() => ({
            message: "Unable to download credential secret.",
        }))) as { detail?: string; message?: string };
        throw new Error(
            error.detail ||
                error.message ||
                "Unable to download credential secret.",
        );
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const match = disposition.match(/filename="([^"]+)"/i);
    const filename = match?.[1] || `${fieldKey}.txt`;
    const objectUrl = URL.createObjectURL(blob);
    try {
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}

export async function copyCredentialSecret(
    credentialId: number,
    fieldKey: string,
): Promise<void> {
    const payload = (await fetchAPI(
        CredentialVaultAPI.copy(credentialId, fieldKey),
        {
            method: "POST",
        },
    )) as { field_key: string; value: string };
    await navigator.clipboard.writeText(payload.value);
}

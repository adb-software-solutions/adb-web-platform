import { API_URL } from "@/lib/config";

export interface ServiceProvider {
    id: number;
    name: string;
    slug: string;
    category: string;
    website_url: string;
    support_url: string;
    status_page_url: string;
    documentation_url: string;
    notes?: string;
    is_active: boolean;
    account_count: number;
    created_at?: string;
    updated_at: string;
}

export interface ProviderAccount {
    id: number;
    resource_id: number;
    name: string;
    provider_id: number;
    provider_name: string;
    provider_category: string;
    ownership_type: "internal" | "client";
    client_id: number | null;
    client_name: string | null;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    description?: string;
    is_portal_visible?: boolean;
    account_identifier: string;
    tenant_id: string;
    project_id: string;
    portal_url: string;
    default_region: string;
    support_plan: string;
    billing_reference: string;
    created_at?: string;
    updated_at: string;
}

export interface ProviderPage<T> {
    items: T[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
}

export interface ProviderOptions {
    categories: Array<{ value: string; label: string }>;
    clients: Array<{ id: number; name: string }>;
    providers: ServiceProvider[];
}

export interface ProviderAccountInput {
    name: string;
    provider_id: number;
    ownership_type: "internal" | "client";
    client_id?: number;
    lifecycle_status: string;
    environment: string;
    criticality: string;
    description: string;
    account_identifier: string;
    tenant_id: string;
    project_id: string;
    portal_url: string;
    default_region: string;
    support_plan: string;
    billing_reference: string;
}

export interface ServiceProviderInput {
    name: string;
    category: string;
    website_url: string;
    support_url: string;
    status_page_url: string;
    documentation_url: string;
    notes: string;
}

const infrastructurePath = `${API_URL}/api/admin/infrastructure`;

export const ProviderAPI = {
    options: () => `${infrastructurePath}/provider-options`,
    providers: (query = "") =>
        `${infrastructurePath}/providers${query ? `?${query}` : ""}`,
    provider: (providerId: number) =>
        `${infrastructurePath}/providers/${providerId}`,
    accounts: (query = "") =>
        `${infrastructurePath}/provider-accounts${query ? `?${query}` : ""}`,
    account: (accountId: number) =>
        `${infrastructurePath}/provider-accounts/${accountId}`,
    archiveAccount: (accountId: number) =>
        `${infrastructurePath}/provider-accounts/${accountId}/archive`,
};

import { API_URL } from "@/lib/config";

export interface StaffUserSummary {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    is_active: boolean;
    is_staff: boolean;
    is_superuser: boolean;
    email_verified: boolean;
    setup_pending: boolean;
    date_joined: string;
    last_login: string | null;
    group_names: string[];
}

export interface StaffUserList {
    items: StaffUserSummary[];
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
    active_count: number;
    inactive_count: number;
}

export interface CapabilityOption {
    id: number;
    code: string;
    name: string;
    app_label: string;
    model: string;
    sensitive: boolean;
}

export interface EffectiveCapability {
    code: string;
    name: string;
    sensitive: boolean;
    sources: string[];
}

export interface GroupOption {
    id: number;
    name: string;
    permission_ids: number[];
}

export interface ClientAccessOption {
    id: number;
    name: string;
    company: string;
    status: string;
}

export interface TicketQueueAccessOption {
    id: number;
    name: string;
    key: string;
    brand_name: string | null;
    enabled: boolean;
}

export interface StaffAccessOptions {
    groups: GroupOption[];
    capabilities: CapabilityOption[];
    clients: ClientAccessOption[];
    ticket_queues: TicketQueueAccessOption[];
}

export interface ObjectAccessScope {
    all: boolean;
    ids: number[];
}

export interface StaffAccessDetail {
    group_ids: number[];
    direct_permission_ids: number[];
    effective_permissions: EffectiveCapability[];
    clients: ObjectAccessScope;
    ticket_queues: ObjectAccessScope;
    default_ticket_queue_ids: number[];
}

export interface StaffUserDetail extends StaffUserSummary {
    access: StaffAccessDetail;
    can_manage: boolean;
}

export interface StaffAccessWrite {
    group_ids: number[];
    direct_permission_ids: number[];
    all_clients: boolean;
    client_ids: number[];
    all_ticket_queues: boolean;
    ticket_queue_ids: number[];
    default_ticket_queue_ids: number[];
}

export interface StaffInviteWrite extends StaffAccessWrite {
    email: string;
    first_name: string;
    last_name: string;
}

export interface StaffInviteResponse {
    user: StaffUserDetail;
    invitation_email_sent: boolean;
}

export interface StaffStatusResponse {
    user: StaffUserDetail;
    message: string;
    success: boolean;
}

export const StaffAccessAPI = {
    list: (query = "") =>
        `${API_URL}/api/admin/access/users${query ? `?${query}` : ""}`,
    options: `${API_URL}/api/admin/access/options`,
    invite: `${API_URL}/api/admin/access/users/invite`,
    detail: (userId: string) => `${API_URL}/api/admin/access/users/${userId}`,
    update: (userId: string) =>
        `${API_URL}/api/admin/access/users/${userId}/access`,
    activate: (userId: string) =>
        `${API_URL}/api/admin/access/users/${userId}/activate`,
    deactivate: (userId: string) =>
        `${API_URL}/api/admin/access/users/${userId}/deactivate`,
    resendInvitation: (userId: string) =>
        `${API_URL}/api/admin/access/users/${userId}/resend-invitation`,
};

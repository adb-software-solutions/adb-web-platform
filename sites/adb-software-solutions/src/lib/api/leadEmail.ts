const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const LeadEmailAPI = {
    options: (leadId: number) =>
        `${API_BASE_URL}/admin/leads/${leadId}/email-options`,
    conversations: (leadId: number) =>
        `${API_BASE_URL}/admin/leads/${leadId}/conversations`,
    send: (leadId: number) => `${API_BASE_URL}/admin/leads/${leadId}/email`,
};

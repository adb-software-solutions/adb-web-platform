const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const OverviewAPI = {
    clients: (query = "") =>
        `${API_BASE_URL}/admin/client-overview${query ? `?${query}` : ""}`,
    leads: (query = "") =>
        `${API_BASE_URL}/admin/lead-overview${query ? `?${query}` : ""}`,
};

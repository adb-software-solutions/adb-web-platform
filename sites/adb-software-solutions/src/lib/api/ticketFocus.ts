const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const TicketFocusAPI = {
    list: (query = "") =>
        `${API_BASE_URL}/admin/ticket-focus${query ? `?${query}` : ""}`,
    queuePreferences: () => `${API_BASE_URL}/admin/ticket-focus/queue-preferences`,
};

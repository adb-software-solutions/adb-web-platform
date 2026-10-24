import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

import OAuthConsentPage from "@/screens/OAuthConsentPage";
import {oauthApi} from "@/utils/oauthApi";

vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({user: {email: "owner@example.test"}}),
}));

vi.mock("@/utils/oauthApi", () => ({
    oauthApi: {
        getAuthorizationRequest: vi.fn(),
        decide: vi.fn(),
    },
}));

const request = {
    client_name: "Claude Code",
    client_id: "adbc_123",
    client_registered_at: "2026-10-24T10:00:00Z",
    is_dynamically_registered: true,
    redirect_host: "127.0.0.1:33418",
    redirect_is_loopback: true,
    resource_name: "Brain",
    resource: "https://brain.example.test/mcp",
    scopes: ["mcp"],
    expires_at: "2026-10-24T10:10:00Z",
};

function visit(search: string) {
    window.history.replaceState({}, "", `/oauth/consent${search}`);
}

beforeEach(() => {
    vi.mocked(oauthApi.getAuthorizationRequest).mockResolvedValue({
        status: "ok",
        data: request,
    });
});

afterEach(() => {
    vi.clearAllMocks();
});

describe("OAuth consent screen", () => {
    it("shows the client, resource and destination", async () => {
        visit("?request=abc");
        render(<OAuthConsentPage />);

        expect(await screen.findByText("Claude Code")).toBeInTheDocument();
        expect(screen.getByText("Brain")).toBeInTheDocument();
        expect(screen.getByText("127.0.0.1:33418")).toBeInTheDocument();
        expect(screen.getByText("(this computer)")).toBeInTheDocument();
        expect(oauthApi.getAuthorizationRequest).toHaveBeenCalledWith("abc");
    });

    it("warns before sending a code to a remote site", async () => {
        vi.mocked(oauthApi.getAuthorizationRequest).mockResolvedValue({
            status: "ok",
            data: {
                ...request,
                redirect_host: "claude.ai",
                redirect_is_loopback: false,
            },
        });
        visit("?request=abc");
        render(<OAuthConsentPage />);

        expect(
            await screen.findByText(
                /Only continue if you started this connection/,
            ),
        ).toBeInTheDocument();
    });

    it("tells non-owners they cannot authorise", async () => {
        vi.mocked(oauthApi.getAuthorizationRequest).mockResolvedValue({
            status: "forbidden",
        });
        visit("?request=abc");
        render(<OAuthConsentPage />);

        expect(
            await screen.findByText(
                /Only platform owners can authorise applications/,
            ),
        ).toBeInTheDocument();
        expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    });

    it("shows protocol errors without contacting the API", async () => {
        visit("?error=invalid_client");
        render(<OAuthConsentPage />);

        expect(
            await screen.findByText(/not registered or has been disabled/),
        ).toBeInTheDocument();
        expect(oauthApi.getAuthorizationRequest).not.toHaveBeenCalled();
    });

    it("submits the decision", async () => {
        vi.mocked(oauthApi.decide).mockResolvedValue({
            status: "error",
            message: "This authorisation request is no longer valid.",
        });
        visit("?request=abc");
        render(<OAuthConsentPage />);

        fireEvent.click(await screen.findByText("Deny"));

        await waitFor(() =>
            expect(oauthApi.decide).toHaveBeenCalledWith("abc", false),
        );
        expect(
            await screen.findByText(
                "This authorisation request is no longer valid.",
            ),
        ).toBeInTheDocument();
    });
});

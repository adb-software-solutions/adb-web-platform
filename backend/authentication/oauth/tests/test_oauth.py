"""Tests for the OAuth 2.1 authorisation server."""

import base64
import hashlib
import json
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from authentication.oauth import services
from authentication.oauth.models import OAuthAuthorizationRequest, OAuthClient, OAuthToken

User = get_user_model()

AUTH_FRONTEND = "https://auth.example.test"
RESOURCE = "https://brain.example.test/mcp"
REDIRECT = "http://127.0.0.1:33418/callback"


def make_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def basic(username: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()


@override_settings(AUTH_FRONTEND_URL=AUTH_FRONTEND, OAUTH_ISSUER="https://api.example.test")
class OAuthTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            email="owner@example.test",
            password="pass-123456",
            first_name="Owner",
            last_name="User",
        )
        self.staff = User.objects.create_user(
            email="staff@example.test",
            password="pass-123456",
            first_name="Staff",
            last_name="User",
            is_staff=True,
        )
        self.server, self.server_secret = services.create_resource_server("Brain", RESOURCE)
        self.introspection_auth = basic(str(self.server.id), self.server_secret)

    # Helpers ---------------------------------------------------------------

    def register(self, **overrides: Any) -> dict[str, Any]:
        metadata = {"client_name": "Claude Code", "redirect_uris": ["http://127.0.0.1/callback"]}
        metadata.update(overrides)
        response = self.client.post(
            "/oauth/register", json.dumps(metadata), content_type="application/json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def authorize(self, client_id: str, challenge: str, **overrides: str) -> Any:
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
            "state": "xyz",
        }
        params.update(overrides)
        return self.client.get(f"/oauth/authorize?{urlencode(params)}")

    def request_id_from(self, response: Any) -> str:
        self.assertEqual(response.status_code, 302)
        location = urlsplit(response["Location"])
        self.assertEqual(
            f"{location.scheme}://{location.netloc}{location.path}",
            f"{AUTH_FRONTEND}/oauth/consent",
        )
        return parse_qs(location.query)["request"][0]

    def approve(self, request_id: str, approve: bool = True) -> dict[str, Any]:
        self.client.force_login(self.superuser)
        response = self.client.post(
            f"/api/oauth/requests/{request_id}/decision",
            json.dumps({"approve": approve}),
            content_type="application/json",
        )
        self.client.logout()
        self.assertEqual(response.status_code, 200, response.content)
        return parse_qs(urlsplit(response.json()["redirect_to"]).query)

    def obtain_code(self) -> tuple[str, str, str]:
        client_id = self.register()["client_id"]
        verifier, challenge = make_pkce()
        request_id = self.request_id_from(self.authorize(client_id, challenge))
        code = self.approve(request_id)["code"][0]
        return client_id, verifier, code

    def exchange(self, client_id: str, code: str, verifier: str, **overrides: str) -> Any:
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": verifier,
            "resource": RESOURCE,
        }
        data.update(overrides)
        return self.client.post("/oauth/token", data)

    def refresh(self, client_id: str, refresh_token: str) -> Any:
        return self.client.post(
            "/oauth/token",
            {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token},
        )

    def introspect(self, token: str, auth: str | None = None) -> Any:
        return self.client.post(
            "/oauth/introspect",
            {"token": token},
            HTTP_AUTHORIZATION=auth or self.introspection_auth,
        )

    def tokens(self) -> tuple[str, dict[str, Any]]:
        client_id, verifier, code = self.obtain_code()
        response = self.exchange(client_id, code, verifier)
        self.assertEqual(response.status_code, 200, response.content)
        return client_id, response.json()


class MetadataAndRegistrationTests(OAuthTestCase):
    def test_metadata_describes_endpoints(self) -> None:
        response = self.client.get("/.well-known/oauth-authorization-server")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["issuer"], "https://api.example.test")
        self.assertEqual(data["token_endpoint"], "https://api.example.test/oauth/token")
        self.assertEqual(data["code_challenge_methods_supported"], ["S256"])
        self.assertEqual(data["scopes_supported"], ["mcp"])
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

    def test_registers_public_client(self) -> None:
        data = self.register()
        self.assertTrue(data["client_id"].startswith("adbc_"))
        self.assertEqual(data["token_endpoint_auth_method"], "none")

    def test_rejects_plain_http_redirect_to_remote_host(self) -> None:
        response = self.client.post(
            "/oauth/register",
            json.dumps({"redirect_uris": ["http://evil.example/callback"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_redirect_uri")

    def test_registers_confidential_client(self) -> None:
        data = self.register(token_endpoint_auth_method="client_secret_post")
        self.assertEqual(data["token_endpoint_auth_method"], "client_secret_post")
        self.assertEqual(data["client_secret_expires_at"], 0)
        client = OAuthClient.objects.get(client_id=data["client_id"])
        self.assertTrue(services.secret_matches(data["client_secret"], client.client_secret_hash))

    def test_public_client_gets_no_secret(self) -> None:
        self.assertNotIn("client_secret", self.register())

    def test_rejects_unknown_auth_method(self) -> None:
        response = self.client.post(
            "/oauth/register",
            json.dumps(
                {
                    "redirect_uris": ["https://app.example/callback"],
                    "token_endpoint_auth_method": "private_key_jwt",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_client_metadata")


class CsrfExemptionTests(OAuthTestCase):
    """Non-browser clients post without CSRF tokens, so these must stay exempt."""

    def test_protocol_endpoints_do_not_require_csrf(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        register = csrf_client.post(
            "/oauth/register",
            json.dumps({"redirect_uris": ["http://127.0.0.1/callback"]}),
            content_type="application/json",
        )
        self.assertEqual(register.status_code, 201)
        client_id = register.json()["client_id"]
        for path, data in [
            ("/oauth/token", {"grant_type": "refresh_token", "client_id": client_id}),
            ("/oauth/revoke", {"client_id": client_id, "token": "x"}),
            ("/oauth/introspect", {"token": "x"}),
        ]:
            response = csrf_client.post(path, data, HTTP_AUTHORIZATION=self.introspection_auth)
            self.assertNotEqual(response.status_code, 403, path)


class AuthorizeTests(OAuthTestCase):
    def test_unknown_client_is_shown_on_consent_screen_not_redirected(self) -> None:
        _, challenge = make_pkce()
        response = self.authorize("adbc_unknown", challenge)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response["Location"].startswith(f"{AUTH_FRONTEND}/oauth/consent?error=invalid_client")
        )

    def test_unregistered_redirect_is_not_followed(self) -> None:
        client_id = self.register()["client_id"]
        _, challenge = make_pkce()
        response = self.authorize(
            client_id, challenge, redirect_uri="https://evil.example/callback"
        )
        self.assertTrue(
            response["Location"].startswith(f"{AUTH_FRONTEND}/oauth/consent?error=invalid_request")
        )

    def test_loopback_redirect_accepts_any_port(self) -> None:
        client_id = self.register()["client_id"]
        _, challenge = make_pkce()
        response = self.authorize(
            client_id, challenge, redirect_uri="http://127.0.0.1:59999/callback"
        )
        self.request_id_from(response)

    def test_missing_pkce_is_returned_to_client(self) -> None:
        client_id = self.register()["client_id"]
        response = self.authorize(client_id, "", code_challenge_method="")
        location = urlsplit(response["Location"])
        self.assertEqual(location.netloc, "127.0.0.1:33418")
        query = parse_qs(location.query)
        self.assertEqual(query["error"], ["invalid_request"])
        self.assertEqual(query["state"], ["xyz"])

    def test_unknown_resource_is_rejected(self) -> None:
        client_id = self.register()["client_id"]
        _, challenge = make_pkce()
        response = self.authorize(client_id, challenge, resource="https://other.example/mcp")
        self.assertEqual(
            parse_qs(urlsplit(response["Location"]).query)["error"], ["invalid_target"]
        )

    def test_unsupported_scope_is_rejected(self) -> None:
        client_id = self.register()["client_id"]
        _, challenge = make_pkce()
        response = self.authorize(client_id, challenge, scope="mcp admin")
        self.assertEqual(parse_qs(urlsplit(response["Location"]).query)["error"], ["invalid_scope"])


class ConsentPermissionTests(OAuthTestCase):
    def pending_request(self) -> str:
        client_id = self.register()["client_id"]
        _, challenge = make_pkce()
        return self.request_id_from(self.authorize(client_id, challenge))

    def test_anonymous_user_cannot_view_request(self) -> None:
        response = self.client.get(f"/api/oauth/requests/{self.pending_request()}")
        self.assertEqual(response.status_code, 401)

    def test_non_superuser_cannot_view_or_approve(self) -> None:
        request_id = self.pending_request()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(f"/api/oauth/requests/{request_id}").status_code, 401)
        response = self.client.post(
            f"/api/oauth/requests/{request_id}/decision",
            json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(OAuthAuthorizationRequest.objects.get(id=request_id).decided_at)

    def test_superuser_sees_request_details(self) -> None:
        self.client.force_login(self.superuser)
        response = self.client.get(f"/api/oauth/requests/{self.pending_request()}")
        self.assertEqual(response.status_code, 200)
        details = response.json()["request"]
        self.assertEqual(details["client_name"], "Claude Code")
        self.assertEqual(details["resource_name"], "Brain")
        self.assertTrue(details["redirect_is_loopback"])

    def test_decision_requires_csrf_token(self) -> None:
        request_id = self.pending_request()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.superuser)
        response = csrf_client.post(
            f"/api/oauth/requests/{request_id}/decision",
            json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_request_can_only_be_decided_once(self) -> None:
        request_id = self.pending_request()
        self.approve(request_id)
        self.client.force_login(self.superuser)
        response = self.client.post(
            f"/api/oauth/requests/{request_id}/decision",
            json.dumps({"approve": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_denial_redirects_with_access_denied(self) -> None:
        query = self.approve(self.pending_request(), approve=False)
        self.assertEqual(query["error"], ["access_denied"])
        self.assertEqual(query["state"], ["xyz"])
        self.assertNotIn("code", query)

    def test_approval_redirect_carries_issuer_and_state(self) -> None:
        query = self.approve(self.pending_request())
        self.assertEqual(query["state"], ["xyz"])
        self.assertEqual(query["iss"], ["https://api.example.test"])


class TokenTests(OAuthTestCase):
    def test_full_flow_issues_introspectable_token(self) -> None:
        _, tokens = self.tokens()
        self.assertEqual(tokens["token_type"], "Bearer")
        self.assertEqual(tokens["scope"], "mcp")

        data = self.introspect(tokens["access_token"]).json()
        self.assertTrue(data["active"])
        self.assertEqual(data["username"], "owner@example.test")
        self.assertEqual(data["aud"], RESOURCE)

    def test_wrong_pkce_verifier_is_rejected(self) -> None:
        client_id, _, code = self.obtain_code()
        response = self.exchange(client_id, code, secrets.token_urlsafe(48))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_failed_exchange_still_consumes_code(self) -> None:
        client_id, verifier, code = self.obtain_code()
        self.exchange(client_id, code, secrets.token_urlsafe(48))
        response = self.exchange(client_id, code, verifier)
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_redirect_uri_must_match(self) -> None:
        client_id, verifier, code = self.obtain_code()
        response = self.exchange(
            client_id, code, verifier, redirect_uri="http://127.0.0.1:1/callback"
        )
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_resource_must_match(self) -> None:
        client_id, verifier, code = self.obtain_code()
        response = self.exchange(client_id, code, verifier, resource="https://other.example/mcp")
        self.assertEqual(response.json()["error"], "invalid_target")

    def test_code_cannot_be_used_by_another_client(self) -> None:
        _, verifier, code = self.obtain_code()
        other_client = self.register()["client_id"]
        response = self.exchange(other_client, code, verifier)
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_expired_code_is_rejected(self) -> None:
        client_id, verifier, code = self.obtain_code()
        OAuthAuthorizationRequest.objects.update(
            code_expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.exchange(client_id, code, verifier)
        self.assertEqual(response.json()["error"], "invalid_grant")

    def test_replayed_code_revokes_issued_tokens(self) -> None:
        client_id, verifier, code = self.obtain_code()
        tokens = self.exchange(client_id, code, verifier).json()
        replay = self.exchange(client_id, code, verifier)
        self.assertEqual(replay.json()["error"], "invalid_grant")
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])

    def test_refresh_rotates_tokens(self) -> None:
        client_id, tokens = self.tokens()
        response = self.refresh(client_id, tokens["refresh_token"])
        self.assertEqual(response.status_code, 200, response.content)
        rotated = response.json()
        self.assertNotEqual(rotated["refresh_token"], tokens["refresh_token"])
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])
        self.assertTrue(self.introspect(rotated["access_token"]).json()["active"])

    def test_refresh_token_reuse_revokes_grant(self) -> None:
        client_id, tokens = self.tokens()
        rotated = self.refresh(client_id, tokens["refresh_token"]).json()
        reuse = self.refresh(client_id, tokens["refresh_token"])
        self.assertEqual(reuse.json()["error"], "invalid_grant")
        self.assertFalse(self.introspect(rotated["access_token"]).json()["active"])
        self.assertEqual(
            self.refresh(client_id, rotated["refresh_token"]).json()["error"], "invalid_grant"
        )

    def test_unknown_grant_type_is_rejected(self) -> None:
        client_id = self.register()["client_id"]
        response = self.client.post(
            "/oauth/token", {"grant_type": "password", "client_id": client_id}
        )
        self.assertEqual(response.json()["error"], "unsupported_grant_type")

    def test_token_responses_are_not_cached(self) -> None:
        client_id, verifier, code = self.obtain_code()
        response = self.exchange(client_id, code, verifier)
        self.assertEqual(response["Cache-Control"], "no-store")


class LockdownTests(OAuthTestCase):
    def test_demoted_superuser_loses_access_immediately(self) -> None:
        client_id, tokens = self.tokens()
        self.superuser.is_superuser = False
        self.superuser.save()
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])
        self.assertEqual(
            self.refresh(client_id, tokens["refresh_token"]).json()["error"], "invalid_grant"
        )

    def test_deactivated_user_loses_access(self) -> None:
        _, tokens = self.tokens()
        self.superuser.is_active = False
        self.superuser.save()
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])

    def test_code_issued_before_demotion_cannot_be_exchanged(self) -> None:
        client_id, verifier, code = self.obtain_code()
        self.superuser.is_superuser = False
        self.superuser.save()
        self.assertEqual(self.exchange(client_id, code, verifier).json()["error"], "invalid_grant")

    def test_disabled_client_tokens_are_inactive(self) -> None:
        client_id, tokens = self.tokens()
        OAuthClient.objects.filter(client_id=client_id).update(is_active=False)
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])


class IntrospectionTests(OAuthTestCase):
    def test_requires_resource_server_credentials(self) -> None:
        _, tokens = self.tokens()
        response = self.introspect(tokens["access_token"], auth=basic(str(self.server.id), "wrong"))
        self.assertEqual(response.status_code, 401)
        response = self.introspect(tokens["access_token"], auth=basic("not-a-uuid", "wrong"))
        self.assertEqual(response.status_code, 401)

    def test_other_resource_server_sees_token_as_inactive(self) -> None:
        _, tokens = self.tokens()
        other, other_secret = services.create_resource_server("Other", "https://other.example/mcp")
        response = self.introspect(tokens["access_token"], auth=basic(str(other.id), other_secret))
        self.assertFalse(response.json()["active"])

    def test_refresh_tokens_are_not_introspectable(self) -> None:
        _, tokens = self.tokens()
        self.assertFalse(self.introspect(tokens["refresh_token"]).json()["active"])

    def test_expired_access_token_is_inactive(self) -> None:
        _, tokens = self.tokens()
        OAuthToken.objects.filter(token_type=OAuthToken.TYPE_ACCESS).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])


class RevocationTests(OAuthTestCase):
    def test_revoking_refresh_token_revokes_grant(self) -> None:
        client_id, tokens = self.tokens()
        response = self.client.post(
            "/oauth/revoke",
            {"client_id": client_id, "token": tokens["refresh_token"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])

    def test_cannot_revoke_another_clients_token(self) -> None:
        _, tokens = self.tokens()
        other_client = self.register()["client_id"]
        self.client.post(
            "/oauth/revoke", {"client_id": other_client, "token": tokens["refresh_token"]}
        )
        self.assertTrue(self.introspect(tokens["access_token"]).json()["active"])

    def test_user_can_list_and_revoke_connected_apps(self) -> None:
        _, tokens = self.tokens()
        self.client.force_login(self.superuser)
        grants = self.client.get("/api/oauth/grants").json()["grants"]
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0]["client_name"], "Claude Code")

        response = self.client.post(f"/api/oauth/grants/{grants[0]['id']}/revoke")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.introspect(tokens["access_token"]).json()["active"])
        self.assertEqual(self.client.get("/api/oauth/grants").json()["grants"], [])

    def test_connected_apps_require_superuser(self) -> None:
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/api/oauth/grants").status_code, 401)


class ConfidentialClientTests(OAuthTestCase):
    def test_basic_authenticated_client_completes_flow(self) -> None:
        client, secret = services.create_confidential_client("Brain web", [REDIRECT])
        verifier, challenge = make_pkce()
        request_id = self.request_id_from(self.authorize(client.client_id, challenge))
        code = self.approve(request_id)["code"][0]

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": verifier,
            "resource": RESOURCE,
        }
        response = self.client.post(
            "/oauth/token", data, HTTP_AUTHORIZATION=basic(client.client_id, secret)
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_wrong_secret_is_rejected(self) -> None:
        client, _ = services.create_confidential_client("Brain web", [REDIRECT])
        response = self.client.post(
            "/oauth/token",
            {"grant_type": "authorization_code", "code": "x"},
            HTTP_AUTHORIZATION=basic(client.client_id, "wrong"),
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_client")

    def test_confidential_client_cannot_skip_secret(self) -> None:
        client, _ = services.create_confidential_client("Brain web", [REDIRECT])
        response = self.client.post(
            "/oauth/token",
            {"grant_type": "authorization_code", "client_id": client.client_id, "code": "x"},
        )
        self.assertEqual(response.status_code, 401)

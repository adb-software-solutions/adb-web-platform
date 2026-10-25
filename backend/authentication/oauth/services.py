"""Domain services for the OAuth 2.1 authorisation server.

Only the subset of OAuth that the MCP authorisation specification needs is
implemented: the authorisation code grant with mandatory S256 PKCE, refresh
token rotation, RFC 7591 dynamic registration, RFC 7662 introspection,
RFC 7009 revocation and RFC 8707 resource indicators.

Authorising a client is restricted to active superusers, and that restriction
is re-checked whenever a token is refreshed or introspected, so demoting or
deactivating the account cuts off every client immediately.
"""

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from authentication.oauth.models import (
    OAuthAuthorizationRequest,
    OAuthClient,
    OAuthGrant,
    OAuthResourceServer,
    OAuthToken,
)

AUTHORIZATION_REQUEST_TTL = timedelta(minutes=10)
AUTHORIZATION_CODE_TTL = timedelta(seconds=60)
ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
GRANT_MAX_AGE = timedelta(days=90)
LAST_USED_RESOLUTION = timedelta(minutes=5)
EXPIRED_RECORD_RETENTION = timedelta(days=1)

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
MAX_REDIRECT_URIS = 10
MAX_CLIENT_NAME_LENGTH = 150

ACCESS_TOKEN_PREFIX = "adbat_"
REFRESH_TOKEN_PREFIX = "adbrt_"
CLIENT_ID_PREFIX = "adbc_"

CODE_VERIFIER_PATTERN = re.compile(r"[A-Za-z0-9\-._~]{43,128}")


class OAuthError(Exception):
    """An RFC 6749 error response."""

    def __init__(self, error: str, description: str, status: int = 400) -> None:
        self.error = error
        self.description = description
        self.status = status
        super().__init__(f"{error}: {description}")


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    scope: str

    def as_response(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": "Bearer",
            "expires_in": int(ACCESS_TOKEN_TTL.total_seconds()),
            "refresh_token": self.refresh_token,
            "scope": self.scope,
        }


# ============================================================================
# Primitives
# ============================================================================


def issuer() -> str:
    return str(settings.OAUTH_ISSUER).rstrip("/")


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def secret_matches(value: str, expected_hash: str) -> bool:
    if not value or not expected_hash:
        return False
    return hmac.compare_digest(hash_secret(value), expected_hash)


def generate_secret(prefix: str = "") -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def pkce_matches(verifier: str, challenge: str) -> bool:
    """Verify an RFC 7636 S256 code verifier against its challenge."""
    if not CODE_VERIFIER_PATTERN.fullmatch(verifier):
        return False
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return hmac.compare_digest(expected, challenge)


def is_superuser_allowed(user: Any) -> bool:
    return bool(user is not None and user.is_active and user.is_superuser)


# ============================================================================
# Redirect URIs
# ============================================================================


def _is_loopback(host: str | None) -> bool:
    return (host or "").lower() in LOOPBACK_HOSTS


def validate_redirect_uri(uri: str) -> None:
    """Reject redirect URIs that are unsafe to register.

    HTTPS is allowed for any host because the consent screen shows the
    destination and only a superuser can approve. Plain HTTP is allowed only
    for loopback addresses used by native and CLI clients (RFC 8252).
    """
    if not isinstance(uri, str) or len(uri) > 2000:
        raise OAuthError(
            "invalid_redirect_uri", "Redirect URIs must be strings under 2000 characters."
        )
    parts = urlsplit(uri)
    if parts.fragment:
        raise OAuthError("invalid_redirect_uri", "Redirect URIs must not contain a fragment.")
    if not parts.hostname:
        raise OAuthError("invalid_redirect_uri", "Redirect URIs must be absolute URLs.")
    if parts.username or parts.password:
        raise OAuthError("invalid_redirect_uri", "Redirect URIs must not contain credentials.")
    if parts.scheme == "https":
        return
    if parts.scheme == "http" and _is_loopback(parts.hostname):
        return
    raise OAuthError(
        "invalid_redirect_uri",
        "Redirect URIs must use HTTPS, or HTTP on a loopback address.",
    )


def redirect_uri_registered(client: OAuthClient, uri: str) -> bool:
    """Match a requested redirect URI exactly, ignoring the port on loopback.

    RFC 8252 section 7.3 requires loopback redirects to accept any port,
    because native clients bind an ephemeral port at request time.
    """
    if uri in client.redirect_uris:
        return True
    requested = urlsplit(uri)
    if requested.scheme != "http" or not _is_loopback(requested.hostname):
        return False
    for registered_uri in client.redirect_uris:
        registered = urlsplit(registered_uri)
        if (
            registered.scheme == "http"
            and (registered.hostname or "").lower() == (requested.hostname or "").lower()
            and registered.path == requested.path
            and registered.query == requested.query
        ):
            return True
    return False


def build_redirect(redirect_uri: str, params: dict[str, str]) -> str:
    """Append response parameters to a redirect URI, keeping its own query."""
    parts = urlsplit(redirect_uri)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend((key, value) for key, value in params.items() if value)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


# ============================================================================
# Clients and resource servers
# ============================================================================


def register_client(metadata: dict[str, Any]) -> tuple[OAuthClient, str]:
    """Register a client from RFC 7591 metadata.

    Returns the client and its secret, which is empty for public clients.
    Confidential clients (such as claude.ai's connectors) still need PKCE.
    """
    redirect_uris = metadata.get("redirect_uris")
    if not isinstance(redirect_uris, list) or not redirect_uris:
        raise OAuthError("invalid_redirect_uri", "At least one redirect URI is required.")
    if len(redirect_uris) > MAX_REDIRECT_URIS:
        raise OAuthError("invalid_redirect_uri", "Too many redirect URIs.")
    for uri in redirect_uris:
        validate_redirect_uri(uri)

    auth_method = metadata.get("token_endpoint_auth_method", OAuthClient.AUTH_METHOD_NONE)
    if auth_method not in dict(OAuthClient.AUTH_METHOD_CHOICES):
        raise OAuthError("invalid_client_metadata", "Unsupported token endpoint auth method.")

    grant_types = metadata.get("grant_types", ["authorization_code", "refresh_token"])
    if not isinstance(grant_types, list) or "authorization_code" not in grant_types:
        raise OAuthError("invalid_client_metadata", "The authorization_code grant is required.")
    if set(grant_types) - {"authorization_code", "refresh_token"}:
        raise OAuthError("invalid_client_metadata", "Unsupported grant type requested.")

    response_types = metadata.get("response_types", ["code"])
    if response_types != ["code"]:
        raise OAuthError("invalid_client_metadata", "Only the code response type is supported.")

    client_name = metadata.get("client_name") or "Unnamed client"
    if not isinstance(client_name, str):
        raise OAuthError("invalid_client_metadata", "client_name must be a string.")

    secret = "" if auth_method == OAuthClient.AUTH_METHOD_NONE else generate_secret()
    client = OAuthClient.objects.create(
        client_id=generate_secret(CLIENT_ID_PREFIX),
        client_name=client_name.strip()[:MAX_CLIENT_NAME_LENGTH] or "Unnamed client",
        redirect_uris=redirect_uris,
        token_endpoint_auth_method=auth_method,
        client_secret_hash=hash_secret(secret) if secret else "",
        is_dynamically_registered=True,
    )
    return client, secret


def registration_response(client: OAuthClient, secret: str = "") -> dict[str, Any]:
    response: dict[str, Any] = {
        "client_id": client.client_id,
        "client_id_issued_at": int(client.created_at.timestamp()),
        "client_name": client.client_name,
        "redirect_uris": client.redirect_uris,
        "token_endpoint_auth_method": client.token_endpoint_auth_method,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
    }
    if secret:
        response["client_secret"] = secret
        response["client_secret_expires_at"] = 0
    return response


def create_confidential_client(
    client_name: str,
    redirect_uris: list[str],
    auth_method: str = OAuthClient.AUTH_METHOD_SECRET_BASIC,
) -> tuple[OAuthClient, str]:
    """Create a pre-registered server-side client and return its secret once."""
    if auth_method == OAuthClient.AUTH_METHOD_NONE:
        raise ValueError("Confidential clients need a secret-based authentication method.")
    for uri in redirect_uris:
        validate_redirect_uri(uri)
    secret = generate_secret()
    client = OAuthClient.objects.create(
        client_id=generate_secret(CLIENT_ID_PREFIX),
        client_name=client_name,
        redirect_uris=redirect_uris,
        token_endpoint_auth_method=auth_method,
        client_secret_hash=hash_secret(secret),
    )
    return client, secret


def create_resource_server(
    name: str,
    resource: str,
    scopes: list[str] | None = None,
) -> tuple[OAuthResourceServer, str]:
    """Create a resource server and return its introspection secret once."""
    secret = generate_secret()
    server = OAuthResourceServer.objects.create(
        name=name,
        resource=resource,
        scopes=scopes or ["mcp"],
        introspection_secret_hash=hash_secret(secret),
    )
    return server, secret


def authenticate_client(
    client_id: str,
    client_secret: str,
    used_basic: bool,
) -> OAuthClient:
    """Authenticate a client at the token or revocation endpoint."""
    client = OAuthClient.objects.filter(client_id=client_id, is_active=True).first()
    if client is None:
        raise OAuthError("invalid_client", "Client authentication failed.", status=401)

    method = client.token_endpoint_auth_method
    if method == OAuthClient.AUTH_METHOD_NONE:
        if client_secret:
            raise OAuthError("invalid_client", "Public clients must not send a secret.", status=401)
        return client
    if method == OAuthClient.AUTH_METHOD_SECRET_BASIC and not used_basic:
        raise OAuthError(
            "invalid_client", "This client must use HTTP Basic authentication.", status=401
        )
    if method == OAuthClient.AUTH_METHOD_SECRET_POST and used_basic:
        raise OAuthError(
            "invalid_client", "This client must send its secret in the form body.", status=401
        )
    if not secret_matches(client_secret, client.client_secret_hash):
        raise OAuthError("invalid_client", "Client authentication failed.", status=401)
    return client


def authenticate_resource_server(server_id: str, secret: str) -> OAuthResourceServer | None:
    try:
        parsed_id = uuid.UUID(server_id)
    except ValueError:
        return None
    server = OAuthResourceServer.objects.filter(id=parsed_id, is_active=True).first()
    if server is None or not secret_matches(secret, server.introspection_secret_hash):
        return None
    return server


def _resource_server_for(resource: str) -> OAuthResourceServer | None:
    candidates = {resource, resource.rstrip("/")}
    return OAuthResourceServer.objects.filter(resource__in=candidates, is_active=True).first()


def _resolve_scope(requested: str, server: OAuthResourceServer) -> str:
    allowed = list(server.scopes) or ["mcp"]
    if not requested.strip():
        return " ".join(allowed)
    scopes = requested.split()
    unknown = [scope for scope in scopes if scope not in allowed]
    if unknown:
        raise OAuthError("invalid_scope", f"Unsupported scope: {' '.join(unknown)}.")
    return " ".join(dict.fromkeys(scopes))


# ============================================================================
# Authorisation requests and consent
# ============================================================================


def get_client_for_authorization(client_id: str, redirect_uri: str) -> OAuthClient:
    """Validate the parts of a request that decide whether we may redirect.

    Errors raised here must be shown to the user rather than sent to the
    redirect URI, because the URI itself is untrusted until it matches.
    """
    client = OAuthClient.objects.filter(client_id=client_id, is_active=True).first()
    if client is None:
        raise OAuthError("invalid_client", "Unknown or disabled client.")
    if not redirect_uri or not redirect_uri_registered(client, redirect_uri):
        raise OAuthError("invalid_request", "The redirect URI is not registered for this client.")
    return client


def create_authorization_request(
    client: OAuthClient, params: dict[str, str]
) -> OAuthAuthorizationRequest:
    """Validate the remaining authorisation parameters and store the request."""
    if params.get("response_type") != "code":
        raise OAuthError("unsupported_response_type", "Only response_type=code is supported.")
    challenge = params.get("code_challenge", "")
    if params.get("code_challenge_method") != "S256" or not 43 <= len(challenge) <= 128:
        raise OAuthError("invalid_request", "PKCE with code_challenge_method=S256 is required.")
    resource = params.get("resource", "")
    if not resource:
        raise OAuthError("invalid_target", "A resource parameter is required.")
    server = _resource_server_for(resource)
    if server is None:
        raise OAuthError("invalid_target", "Unknown resource.")
    scope = _resolve_scope(params.get("scope", ""), server)

    now = timezone.now()
    OAuthAuthorizationRequest.objects.filter(expires_at__lt=now - EXPIRED_RECORD_RETENTION).delete()
    return OAuthAuthorizationRequest.objects.create(
        id=secrets.token_urlsafe(32),
        client=client,
        resource_server=server,
        redirect_uri=params["redirect_uri"],
        scope=scope,
        state=params.get("state", "")[:2000],
        code_challenge=challenge,
        expires_at=now + AUTHORIZATION_REQUEST_TTL,
    )


def get_pending_request(request_id: str) -> OAuthAuthorizationRequest | None:
    auth_request = (
        OAuthAuthorizationRequest.objects.select_related("client", "resource_server")
        .filter(id=request_id, decided_at__isnull=True)
        .first()
    )
    if auth_request is None or auth_request.is_expired:
        return None
    return auth_request


def decide_authorization_request(
    auth_request: OAuthAuthorizationRequest,
    user: Any,
    approve: bool,
) -> str:
    """Record the user's decision and return the client redirect URL."""
    if not is_superuser_allowed(user):
        raise OAuthError(
            "access_denied", "Only superusers may authorise OAuth clients.", status=403
        )

    with transaction.atomic():
        locked = OAuthAuthorizationRequest.objects.select_for_update().get(id=auth_request.id)
        if locked.decided_at is not None or locked.is_expired:
            raise OAuthError("invalid_request", "This authorisation request is no longer valid.")
        locked.user = user
        locked.decided_at = timezone.now()
        locked.approved = approve
        params = {"state": locked.state, "iss": issuer()}
        if approve:
            code = generate_secret()
            locked.code_hash = hash_secret(code)
            locked.code_expires_at = locked.decided_at + AUTHORIZATION_CODE_TTL
            params["code"] = code
        else:
            params["error"] = "access_denied"
            params["error_description"] = "The user denied the request."
        locked.save()
    return build_redirect(locked.redirect_uri, params)


# ============================================================================
# Tokens
# ============================================================================


def _issue_tokens(grant: OAuthGrant) -> IssuedTokens:
    now = timezone.now()
    access = generate_secret(ACCESS_TOKEN_PREFIX)
    refresh = generate_secret(REFRESH_TOKEN_PREFIX)
    OAuthToken.objects.bulk_create(
        [
            OAuthToken(
                grant=grant,
                token_type=OAuthToken.TYPE_ACCESS,
                token_hash=hash_secret(access),
                expires_at=now + ACCESS_TOKEN_TTL,
            ),
            OAuthToken(
                grant=grant,
                token_type=OAuthToken.TYPE_REFRESH,
                token_hash=hash_secret(refresh),
                expires_at=min(now + REFRESH_TOKEN_TTL, grant.expires_at),
            ),
        ]
    )
    OAuthToken.objects.filter(grant=grant, expires_at__lt=now - EXPIRED_RECORD_RETENTION).delete()
    return IssuedTokens(access_token=access, refresh_token=refresh, scope=grant.scope)


def revoke_grant(grant: OAuthGrant) -> None:
    now = timezone.now()
    with transaction.atomic():
        OAuthGrant.objects.filter(id=grant.id, revoked_at__isnull=True).update(revoked_at=now)
        OAuthToken.objects.filter(grant=grant, revoked_at__isnull=True).update(revoked_at=now)


def _resource_param_matches(resource: str, server: OAuthResourceServer) -> bool:
    return not resource or resource.rstrip("/") == server.resource.rstrip("/")


def exchange_authorization_code(
    client: OAuthClient,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    resource: str,
) -> IssuedTokens:
    """Exchange a single-use authorisation code for tokens."""
    if not code:
        raise OAuthError("invalid_request", "The code parameter is required.")

    # Failures are raised after the transaction commits so that marking the
    # code as used, and revoking a grant on replay, are never rolled back.
    with transaction.atomic():
        result = _exchange_locked(client, code, redirect_uri, code_verifier, resource)
    if isinstance(result, OAuthError):
        raise result
    return result


def _exchange_locked(
    client: OAuthClient,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    resource: str,
) -> IssuedTokens | OAuthError:
    auth_request = (
        OAuthAuthorizationRequest.objects.select_for_update(of=("self",))
        .select_related("resource_server", "user", "grant")
        .filter(code_hash=hash_secret(code))
        .first()
    )
    if auth_request is None or auth_request.client_id != client.id:
        return OAuthError("invalid_grant", "Invalid authorisation code.")
    if auth_request.code_used_at is not None:
        # RFC 6749 section 4.1.2: a replayed code revokes what it issued.
        if auth_request.grant is not None:
            revoke_grant(auth_request.grant)
        return OAuthError("invalid_grant", "Authorisation code has already been used.")

    now = timezone.now()
    auth_request.code_used_at = now
    auth_request.save(update_fields=["code_used_at"])

    if auth_request.code_expires_at is None or now >= auth_request.code_expires_at:
        return OAuthError("invalid_grant", "Authorisation code has expired.")
    if redirect_uri != auth_request.redirect_uri:
        return OAuthError("invalid_grant", "The redirect URI does not match the authorisation.")
    if not pkce_matches(code_verifier, auth_request.code_challenge):
        return OAuthError("invalid_grant", "PKCE verification failed.")
    if not _resource_param_matches(resource, auth_request.resource_server):
        return OAuthError("invalid_target", "The resource does not match the authorisation.")
    user = auth_request.user
    if user is None or not is_superuser_allowed(user) or not auth_request.resource_server.is_active:
        return OAuthError("invalid_grant", "This authorisation is no longer permitted.")

    grant = OAuthGrant.objects.create(
        client=client,
        resource_server=auth_request.resource_server,
        user=user,
        scope=auth_request.scope,
        expires_at=now + GRANT_MAX_AGE,
        last_used_at=now,
    )
    auth_request.grant = grant
    auth_request.save(update_fields=["grant"])
    client.last_used_at = now
    client.save(update_fields=["last_used_at"])
    return _issue_tokens(grant)


def refresh_tokens(
    client: OAuthClient, refresh_token: str, resource: str, scope: str
) -> IssuedTokens:
    """Rotate a refresh token, revoking the grant if a used token is replayed."""
    if not refresh_token:
        raise OAuthError("invalid_request", "The refresh_token parameter is required.")

    with transaction.atomic():
        result = _refresh_locked(client, refresh_token, resource, scope)
    if isinstance(result, OAuthError):
        raise result
    return result


def _refresh_locked(
    client: OAuthClient,
    refresh_token: str,
    resource: str,
    scope: str,
) -> IssuedTokens | OAuthError:
    token = (
        OAuthToken.objects.select_for_update(of=("self",))
        .select_related("grant", "grant__user", "grant__resource_server")
        .filter(token_hash=hash_secret(refresh_token), token_type=OAuthToken.TYPE_REFRESH)
        .first()
    )
    if token is None or token.grant.client_id != client.id:
        return OAuthError("invalid_grant", "Invalid refresh token.")
    grant = token.grant
    if token.rotated_at is not None:
        revoke_grant(grant)
        return OAuthError("invalid_grant", "Refresh token reuse detected; the grant was revoked.")
    now = timezone.now()
    if token.revoked_at is not None or now >= token.expires_at or not grant.is_usable:
        return OAuthError("invalid_grant", "Refresh token has expired or been revoked.")
    if not is_superuser_allowed(grant.user) or not grant.resource_server.is_active:
        revoke_grant(grant)
        return OAuthError("invalid_grant", "This authorisation is no longer permitted.")
    if not _resource_param_matches(resource, grant.resource_server):
        return OAuthError("invalid_target", "The resource does not match the authorisation.")
    if scope and not set(scope.split()) <= set(grant.scope.split()):
        return OAuthError("invalid_scope", "Refresh cannot widen the granted scope.")

    token.rotated_at = now
    token.save(update_fields=["rotated_at"])
    OAuthToken.objects.filter(
        grant=grant,
        token_type=OAuthToken.TYPE_ACCESS,
        revoked_at__isnull=True,
    ).update(revoked_at=now)
    grant.last_used_at = now
    grant.save(update_fields=["last_used_at"])
    client.last_used_at = now
    client.save(update_fields=["last_used_at"])
    return _issue_tokens(grant)


def introspect_token(server: OAuthResourceServer, token_value: str) -> dict[str, Any]:
    """Describe an access token to the resource server it was issued for."""
    inactive: dict[str, Any] = {"active": False}
    if not token_value:
        return inactive
    token = (
        OAuthToken.objects.select_related("grant", "grant__user", "grant__client")
        .filter(token_hash=hash_secret(token_value), token_type=OAuthToken.TYPE_ACCESS)
        .first()
    )
    if token is None:
        return inactive
    grant = token.grant
    now = timezone.now()
    if (
        token.revoked_at is not None
        or now >= token.expires_at
        or not grant.is_usable
        or grant.resource_server_id != server.id
        or not grant.client.is_active
        or not is_superuser_allowed(grant.user)
    ):
        return inactive

    if grant.last_used_at is None or now - grant.last_used_at > LAST_USED_RESOLUTION:
        OAuthGrant.objects.filter(id=grant.id).update(last_used_at=now)

    return {
        "active": True,
        "scope": grant.scope,
        "client_id": grant.client.client_id,
        "username": grant.user.email,
        "sub": str(grant.user.id),
        "token_type": "Bearer",
        "exp": int(token.expires_at.timestamp()),
        "iat": int(token.created_at.timestamp()),
        "aud": server.resource,
        "iss": issuer(),
    }


def revoke_token(client: OAuthClient, token_value: str) -> None:
    """RFC 7009 revocation. Unknown tokens are silently ignored."""
    token = (
        OAuthToken.objects.select_related("grant")
        .filter(token_hash=hash_secret(token_value), grant__client=client)
        .first()
    )
    if token is None:
        return
    if token.token_type == OAuthToken.TYPE_REFRESH:
        revoke_grant(token.grant)
    else:
        OAuthToken.objects.filter(id=token.id, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )


def server_metadata() -> dict[str, Any]:
    """RFC 8414 authorisation server metadata."""
    base = issuer()
    scopes = sorted(
        {
            scope
            for scopes in OAuthResourceServer.objects.filter(is_active=True).values_list(
                "scopes", flat=True
            )
            for scope in (scopes or ["mcp"])
        }
    )
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/oauth/register",
        "revocation_endpoint": f"{base}/oauth/revoke",
        "introspection_endpoint": f"{base}/oauth/introspect",
        "scopes_supported": scopes,
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": [
            OAuthClient.AUTH_METHOD_NONE,
            OAuthClient.AUTH_METHOD_SECRET_BASIC,
            OAuthClient.AUTH_METHOD_SECRET_POST,
        ],
        "revocation_endpoint_auth_methods_supported": [
            OAuthClient.AUTH_METHOD_NONE,
            OAuthClient.AUTH_METHOD_SECRET_BASIC,
            OAuthClient.AUTH_METHOD_SECRET_POST,
        ],
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "authorization_response_iss_parameter_supported": True,
    }

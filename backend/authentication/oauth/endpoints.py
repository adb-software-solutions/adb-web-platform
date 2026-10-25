"""OAuth 2.1 protocol endpoints.

These are plain Django views rather than Django Ninja routes because OAuth
fixes their request encoding (form bodies, HTTP Basic client credentials) and
error format. None of them read the session cookie: the browser-facing consent
step happens in the authentication frontend through ``authentication.oauth.views``.
"""

import base64
import binascii
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import unquote, urlencode

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from authentication.oauth import services
from authentication.oauth.services import OAuthError
from authentication.ratelimit import check_rate_limit_for_request, get_client_ip

logger = logging.getLogger(__name__)

View = Callable[..., HttpResponse]


def _no_store(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    return response


def _error(exc: OAuthError) -> HttpResponse:
    response = JsonResponse(
        {"error": exc.error, "error_description": exc.description},
        status=exc.status,
    )
    if exc.status == 401:
        response["WWW-Authenticate"] = 'Basic realm="oauth"'
    return _no_store(response)


def _public_cors(view: View) -> View:
    """Allow browser-based MCP clients to call an endpoint without cookies."""

    # wraps() also carries over the csrf_exempt marker set on the inner view.
    @wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = view(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, MCP-Protocol-Version"
        )
        response["Access-Control-Max-Age"] = "86400"
        return response

    return wrapper


def _rate_limited(request: HttpRequest, limit_type: str) -> HttpResponse | None:
    allowed, message, retry_after = check_rate_limit_for_request(
        request,
        limit_type,
        get_client_ip(request),
    )
    if allowed:
        return None
    response = _error(OAuthError("slow_down", message or "Too many requests.", status=429))
    response["Retry-After"] = str(retry_after)
    return response


def _basic_credentials(request: HttpRequest) -> tuple[str, str] | None:
    """Decode RFC 6749 section 2.3.1 HTTP Basic client credentials."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, encoded = header.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        return None
    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return unquote(username), unquote(password)


def _authenticate_client(request: HttpRequest) -> services.OAuthClient:
    basic = _basic_credentials(request)
    if basic is not None:
        client_id, client_secret = basic
        return services.authenticate_client(client_id, client_secret, used_basic=True)
    return services.authenticate_client(
        request.POST.get("client_id", ""),
        request.POST.get("client_secret", ""),
        used_basic=False,
    )


@_public_cors
@require_http_methods(["GET", "OPTIONS"])
def authorization_server_metadata(request: HttpRequest) -> HttpResponse:
    """RFC 8414 discovery document."""
    response = JsonResponse(services.server_metadata())
    response["Cache-Control"] = "public, max-age=300"
    return response


@require_http_methods(["GET"])
def authorize(request: HttpRequest) -> HttpResponse:
    """Validate an authorisation request and hand it to the consent screen."""
    limited = _rate_limited(request, "oauth_authorize")
    if limited is not None:
        return limited

    params = {key: request.GET.get(key, "") for key in request.GET}
    consent_url = f"{settings.AUTH_FRONTEND_URL.rstrip('/')}/oauth/consent"

    try:
        client = services.get_client_for_authorization(
            params.get("client_id", ""),
            params.get("redirect_uri", ""),
        )
    except OAuthError as exc:
        # The redirect URI is untrusted, so show the error ourselves.
        query = urlencode({"error": exc.error, "error_description": exc.description})
        return HttpResponseRedirect(f"{consent_url}?{query}")

    try:
        auth_request = services.create_authorization_request(client, params)
    except OAuthError as exc:
        return HttpResponseRedirect(
            services.build_redirect(
                params["redirect_uri"],
                {
                    "error": exc.error,
                    "error_description": exc.description,
                    "state": params.get("state", ""),
                    "iss": services.issuer(),
                },
            )
        )

    return HttpResponseRedirect(f"{consent_url}?{urlencode({'request': auth_request.id})}")


@_public_cors
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def token(request: HttpRequest) -> HttpResponse:
    """Authorisation code and refresh token grants."""
    limited = _rate_limited(request, "oauth_token")
    if limited is not None:
        return limited

    try:
        client = _authenticate_client(request)
        grant_type = request.POST.get("grant_type", "")
        if grant_type == "authorization_code":
            issued = services.exchange_authorization_code(
                client,
                code=request.POST.get("code", ""),
                redirect_uri=request.POST.get("redirect_uri", ""),
                code_verifier=request.POST.get("code_verifier", ""),
                resource=request.POST.get("resource", ""),
            )
        elif grant_type == "refresh_token":
            issued = services.refresh_tokens(
                client,
                refresh_token=request.POST.get("refresh_token", ""),
                resource=request.POST.get("resource", ""),
                scope=request.POST.get("scope", ""),
            )
        else:
            raise OAuthError("unsupported_grant_type", "Unsupported grant_type.")
    except OAuthError as exc:
        logger.info("OAuth token request rejected: %s", exc.error)
        return _error(exc)

    return _no_store(JsonResponse(issued.as_response()))


@_public_cors
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def register(request: HttpRequest) -> HttpResponse:
    """RFC 7591 dynamic client registration for public clients."""
    limited = _rate_limited(request, "oauth_register")
    if limited is not None:
        return limited

    try:
        metadata = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error(OAuthError("invalid_client_metadata", "The request body must be JSON."))
    if not isinstance(metadata, dict):
        return _error(
            OAuthError("invalid_client_metadata", "The request body must be a JSON object.")
        )

    try:
        client, secret = services.register_client(metadata)
    except OAuthError as exc:
        return _error(exc)

    logger.info("Registered OAuth client %s (%s)", client.client_id, client.client_name)
    return _no_store(JsonResponse(services.registration_response(client, secret), status=201))


@csrf_exempt
@require_http_methods(["POST"])
def introspect(request: HttpRequest) -> HttpResponse:
    """RFC 7662 introspection for registered resource servers."""
    credentials = _basic_credentials(request)
    server = services.authenticate_resource_server(*credentials) if credentials else None
    if server is None:
        limited = _rate_limited(request, "oauth_introspect_failure")
        if limited is not None:
            return limited
        return _error(
            OAuthError("invalid_client", "Resource server authentication failed.", status=401)
        )

    return _no_store(JsonResponse(services.introspect_token(server, request.POST.get("token", ""))))


@_public_cors
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def revoke(request: HttpRequest) -> HttpResponse:
    """RFC 7009 token revocation."""
    limited = _rate_limited(request, "oauth_token")
    if limited is not None:
        return limited

    try:
        client = _authenticate_client(request)
    except OAuthError as exc:
        return _error(exc)
    services.revoke_token(client, request.POST.get("token", ""))
    return _no_store(HttpResponse(status=200))

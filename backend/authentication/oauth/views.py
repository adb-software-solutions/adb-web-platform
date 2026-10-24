"""Consent and connected-application API for the authentication frontend.

Every route requires an authenticated superuser session. ``SessionAuthSuperUser``
also enforces Django CSRF protection on unsafe methods.
"""

import logging
import uuid
from typing import Any, cast
from urllib.parse import urlsplit

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.security import SessionAuthSuperUser

from authentication.models import User
from authentication.oauth import services
from authentication.oauth.models import OAuthGrant
from authentication.oauth.services import OAuthError

logger = logging.getLogger(__name__)

oauth_router = Router(tags=["oauth"], auth=SessionAuthSuperUser())


class AuthorizationDecisionRequest(Schema):
    approve: bool


@oauth_router.get("/requests/{request_id}", response={200: dict, 404: dict})
def get_authorization_request(request: HttpRequest, request_id: str) -> tuple[int, dict[str, Any]]:
    """Describe a pending authorisation request for the consent screen."""
    auth_request = services.get_pending_request(request_id)
    if auth_request is None:
        return 404, {
            "success": False,
            "message": "This authorisation request has expired or was already used.",
        }

    redirect = urlsplit(auth_request.redirect_uri)
    client = auth_request.client
    return 200, {
        "success": True,
        "request": {
            "client_name": client.client_name,
            "client_id": client.client_id,
            "client_registered_at": client.created_at.isoformat(),
            "is_dynamically_registered": client.is_dynamically_registered,
            "redirect_host": redirect.netloc,
            "redirect_is_loopback": (redirect.hostname or "") in services.LOOPBACK_HOSTS,
            "resource_name": auth_request.resource_server.name,
            "resource": auth_request.resource_server.resource,
            "scopes": auth_request.scope.split(),
            "expires_at": auth_request.expires_at.isoformat(),
        },
    }


@oauth_router.post("/requests/{request_id}/decision", response={200: dict, 400: dict, 404: dict})
def decide_authorization_request(
    request: HttpRequest,
    request_id: str,
    data: AuthorizationDecisionRequest,
) -> tuple[int, dict[str, Any]]:
    """Approve or deny a pending request and return where to send the browser."""
    auth_request = services.get_pending_request(request_id)
    if auth_request is None:
        return 404, {
            "success": False,
            "message": "This authorisation request has expired or was already used.",
        }

    try:
        redirect_to = services.decide_authorization_request(
            auth_request, request.user, data.approve
        )
    except OAuthError as exc:
        return 400, {"success": False, "message": exc.description}

    logger.info(
        "OAuth request for client %s %s by %s",
        auth_request.client.client_id,
        "approved" if data.approve else "denied",
        request.user.pk,
    )
    return 200, {"success": True, "redirect_to": redirect_to}


@oauth_router.get("/grants", response={200: dict})
def list_grants(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List the current user's active connected applications."""
    grants = (
        OAuthGrant.objects.select_related("client", "resource_server")
        .filter(user=cast(User, request.user), revoked_at__isnull=True)
        .order_by("-last_used_at", "-created_at")
    )
    return 200, {
        "success": True,
        "grants": [
            {
                "id": str(grant.id),
                "client_name": grant.client.client_name,
                "resource_name": grant.resource_server.name,
                "scopes": grant.scope.split(),
                "created_at": grant.created_at.isoformat(),
                "last_used_at": grant.last_used_at.isoformat() if grant.last_used_at else None,
                "expires_at": grant.expires_at.isoformat(),
            }
            for grant in grants
            if grant.is_usable
        ],
    }


@oauth_router.post("/grants/{grant_id}/revoke", response={200: dict, 404: dict})
def revoke_grant(request: HttpRequest, grant_id: uuid.UUID) -> tuple[int, dict[str, Any]]:
    """Revoke a connected application and every token issued to it."""
    grant = OAuthGrant.objects.filter(
        id=grant_id, user=cast(User, request.user), revoked_at__isnull=True
    ).first()
    if grant is None:
        return 404, {"success": False, "message": "Connected application not found."}
    services.revoke_grant(grant)
    logger.info("OAuth grant %s revoked by %s", grant.id, request.user.pk)
    return 200, {"success": True, "message": "Access revoked."}

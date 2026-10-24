"""Models for the OAuth 2.1 authorisation server.

Every secret (client secrets, introspection secrets, authorisation codes,
access and refresh tokens) is stored only as a SHA-256 digest. The values are
high-entropy random strings, so a fast digest is sufficient and allows indexed
lookup.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def default_resource_scopes() -> list[str]:
    return ["mcp"]


class OAuthResourceServer(models.Model):
    """A protected service, such as an MCP server, that accepts our tokens.

    The ``resource`` URI is the RFC 8707 resource indicator clients request
    tokens for. Resource servers authenticate to the introspection endpoint
    with HTTP Basic credentials of ``<id>:<secret>``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    resource = models.URLField(
        max_length=500,
        unique=True,
        help_text="Canonical resource URI, for example https://brain.example.com/mcp",
    )
    scopes = models.JSONField(
        default=default_resource_scopes,
        help_text="Scopes this resource server accepts. A request without a scope is granted all of them.",
    )
    introspection_secret_hash = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "OAuth resource server"
        verbose_name_plural = "OAuth resource servers"

    def __str__(self) -> str:
        return f"{self.name} ({self.resource})"


class OAuthClient(models.Model):
    """An application that requests tokens on behalf of a user."""

    AUTH_METHOD_NONE = "none"
    AUTH_METHOD_SECRET_BASIC = "client_secret_basic"
    AUTH_METHOD_SECRET_POST = "client_secret_post"
    AUTH_METHOD_CHOICES = [
        (AUTH_METHOD_NONE, "Public client (PKCE only)"),
        (AUTH_METHOD_SECRET_BASIC, "Client secret (HTTP Basic)"),
        (AUTH_METHOD_SECRET_POST, "Client secret (form body)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.CharField(max_length=64, unique=True)
    client_name = models.CharField(max_length=150)
    redirect_uris = models.JSONField(default=list)
    token_endpoint_auth_method = models.CharField(
        max_length=32,
        choices=AUTH_METHOD_CHOICES,
        default=AUTH_METHOD_NONE,
    )
    client_secret_hash = models.CharField(max_length=64, blank=True, default="")
    is_dynamically_registered = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OAuth client"
        verbose_name_plural = "OAuth clients"

    def __str__(self) -> str:
        return f"{self.client_name} ({self.client_id})"

    @property
    def is_confidential(self) -> bool:
        return self.token_endpoint_auth_method != self.AUTH_METHOD_NONE


class OAuthAuthorizationRequest(models.Model):
    """A validated ``/oauth/authorize`` request awaiting the user's decision.

    The same row carries the authorisation code once the user approves, so a
    replayed code can be traced back to the grant it produced.
    """

    id = models.CharField(primary_key=True, max_length=64, editable=False)
    client = models.ForeignKey(
        OAuthClient, on_delete=models.CASCADE, related_name="authorization_requests"
    )
    resource_server = models.ForeignKey(
        OAuthResourceServer,
        on_delete=models.CASCADE,
        related_name="authorization_requests",
    )
    redirect_uri = models.URLField(max_length=2000)
    scope = models.CharField(max_length=500)
    state = models.TextField(blank=True, default="")
    code_challenge = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="oauth_authorization_requests",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    code_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    code_expires_at = models.DateTimeField(null=True, blank=True)
    code_used_at = models.DateTimeField(null=True, blank=True)
    grant = models.ForeignKey(
        "OAuthGrant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorization_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OAuth authorisation request"
        verbose_name_plural = "OAuth authorisation requests"
        indexes = [models.Index(fields=["expires_at"])]

    def __str__(self) -> str:
        return f"{self.client.client_name} request {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class OAuthGrant(models.Model):
    """A user's consent for one client to access one resource server.

    Access and refresh tokens belong to a grant. Revoking the grant revokes
    every token issued under it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="grants")
    resource_server = models.ForeignKey(
        OAuthResourceServer, on_delete=models.CASCADE, related_name="grants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_grants",
    )
    scope = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OAuth grant"
        verbose_name_plural = "OAuth grants"
        indexes = [models.Index(fields=["user", "revoked_at"])]

    def __str__(self) -> str:
        return f"{self.user} → {self.client.client_name}"

    @property
    def is_usable(self) -> bool:
        return self.revoked_at is None and timezone.now() < self.expires_at


class OAuthToken(models.Model):
    """An access or refresh token issued under a grant."""

    TYPE_ACCESS = "access"
    TYPE_REFRESH = "refresh"
    TYPE_CHOICES = [(TYPE_ACCESS, "Access token"), (TYPE_REFRESH, "Refresh token")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grant = models.ForeignKey(OAuthGrant, on_delete=models.CASCADE, related_name="tokens")
    token_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    rotated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When a refresh token was exchanged. Presenting it again revokes the grant.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OAuth token"
        verbose_name_plural = "OAuth tokens"
        indexes = [models.Index(fields=["expires_at"])]

    def __str__(self) -> str:
        return f"{self.get_token_type_display()} for {self.grant}"

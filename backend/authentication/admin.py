from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.http import HttpRequest
from unfold.admin import ModelAdmin

from authentication.models import CustomGroup, User
from authentication.oauth.models import OAuthClient, OAuthGrant, OAuthResourceServer, OAuthToken
from authentication.passkeys.models import Passkey, PasskeyAuthenticationLog, PasskeyChallenge
from authentication.twofactor.models import RecoveryCode, TwoFactorChallenge, TwoFactorMethod


class GroupAdmin(BaseGroupAdmin, ModelAdmin[CustomGroup]):
    pass


class UserAdmin(ModelAdmin[User]):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "email_verified",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "email_verified",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_editable = (
        "is_active",
        "is_staff",
        "email_verified",
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined", "email")


class PasskeyAdmin(ModelAdmin[Passkey]):
    """Admin interface for Passkey model."""

    list_display = (
        "id",
        "user",
        "name",
        "device_type",
        "backed_up",
        "created_at",
        "last_used_at",
    )
    list_filter = ("device_type", "backed_up", "created_at", "last_used_at")
    search_fields = ("user__email", "name", "credential_id")
    readonly_fields = (
        "id",
        "credential_id",
        "public_key",
        "sign_count",
        "transports",
        "created_at",
        "last_used_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


class PasskeyChallengeAdmin(ModelAdmin[PasskeyChallenge]):
    """Admin interface for PasskeyChallenge model."""

    list_display = (
        "id",
        "user",
        "email",
        "challenge_type",
        "created_at",
    )
    list_filter = ("challenge_type", "created_at")
    search_fields = ("user__email", "email")
    readonly_fields = ("id", "challenge", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


class PasskeyAuthenticationLogAdmin(ModelAdmin[PasskeyAuthenticationLog]):
    """Admin interface for PasskeyAuthenticationLog model."""

    list_display = (
        "id",
        "user",
        "email",
        "event_type",
        "passkey",
        "ip_address",
        "created_at",
    )
    list_filter = ("event_type", "created_at")
    search_fields = ("user__email", "email", "ip_address", "error_message")
    readonly_fields = (
        "id",
        "user",
        "email",
        "event_type",
        "passkey",
        "ip_address",
        "user_agent",
        "error_message",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Prevent manual creation of log entries."""
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Prevent editing of log entries."""
        return False


class TwoFactorMethodAdmin(ModelAdmin[TwoFactorMethod]):
    list_display = (
        "id",
        "user",
        "method_type",
        "name",
        "is_primary",
        "is_verified",
        "created_at",
        "last_used_at",
    )
    list_filter = ("method_type", "is_primary", "is_verified", "created_at")
    search_fields = ("user__email", "name")
    ordering = ("-created_at",)
    readonly_fields = ("secret", "created_at", "last_used_at")


class RecoveryCodeAdmin(ModelAdmin[RecoveryCode]):
    list_display = ("id", "user", "is_used", "created_at", "used_at")
    list_filter = ("is_used", "created_at", "used_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("code_hash", "created_at", "used_at")


class TwoFactorChallengeAdmin(ModelAdmin[TwoFactorChallenge]):
    list_display = ("id", "user", "password_verified", "created_at", "ip_address")
    list_filter = ("password_verified", "created_at")
    search_fields = ("user__email", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("challenge_token", "created_at", "ip_address", "user_agent")


class OAuthResourceServerAdmin(ModelAdmin[OAuthResourceServer]):
    """Resource servers are created with ``create_oauth_resource_server``."""

    list_display = ("name", "resource", "scopes", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "resource")
    readonly_fields = ("id", "introspection_secret_hash", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class OAuthClientAdmin(ModelAdmin[OAuthClient]):
    list_display = (
        "client_name",
        "client_id",
        "token_endpoint_auth_method",
        "is_dynamically_registered",
        "is_active",
        "created_at",
        "last_used_at",
    )
    list_filter = ("is_active", "is_dynamically_registered", "token_endpoint_auth_method")
    search_fields = ("client_name", "client_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "client_id",
        "client_secret_hash",
        "is_dynamically_registered",
        "created_at",
        "last_used_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class OAuthGrantAdmin(ModelAdmin[OAuthGrant]):
    list_display = (
        "user",
        "client",
        "resource_server",
        "scope",
        "created_at",
        "last_used_at",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("resource_server", "created_at", "revoked_at")
    search_fields = ("user__email", "client__client_name", "client__client_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "client",
        "resource_server",
        "user",
        "scope",
        "created_at",
        "expires_at",
        "last_used_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class OAuthTokenAdmin(ModelAdmin[OAuthToken]):
    list_display = (
        "id",
        "grant",
        "token_type",
        "created_at",
        "expires_at",
        "revoked_at",
        "rotated_at",
    )
    list_filter = ("token_type", "created_at", "revoked_at")
    search_fields = ("grant__user__email", "grant__client__client_name")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "grant",
        "token_type",
        "token_hash",
        "created_at",
        "expires_at",
        "rotated_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


admin.site.unregister(Group)
admin.site.register(User, UserAdmin)
admin.site.register(CustomGroup, GroupAdmin)
admin.site.register(Passkey, PasskeyAdmin)
admin.site.register(PasskeyChallenge, PasskeyChallengeAdmin)
admin.site.register(PasskeyAuthenticationLog, PasskeyAuthenticationLogAdmin)
admin.site.register(TwoFactorMethod, TwoFactorMethodAdmin)
admin.site.register(RecoveryCode, RecoveryCodeAdmin)
admin.site.register(TwoFactorChallenge, TwoFactorChallengeAdmin)
admin.site.register(OAuthResourceServer, OAuthResourceServerAdmin)
admin.site.register(OAuthClient, OAuthClientAdmin)
admin.site.register(OAuthGrant, OAuthGrantAdmin)
admin.site.register(OAuthToken, OAuthTokenAdmin)

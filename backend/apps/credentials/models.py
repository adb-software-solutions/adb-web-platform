from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.core.ownership import OwnershipType, ownership_constraint, validate_ownership


class CredentialType(models.Model):
    """Typed credential template describing metadata and encrypted secret fields."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    field_schema = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            base = (slugify(self.name) or "credential-type")[:100]
            candidate = base
            suffix = 2
            queryset = type(self).objects.all()
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            while queryset.filter(slug=candidate).exists():
                suffix_text = f"-{suffix}"
                candidate = f"{base[: 100 - len(suffix_text)]}{suffix_text}"
                suffix += 1
            self.slug = candidate

            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(dict.fromkeys([*update_fields, "slug"]))

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class StoredCredential(models.Model):
    """Client-owned or internal credential metadata and encrypted secret storage.

    Production secrets belong in ``encrypted_secret_payload`` and must be written
    through the credential-secret service. The individual secret columns and
    ``notes`` remain plaintext legacy fields for compatibility only and must not
    receive new production credential data.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    ownership_type = models.CharField(
        max_length=20,
        choices=OwnershipType.choices,
        default=OwnershipType.INTERNAL,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="credentials",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    credential_type = models.ForeignKey(
        CredentialType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credentials",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    description = models.TextField(blank=True)

    username = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Plaintext compatibility fields. New production writes must never use these.
    password = models.CharField(max_length=500, blank=True)
    api_key = models.CharField(max_length=500, blank=True)
    secret_key = models.CharField(max_length=500, blank=True)
    private_key = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    encrypted_secret_payload = models.TextField(blank=True, editable=False)
    secret_payload_version = models.PositiveSmallIntegerField(default=1, editable=False)
    secret_field_keys = models.JSONField(default=list, blank=True, editable=False)

    expires_at = models.DateTimeField(blank=True, null=True)
    last_rotated_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="credentials_created",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="credentials_updated",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [ownership_constraint("storedcredential_valid_ownership")]
        permissions = [
            ("reveal_storedcredential", "Can reveal stored credential secrets"),
            ("copy_storedcredential_secret", "Can copy stored credential secrets"),
            ("download_storedcredential_secret", "Can download stored credential secrets"),
        ]
        indexes = [
            models.Index(
                fields=["ownership_type", "client", "status"],
                name="credential_owner_status_idx",
            )
        ]

    def clean(self) -> None:
        super().clean()
        validate_ownership(self)

    def __str__(self) -> str:
        return self.name


class CredentialResourceLink(models.Model):
    """Attach one credential to one or more structured infrastructure resources."""

    credential = models.ForeignKey(
        StoredCredential,
        on_delete=models.CASCADE,
        related_name="resource_links",
    )
    resource = models.ForeignKey(
        "infrastructure.InfrastructureResource",
        on_delete=models.CASCADE,
        related_name="credential_links",
    )
    purpose = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="credential_resource_links_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["credential__name", "resource__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["credential", "resource"],
                name="unique_credential_resource_link",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if not self.credential_id or not self.resource_id:
            return
        if self.credential.ownership_type != OwnershipType.CLIENT:
            return
        if (
            self.resource.ownership_type != OwnershipType.CLIENT
            or self.resource.client_id != self.credential.client_id
        ):
            raise ValidationError(
                "Client-owned credentials may only link to resources owned by the same client."
            )

    def __str__(self) -> str:
        return f"{self.credential} → {self.resource}"


def credential_field_schema(credential_type: CredentialType | None) -> list[dict[str, Any]]:
    """Return a defensive normalised field schema for UI/API validation."""
    if credential_type is None or not isinstance(credential_type.field_schema, list):
        return []
    return [field for field in credential_type.field_schema if isinstance(field, dict)]

from __future__ import annotations

from datetime import datetime
from typing import Literal

from ninja import Schema
from pydantic import Field, model_validator

CredentialOwnershipFilter = Literal["all", "internal", "client"]
CredentialStatusFilter = Literal["active", "inactive", "archived", "all"]
CredentialStatusValue = Literal["active", "inactive", "archived"]
CredentialOwnershipValue = Literal["internal", "client"]
CredentialFieldKind = Literal["text", "password", "textarea", "url"]
CredentialFieldStorage = Literal["username", "url", "metadata", "secret"]

LEGACY_SECRET_FIELD_LABELS = {
    "password": "Password",
    "api_key": "API key",
    "secret_key": "Secret key",
    "private_key": "Private key",
    "notes": "Notes",
}
LEGACY_MULTILINE_SECRET_FIELDS = {"private_key", "notes"}


class CredentialFieldOut(Schema):
    key: str
    label: str
    kind: CredentialFieldKind
    storage: CredentialFieldStorage
    required: bool


class CredentialTypeOut(Schema):
    id: int
    slug: str
    name: str
    icon: str
    description: str
    fields: list[CredentialFieldOut]


class CredentialResourceLinkIn(Schema):
    resource_id: int
    purpose: str = ""
    is_primary: bool = False


class CredentialResourceLinkOut(Schema):
    id: int
    resource_id: int
    resource_name: str
    resource_type: str
    ownership_type: str
    client_name: str | None
    purpose: str
    is_primary: bool


class CredentialCreateIn(Schema):
    name: str
    credential_type_id: int
    ownership_type: CredentialOwnershipValue = "internal"
    client_id: int | None = None
    status: CredentialStatusValue = "active"
    description: str = ""
    expires_at: datetime | None = None
    values: dict[str, str] = Field(default_factory=dict)
    resource_links: list[CredentialResourceLinkIn] = Field(default_factory=list)


class CredentialUpdateIn(Schema):
    name: str | None = None
    status: CredentialStatusValue | None = None
    description: str | None = None
    expires_at: datetime | None = None
    clear_expires_at: bool = False
    values: dict[str, str] = Field(default_factory=dict)
    clear_secret_fields: list[str] = Field(default_factory=list)
    resource_links: list[CredentialResourceLinkIn] | None = None


class CredentialSummaryOut(Schema):
    id: int
    name: str
    status: str
    ownership_type: str
    client_id: int | None
    client_name: str | None
    credential_type_id: int | None
    credential_type_slug: str | None
    credential_type_name: str | None
    username: str
    url: str
    expires_at: datetime | None
    last_rotated_at: datetime | None
    secret_field_keys: list[str]
    resource_count: int
    has_legacy_plaintext: bool
    updated_at: datetime


class CredentialPageOut(Schema):
    items: list[CredentialSummaryOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class CredentialDetailOut(CredentialSummaryOut):
    description: str
    metadata: dict[str, str]
    fields: list[CredentialFieldOut]
    resource_links: list[CredentialResourceLinkOut]
    created_by: str | None
    updated_by: str | None
    created_at: datetime

    @model_validator(mode="after")
    def include_untyped_encrypted_fields(self) -> CredentialDetailOut:
        """Keep migrated legacy secrets visible even without template metadata."""
        known_keys = {field.key for field in self.fields}
        for raw_key in self.secret_field_keys:
            key = raw_key.strip()
            if not key or key in known_keys:
                continue
            self.fields.append(
                CredentialFieldOut(
                    key=key,
                    label=LEGACY_SECRET_FIELD_LABELS.get(
                        key,
                        key.replace("_", " ").title(),
                    ),
                    kind="textarea" if key in LEGACY_MULTILINE_SECRET_FIELDS else "password",
                    storage="secret",
                    required=False,
                )
            )
            known_keys.add(key)
        return self


class CredentialClientOptionOut(Schema):
    id: int
    name: str


class CredentialResourceOptionOut(Schema):
    id: int
    name: str
    resource_type: str
    ownership_type: str
    client_id: int | None
    client_name: str | None


class CredentialOptionsOut(Schema):
    types: list[CredentialTypeOut]
    clients: list[CredentialClientOptionOut]
    resources: list[CredentialResourceOptionOut]


class CredentialSecretRevealIn(Schema):
    fields: list[str] = Field(default_factory=list)


class CredentialSecretsOut(Schema):
    fields: dict[str, str]


class CredentialSecretValueOut(Schema):
    field_key: str
    value: str


class CredentialLegacyMigrationOut(Schema):
    migrated_fields: list[str]

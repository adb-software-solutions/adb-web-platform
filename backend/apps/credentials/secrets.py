from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.credentials.models import StoredCredential

SECRET_PAYLOAD_VERSION = 1
LEGACY_PLAINTEXT_FIELDS = ("password", "api_key", "secret_key", "private_key", "notes")


class CredentialEncryptionError(RuntimeError):
    """Base exception for encrypted credential-secret operations."""


class CredentialEncryptionNotConfiguredError(CredentialEncryptionError):
    """No valid credential encryption key is configured."""


class CredentialDecryptionError(CredentialEncryptionError):
    """A stored encrypted credential payload cannot be decrypted safely."""


class CredentialSecretFieldError(CredentialEncryptionError):
    """A requested encrypted secret field does not exist."""


def store_credential_secrets(
    credential: StoredCredential,
    secrets: Mapping[str, str],
    *,
    mark_rotated: bool = True,
) -> None:
    """Encrypt and persist secret material without touching legacy plaintext fields."""
    payload = _normalise_secrets(secrets)
    if not payload:
        raise CredentialEncryptionError("At least one non-empty credential secret is required.")

    encoded = json.dumps(
        {"version": SECRET_PAYLOAD_VERSION, "secrets": payload},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    credential.encrypted_secret_payload = _fernet().encrypt(encoded).decode("ascii")
    credential.secret_payload_version = SECRET_PAYLOAD_VERSION
    credential.secret_field_keys = sorted(payload)

    update_fields = [
        "encrypted_secret_payload",
        "secret_payload_version",
        "secret_field_keys",
        "updated_at",
    ]
    if mark_rotated:
        credential.last_rotated_at = timezone.now()
        update_fields.append("last_rotated_at")
    credential.save(update_fields=update_fields)


def merge_credential_secrets(
    credential: StoredCredential,
    updates: Mapping[str, str],
    *,
    clear_fields: Iterable[str] = (),
) -> None:
    """Merge secret edits without requiring unchanged values to leave the server."""
    existing = _decrypt_payload(credential) if credential.encrypted_secret_payload else {}
    for field in clear_fields:
        existing.pop(field.strip(), None)
    existing.update(_normalise_secrets(updates))
    if not existing:
        clear_credential_secrets(credential)
        return
    store_credential_secrets(credential, existing, mark_rotated=True)


def load_credential_secrets_for_service(credential: StoredCredential) -> dict[str, str]:
    """Decrypt secret material for trusted backend integrations such as Graph."""
    return _decrypt_payload(credential)


def reveal_credential_secrets(
    credential: StoredCredential,
    *,
    actor: Any,
    fields: Iterable[str] | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
) -> dict[str, str]:
    """Reveal secret material to an authorised human and always audit the event."""
    if not getattr(actor, "is_authenticated", False) or not actor.has_perm(
        "credentials.reveal_storedcredential"
    ):
        raise PermissionDenied("You do not have permission to reveal credential secrets.")

    secrets = _select_fields(_decrypt_payload(credential), fields)
    AuditEvent.record(
        action="credentials.secret_revealed",
        actor=actor,
        target=credential,
        metadata={"secret_fields": sorted(secrets)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return secrets


def copy_credential_secret(
    credential: StoredCredential,
    field_key: str,
    *,
    actor: Any,
    ip_address: str | None = None,
    user_agent: str = "",
) -> str:
    """Return one secret for clipboard use and audit the copy operation."""
    return _single_secret_action(
        credential,
        field_key,
        actor=actor,
        permission="credentials.copy_storedcredential_secret",
        action="credentials.secret_copied",
        denied_message="You do not have permission to copy credential secrets.",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def download_credential_secret(
    credential: StoredCredential,
    field_key: str,
    *,
    actor: Any,
    ip_address: str | None = None,
    user_agent: str = "",
) -> str:
    """Return one secret for an explicit file download and audit the operation."""
    return _single_secret_action(
        credential,
        field_key,
        actor=actor,
        permission="credentials.download_storedcredential_secret",
        action="credentials.secret_downloaded",
        denied_message="You do not have permission to download credential secrets.",
        ip_address=ip_address,
        user_agent=user_agent,
    )


def rotate_credential_encryption(credential: StoredCredential) -> None:
    """Re-encrypt an existing payload with the current primary encryption key."""
    secrets = _decrypt_payload(credential)
    store_credential_secrets(credential, secrets, mark_rotated=True)


def clear_credential_secrets(credential: StoredCredential) -> None:
    """Remove only the encrypted secret payload, leaving credential metadata intact."""
    credential.encrypted_secret_payload = ""
    credential.secret_payload_version = SECRET_PAYLOAD_VERSION
    credential.secret_field_keys = []
    credential.last_rotated_at = timezone.now()
    credential.save(
        update_fields=[
            "encrypted_secret_payload",
            "secret_payload_version",
            "secret_field_keys",
            "last_rotated_at",
            "updated_at",
        ]
    )


@transaction.atomic
def migrate_legacy_plaintext_secrets(
    credential: StoredCredential,
    *,
    actor: Any,
    ip_address: str | None = None,
    user_agent: str = "",
) -> list[str]:
    """Encrypt legacy plaintext secret columns and blank them in one transaction."""
    if not getattr(actor, "is_authenticated", False) or not actor.has_perm(
        "credentials.change_storedcredential"
    ):
        raise PermissionDenied("You do not have permission to migrate credential secrets.")

    credential = StoredCredential.objects.select_for_update().get(pk=credential.pk)
    legacy = {
        field: str(getattr(credential, field))
        for field in LEGACY_PLAINTEXT_FIELDS
        if getattr(credential, field)
    }
    if not legacy:
        return []

    merge_credential_secrets(credential, legacy)
    for field in legacy:
        setattr(credential, field, "")
    credential.updated_by = actor
    credential.save(update_fields=[*legacy.keys(), "updated_by", "updated_at"])
    AuditEvent.record(
        action="credentials.legacy_secrets_encrypted",
        actor=actor,
        target=credential,
        metadata={"secret_fields": sorted(legacy)},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return sorted(legacy)


def _single_secret_action(
    credential: StoredCredential,
    field_key: str,
    *,
    actor: Any,
    permission: str,
    action: str,
    denied_message: str,
    ip_address: str | None,
    user_agent: str,
) -> str:
    if not getattr(actor, "is_authenticated", False) or not actor.has_perm(permission):
        raise PermissionDenied(denied_message)

    key = field_key.strip()
    secrets = _decrypt_payload(credential)
    try:
        value = secrets[key]
    except KeyError as exc:
        raise CredentialSecretFieldError("Credential secret field was not found.") from exc

    AuditEvent.record(
        action=action,
        actor=actor,
        target=credential,
        metadata={"secret_fields": [key]},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return value


def _select_fields(
    secrets: dict[str, str],
    fields: Iterable[str] | None,
) -> dict[str, str]:
    if fields is None:
        return secrets
    requested = {field.strip() for field in fields if field.strip()}
    missing = requested.difference(secrets)
    if missing:
        raise CredentialSecretFieldError(f"Credential secret field was not found: {min(missing)}")
    return {key: value for key, value in secrets.items() if key in requested}


def _decrypt_payload(credential: StoredCredential) -> dict[str, str]:
    if not credential.encrypted_secret_payload:
        raise CredentialDecryptionError("Credential has no encrypted secret payload.")
    try:
        plaintext = _fernet().decrypt(credential.encrypted_secret_payload.encode("ascii"))
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise CredentialDecryptionError(
            "Credential secret payload could not be decrypted."
        ) from exc

    try:
        decoded = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CredentialDecryptionError("Credential secret payload is invalid.") from exc

    if not isinstance(decoded, dict) or decoded.get("version") != SECRET_PAYLOAD_VERSION:
        raise CredentialDecryptionError("Credential secret payload version is unsupported.")
    secrets = decoded.get("secrets")
    if not isinstance(secrets, dict):
        raise CredentialDecryptionError("Credential secret payload has no secrets object.")

    result = {
        key: value
        for key, value in secrets.items()
        if isinstance(key, str) and isinstance(value, str) and value
    }
    if not result:
        raise CredentialDecryptionError("Credential secret payload is empty.")
    return result


def _normalise_secrets(secrets: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in secrets.items():
        normalised_key = key.strip()
        if normalised_key and value:
            result[normalised_key] = value
    return result


def _configured_keys() -> list[str]:
    configured = getattr(settings, "CREDENTIAL_ENCRYPTION_KEYS", None)
    if configured is None:
        configured = os.environ.get("CREDENTIAL_ENCRYPTION_KEYS", "")
    if isinstance(configured, str):
        return [item.strip() for item in configured.split(",") if item.strip()]
    return [str(item).strip() for item in configured if str(item).strip()]


def _fernet() -> MultiFernet:
    configured_keys = _configured_keys()
    if not configured_keys:
        raise CredentialEncryptionNotConfiguredError(
            "CREDENTIAL_ENCRYPTION_KEYS must contain at least one Fernet key."
        )

    try:
        fernets = [Fernet(key.encode("ascii")) for key in configured_keys]
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialEncryptionNotConfiguredError(
            "CREDENTIAL_ENCRYPTION_KEYS contains an invalid Fernet key."
        ) from exc
    return MultiFernet(fernets)

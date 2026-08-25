from __future__ import annotations

from typing import TypedDict


class CredentialFieldDefinition(TypedDict):
    key: str
    label: str
    kind: str
    storage: str
    required: bool


class CredentialTemplateDefinition(TypedDict):
    slug: str
    name: str
    icon: str
    description: str
    sort_order: int
    fields: list[CredentialFieldDefinition]


def _field(
    key: str,
    label: str,
    *,
    kind: str = "text",
    storage: str = "secret",
    required: bool = False,
) -> CredentialFieldDefinition:
    return {
        "key": key,
        "label": label,
        "kind": kind,
        "storage": storage,
        "required": required,
    }


BUILTIN_CREDENTIAL_TEMPLATES: tuple[CredentialTemplateDefinition, ...] = (
    {
        "slug": "username-password",
        "name": "Username and password",
        "icon": "key-round",
        "description": (
            "General username/password login for websites, servers and vendor portals."
        ),
        "sort_order": 10,
        "fields": [
            _field("username", "Username", storage="username"),
            _field("password", "Password", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "ssh-key",
        "name": "SSH key",
        "icon": "terminal-square",
        "description": (
            "SSH login using encrypted public/private key material and optional passphrase."
        ),
        "sort_order": 20,
        "fields": [
            _field("username", "SSH username", storage="username"),
            _field("public_key", "Public key", kind="textarea"),
            _field("private_key", "Private key", kind="textarea", required=True),
            _field("passphrase", "Key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "database-login",
        "name": "Database login",
        "icon": "database",
        "description": ("Database username/password with optional logical database identifier."),
        "sort_order": 30,
        "fields": [
            _field(
                "username",
                "Database username",
                storage="username",
                required=True,
            ),
            _field("password", "Database password", kind="password", required=True),
            _field("database_name", "Database name", storage="metadata"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "api-key",
        "name": "API key or token",
        "icon": "braces",
        "description": "API token/key pair for integrations and service access.",
        "sort_order": 40,
        "fields": [
            _field("api_key", "API key / token", kind="password", required=True),
            _field("api_secret", "API secret", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "oauth-application",
        "name": "OAuth application",
        "icon": "shield-keyhole",
        "description": (
            "OAuth/client-credential application with optional certificate authentication."
        ),
        "sort_order": 50,
        "fields": [
            _field("client_id", "Client ID", storage="metadata", required=True),
            _field("tenant_id", "Tenant ID", storage="metadata"),
            _field("client_secret", "Client secret", kind="password"),
            _field("certificate", "Certificate", kind="textarea"),
            _field("private_key", "Private key", kind="textarea"),
            _field("passphrase", "Private-key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "service-account",
        "name": "Service account",
        "icon": "bot",
        "description": ("Service-account credential, including encrypted JSON/key material."),
        "sort_order": 60,
        "fields": [
            _field("account_identifier", "Account identifier", storage="metadata"),
            _field(
                "service_account_json",
                "Service-account JSON / key",
                kind="textarea",
                required=True,
            ),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "certificate-keypair",
        "name": "Certificate and private key",
        "icon": "badge-check",
        "description": ("Certificate/keypair stored together with optional encrypted passphrase."),
        "sort_order": 70,
        "fields": [
            _field("certificate", "Certificate", kind="textarea", required=True),
            _field("private_key", "Private key", kind="textarea", required=True),
            _field("passphrase", "Private-key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "licence-key",
        "name": "Licence key",
        "icon": "ticket-check",
        "description": "Encrypted software or service licence/activation key.",
        "sort_order": 80,
        "fields": [
            _field("licence_key", "Licence key", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "recovery-codes",
        "name": "Recovery codes",
        "icon": "list-key",
        "description": "Encrypted MFA/account recovery codes.",
        "sort_order": 90,
        "fields": [
            _field("recovery_codes", "Recovery codes", kind="textarea", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "encryption-key",
        "name": "Encryption key",
        "icon": "key-square",
        "description": "Application, backup or other encryption key material.",
        "sort_order": 100,
        "fields": [
            _field("encryption_key", "Encryption key", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
    {
        "slug": "custom-secret",
        "name": "Custom secret",
        "icon": "lock-keyhole",
        "description": (
            "General encrypted secret for credentials that do not fit another template."
        ),
        "sort_order": 110,
        "fields": [
            _field("username", "Username / identifier", storage="username"),
            _field("url", "URL", kind="url", storage="url"),
            _field("secret_value", "Secret value", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    },
)

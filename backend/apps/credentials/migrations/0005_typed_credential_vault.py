# Generated manually for the typed credential vault foundation.

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


BUILTIN_TYPES = (
    (
        "username-password",
        "Username and password",
        "key-round",
        "General username/password login for websites, servers and vendor portals.",
        10,
        [
            {"key": "username", "label": "Username", "kind": "text", "storage": "username", "required": False},
            {"key": "password", "label": "Password", "kind": "password", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "ssh-key",
        "SSH key",
        "terminal-square",
        "SSH login using encrypted public/private key material and optional passphrase.",
        20,
        [
            {"key": "username", "label": "SSH username", "kind": "text", "storage": "username", "required": False},
            {"key": "public_key", "label": "Public key", "kind": "textarea", "storage": "secret", "required": False},
            {"key": "private_key", "label": "Private key", "kind": "textarea", "storage": "secret", "required": True},
            {"key": "passphrase", "label": "Key passphrase", "kind": "password", "storage": "secret", "required": False},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "database-login",
        "Database login",
        "database",
        "Database username/password with optional logical database identifier.",
        30,
        [
            {"key": "username", "label": "Database username", "kind": "text", "storage": "username", "required": True},
            {"key": "password", "label": "Database password", "kind": "password", "storage": "secret", "required": True},
            {"key": "database_name", "label": "Database name", "kind": "text", "storage": "metadata", "required": False},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "api-key",
        "API key or token",
        "braces",
        "API token/key pair for integrations and service access.",
        40,
        [
            {"key": "api_key", "label": "API key / token", "kind": "password", "storage": "secret", "required": True},
            {"key": "api_secret", "label": "API secret", "kind": "password", "storage": "secret", "required": False},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "oauth-application",
        "OAuth application",
        "shield-keyhole",
        "OAuth/client-credential application with optional certificate authentication.",
        50,
        [
            {"key": "client_id", "label": "Client ID", "kind": "text", "storage": "metadata", "required": True},
            {"key": "tenant_id", "label": "Tenant ID", "kind": "text", "storage": "metadata", "required": False},
            {"key": "client_secret", "label": "Client secret", "kind": "password", "storage": "secret", "required": False},
            {"key": "certificate", "label": "Certificate", "kind": "textarea", "storage": "secret", "required": False},
            {"key": "private_key", "label": "Private key", "kind": "textarea", "storage": "secret", "required": False},
            {"key": "passphrase", "label": "Private-key passphrase", "kind": "password", "storage": "secret", "required": False},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "service-account",
        "Service account",
        "bot",
        "Service-account credential, including encrypted JSON/key material.",
        60,
        [
            {"key": "account_identifier", "label": "Account identifier", "kind": "text", "storage": "metadata", "required": False},
            {"key": "service_account_json", "label": "Service-account JSON / key", "kind": "textarea", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "certificate-keypair",
        "Certificate and private key",
        "badge-check",
        "Certificate/keypair stored together with optional encrypted passphrase.",
        70,
        [
            {"key": "certificate", "label": "Certificate", "kind": "textarea", "storage": "secret", "required": True},
            {"key": "private_key", "label": "Private key", "kind": "textarea", "storage": "secret", "required": True},
            {"key": "passphrase", "label": "Private-key passphrase", "kind": "password", "storage": "secret", "required": False},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "licence-key",
        "Licence key",
        "ticket-check",
        "Encrypted software or service licence/activation key.",
        80,
        [
            {"key": "licence_key", "label": "Licence key", "kind": "password", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "recovery-codes",
        "Recovery codes",
        "list-key",
        "Encrypted MFA/account recovery codes.",
        90,
        [
            {"key": "recovery_codes", "label": "Recovery codes", "kind": "textarea", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "encryption-key",
        "Encryption key",
        "key-square",
        "Application, backup or other encryption key material.",
        100,
        [
            {"key": "encryption_key", "label": "Encryption key", "kind": "password", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
    (
        "custom-secret",
        "Custom secret",
        "lock-keyhole",
        "General encrypted secret for credentials that do not fit another template.",
        110,
        [
            {"key": "username", "label": "Username / identifier", "kind": "text", "storage": "username", "required": False},
            {"key": "url", "label": "URL", "kind": "url", "storage": "url", "required": False},
            {"key": "secret_value", "label": "Secret value", "kind": "password", "storage": "secret", "required": True},
            {"key": "notes", "label": "Encrypted notes", "kind": "textarea", "storage": "secret", "required": False},
        ],
    ),
)


def seed_credential_types(apps, schema_editor) -> None:
    CredentialType = apps.get_model("credentials", "CredentialType")

    for credential_type in CredentialType.objects.order_by("id"):
        base = slugify(credential_type.name) or f"credential-type-{credential_type.id}"
        candidate = base[:100]
        suffix = 2
        while CredentialType.objects.filter(slug=candidate).exclude(pk=credential_type.pk).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base[: 100 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        credential_type.slug = candidate
        credential_type.save(update_fields=["slug"])

    for slug, name, icon, description, sort_order, fields in BUILTIN_TYPES:
        existing = CredentialType.objects.filter(slug=slug).first()
        if existing is None:
            existing = CredentialType.objects.filter(name=name).first()
        if existing is None:
            CredentialType.objects.create(
                slug=slug,
                name=name,
                icon=icon,
                description=description,
                sort_order=sort_order,
                field_schema=fields,
                is_system=True,
                is_active=True,
            )
            continue
        existing.slug = slug
        existing.icon = icon
        existing.description = description
        existing.sort_order = sort_order
        existing.field_schema = fields
        existing.is_system = True
        existing.is_active = True
        existing.save(
            update_fields=[
                "slug",
                "icon",
                "description",
                "sort_order",
                "field_schema",
                "is_system",
                "is_active",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("credentials", "0004_encrypted_secret_payload"),
        ("infrastructure", "0003_legacy_resource_identities"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="credentialtype",
            name="slug",
            field=models.SlugField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="credentialtype",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="credentialtype",
            name="field_schema",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="credentialtype",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="credentialtype",
            name="is_system",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="credentialtype",
            name="sort_order",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(seed_credential_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="credentialtype",
            name="slug",
            field=models.SlugField(max_length=100, unique=True),
        ),
        migrations.AlterModelOptions(
            name="credentialtype",
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("inactive", "Inactive"), ("archived", "Archived")],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="secret_field_keys",
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="credentials_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="storedcredential",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="credentials_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name="storedcredential",
            options={
                "ordering": ["name", "id"],
                "permissions": [
                    ("reveal_storedcredential", "Can reveal stored credential secrets"),
                    ("copy_storedcredential_secret", "Can copy stored credential secrets"),
                    ("download_storedcredential_secret", "Can download stored credential secrets"),
                ],
            },
        ),
        migrations.AddIndex(
            model_name="storedcredential",
            index=models.Index(
                fields=["ownership_type", "client", "status"],
                name="credential_owner_status_idx",
            ),
        ),
        migrations.CreateModel(
            name="CredentialResourceLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("purpose", models.CharField(blank=True, max_length=200)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="credential_resource_links_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resource_links",
                        to="credentials.storedcredential",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credential_links",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["credential__name", "resource__name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="credentialresourcelink",
            constraint=models.UniqueConstraint(
                fields=("credential", "resource"),
                name="unique_credential_resource_link",
            ),
        ),
    ]

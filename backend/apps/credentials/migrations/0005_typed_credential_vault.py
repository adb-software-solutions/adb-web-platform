# Generated manually for the typed credential vault foundation.

from __future__ import annotations

import django.db.models.deletion
from django.apps.registry import Apps
from django.conf import settings
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.utils.text import slugify


def _field(
    key: str,
    label: str,
    *,
    kind: str = "text",
    storage: str = "secret",
    required: bool = False,
) -> dict[str, object]:
    return {
        "key": key,
        "label": label,
        "kind": kind,
        "storage": storage,
        "required": required,
    }


BUILTIN_TYPES = (
    (
        "username-password",
        "Username and password",
        "key-round",
        "General username/password login for websites, servers and vendor portals.",
        10,
        [
            _field("username", "Username", storage="username"),
            _field("password", "Password", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "ssh-key",
        "SSH key",
        "terminal-square",
        "SSH login using encrypted public/private key material and optional passphrase.",
        20,
        [
            _field("username", "SSH username", storage="username"),
            _field("public_key", "Public key", kind="textarea"),
            _field("private_key", "Private key", kind="textarea", required=True),
            _field("passphrase", "Key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "database-login",
        "Database login",
        "database",
        "Database username/password with optional logical database identifier.",
        30,
        [
            _field("username", "Database username", storage="username", required=True),
            _field("password", "Database password", kind="password", required=True),
            _field("database_name", "Database name", storage="metadata"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "api-key",
        "API key or token",
        "braces",
        "API token/key pair for integrations and service access.",
        40,
        [
            _field("api_key", "API key / token", kind="password", required=True),
            _field("api_secret", "API secret", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "oauth-application",
        "OAuth application",
        "shield-keyhole",
        "OAuth/client-credential application with optional certificate authentication.",
        50,
        [
            _field("client_id", "Client ID", storage="metadata", required=True),
            _field("tenant_id", "Tenant ID", storage="metadata"),
            _field("client_secret", "Client secret", kind="password"),
            _field("certificate", "Certificate", kind="textarea"),
            _field("private_key", "Private key", kind="textarea"),
            _field("passphrase", "Private-key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "service-account",
        "Service account",
        "bot",
        "Service-account credential, including encrypted JSON/key material.",
        60,
        [
            _field("account_identifier", "Account identifier", storage="metadata"),
            _field(
                "service_account_json",
                "Service-account JSON / key",
                kind="textarea",
                required=True,
            ),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "certificate-keypair",
        "Certificate and private key",
        "badge-check",
        "Certificate/keypair stored together with optional encrypted passphrase.",
        70,
        [
            _field("certificate", "Certificate", kind="textarea", required=True),
            _field("private_key", "Private key", kind="textarea", required=True),
            _field("passphrase", "Private-key passphrase", kind="password"),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "licence-key",
        "Licence key",
        "ticket-check",
        "Encrypted software or service licence/activation key.",
        80,
        [
            _field("licence_key", "Licence key", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "recovery-codes",
        "Recovery codes",
        "list-key",
        "Encrypted MFA/account recovery codes.",
        90,
        [
            _field("recovery_codes", "Recovery codes", kind="textarea", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "encryption-key",
        "Encryption key",
        "key-square",
        "Application, backup or other encryption key material.",
        100,
        [
            _field("encryption_key", "Encryption key", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
    (
        "custom-secret",
        "Custom secret",
        "lock-keyhole",
        "General encrypted secret for credentials that do not fit another template.",
        110,
        [
            _field("username", "Username / identifier", storage="username"),
            _field("url", "URL", kind="url", storage="url"),
            _field("secret_value", "Secret value", kind="password", required=True),
            _field("notes", "Encrypted notes", kind="textarea"),
        ],
    ),
)


def seed_credential_types(
    apps: Apps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor
    CredentialType = apps.get_model("credentials", "CredentialType")

    for credential_type in CredentialType.objects.order_by("id"):
        base = slugify(credential_type.name) or f"credential-type-{credential_type.id}"
        candidate = base[:100]
        suffix = 2
        while (
            CredentialType.objects.filter(slug=candidate)
            .exclude(pk=credential_type.pk)
            .exists()
        ):
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
            field=models.CharField(blank=True, max_length=100, null=True),
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
                choices=[
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("archived", "Archived"),
                ],
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
                    (
                        "copy_storedcredential_secret",
                        "Can copy stored credential secrets",
                    ),
                    (
                        "download_storedcredential_secret",
                        "Can download stored credential secrets",
                    ),
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
            options={
                "ordering": ["credential__name", "resource__name", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="credentialresourcelink",
            constraint=models.UniqueConstraint(
                fields=("credential", "resource"),
                name="unique_credential_resource_link",
            ),
        ),
    ]

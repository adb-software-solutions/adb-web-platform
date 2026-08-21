# Generated manually for explicit legacy infrastructure identity reconciliation.

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _identity_model(
    *,
    name: str,
    legacy_field: str,
    legacy_model: str,
    ordering: str,
) -> migrations.CreateModel:
    model_slug = name.lower()
    return migrations.CreateModel(
        name=name,
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
            ("linked_at", models.DateTimeField(auto_now_add=True)),
            (
                "linked_by",
                models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name=f"legacy_{model_slug}_linked",
                    to=settings.AUTH_USER_MODEL,
                ),
            ),
            (
                "resource",
                models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name=f"legacy_{model_slug}",
                    to="infrastructure.infrastructureresource",
                ),
            ),
            (
                legacy_field,
                models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="structured_resource_identity",
                    to=f"infrastructure.{legacy_model}",
                ),
            ),
        ],
        options={"ordering": [ordering]},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("infrastructure", "0002_structured_resource_foundation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="infrastructureresource",
            options={
                "ordering": ["name", "id"],
                "permissions": [
                    (
                        "reconcile_legacy_infrastructure",
                        "Can reconcile legacy infrastructure with structured resources",
                    )
                ],
            },
        ),
        _identity_model(
            name="ServerResourceIdentity",
            legacy_field="server",
            legacy_model="server",
            ordering="server__hostname",
        ),
        _identity_model(
            name="DatabaseResourceIdentity",
            legacy_field="database",
            legacy_model="database",
            ordering="database__name",
        ),
        _identity_model(
            name="WebsiteResourceIdentity",
            legacy_field="website",
            legacy_model="website",
            ordering="website__name",
        ),
        _identity_model(
            name="DomainResourceIdentity",
            legacy_field="domain",
            legacy_model="domain",
            ordering="domain__domain_name",
        ),
        _identity_model(
            name="SSLCertificateResourceIdentity",
            legacy_field="ssl_certificate",
            legacy_model="sslcertificate",
            ordering="ssl_certificate__domain__domain_name",
        ),
        _identity_model(
            name="LicenceResourceIdentity",
            legacy_field="licence",
            legacy_model="licence",
            ordering="licence__name",
        ),
        _identity_model(
            name="ApplicationResourceIdentity",
            legacy_field="application",
            legacy_model="application",
            ordering="application__name",
        ),
        _identity_model(
            name="MobileAppResourceIdentity",
            legacy_field="mobile_app",
            legacy_model="mobileapp",
            ordering="mobile_app__name",
        ),
        _identity_model(
            name="APIResourceIdentity",
            legacy_field="api",
            legacy_model="api",
            ordering="api__name",
        ),
        _identity_model(
            name="BotResourceIdentity",
            legacy_field="bot",
            legacy_model="bot",
            ordering="bot__name",
        ),
        _identity_model(
            name="EmailSystemResourceIdentity",
            legacy_field="email_system",
            legacy_model="emailsystem",
            ordering="email_system__provider",
        ),
    ]

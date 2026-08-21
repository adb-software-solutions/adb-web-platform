from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .legacy_models import (
    API,
    Application,
    Bot,
    Database,
    Domain,
    EmailSystem,
    Licence,
    MobileApp,
    Server,
    SSLCertificate,
    Website,
)
from .resource_models import InfrastructureResource


class LegacyResourceIdentityBase(models.Model):
    """Temporary explicit identity bridge for one legacy infrastructure record."""

    expected_resource_type: ClassVar[str] = ""

    resource = models.OneToOneField(
        InfrastructureResource,
        on_delete=models.PROTECT,
        related_name="legacy_%(class)s",
    )
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="legacy_%(class)s_linked",
        null=True,
        blank=True,
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()
        if (
            self.resource_id
            and self.expected_resource_type
            and self.resource.resource_type != self.expected_resource_type
        ):
            raise ValidationError(
                {
                    "resource": (
                        "This legacy record requires an InfrastructureResource "
                        f"with type '{self.expected_resource_type}'."
                    )
                }
            )


class ServerResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.SERVER

    server = models.OneToOneField(
        Server,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["server__hostname"]
        permissions = [
            (
                "reconcile_legacy_infrastructure",
                "Can reconcile legacy infrastructure with structured resources",
            )
        ]

    def __str__(self) -> str:
        return f"{self.server} -> {self.resource}"


class DatabaseResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.DATABASE_INSTANCE

    database = models.OneToOneField(
        Database,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["database__name"]

    def __str__(self) -> str:
        return f"{self.database} -> {self.resource}"


class WebsiteResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.WEBSITE

    website = models.OneToOneField(
        Website,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["website__name"]

    def __str__(self) -> str:
        return f"{self.website} -> {self.resource}"


class DomainResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.DOMAIN

    domain = models.OneToOneField(
        Domain,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["domain__domain_name"]

    def __str__(self) -> str:
        return f"{self.domain} -> {self.resource}"


class SSLCertificateResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.TLS_CERTIFICATE

    ssl_certificate = models.OneToOneField(
        SSLCertificate,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["ssl_certificate__domain__domain_name"]

    def __str__(self) -> str:
        return f"{self.ssl_certificate} -> {self.resource}"


class LicenceResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.LICENCE

    licence = models.OneToOneField(
        Licence,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["licence__name"]

    def __str__(self) -> str:
        return f"{self.licence} -> {self.resource}"


class ApplicationResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.APPLICATION

    application = models.OneToOneField(
        Application,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["application__name"]

    def __str__(self) -> str:
        return f"{self.application} -> {self.resource}"


class MobileAppResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.MOBILE_APP

    mobile_app = models.OneToOneField(
        MobileApp,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["mobile_app__name"]

    def __str__(self) -> str:
        return f"{self.mobile_app} -> {self.resource}"


class APIResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.API

    api = models.OneToOneField(
        API,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["api__name"]

    def __str__(self) -> str:
        return f"{self.api} -> {self.resource}"


class BotResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.BOT

    bot = models.OneToOneField(
        Bot,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["bot__name"]

    def __str__(self) -> str:
        return f"{self.bot} -> {self.resource}"


class EmailSystemResourceIdentity(LegacyResourceIdentityBase):
    expected_resource_type = InfrastructureResource.ResourceType.EMAIL_SYSTEM

    email_system = models.OneToOneField(
        EmailSystem,
        on_delete=models.PROTECT,
        related_name="structured_resource_identity",
    )

    class Meta:
        ordering = ["email_system__provider"]

    def __str__(self) -> str:
        return f"{self.email_system} -> {self.resource}"

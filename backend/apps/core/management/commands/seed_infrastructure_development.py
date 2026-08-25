from __future__ import annotations

import random
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.clients.models import Client
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import (
    API,
    Bot,
    Domain,
    EmailSystem,
    InfrastructureResource,
    MobileApp,
    ProviderAccount,
    ServiceProvider,
    SSLCertificate,
    Website,
    WebsiteTechStack,
)

DEMO_PREFIX = "[DEMO]"


class Command(BaseCommand):
    help = "Populate the extended infrastructure inventory with deterministic fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--scale", type=int, default=1)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_infrastructure_development is disabled when DEBUG=False. "
                "Use --force only in a disposable environment."
            )

        websites = list(Website.objects.filter(name__startswith=DEMO_PREFIX))
        domains = list(Domain.objects.filter(domain_name__startswith="demo-"))
        if not websites or not domains:
            raise CommandError("Run seed_development first so demo websites and domains exist.")

        rng = random.Random(20260818)
        scale = max(1, options["scale"])
        with transaction.atomic():
            if options["reset"]:
                self._reset()
            self._seed_providers()
            self._seed_website_technology(websites)
            self._seed_ssl(domains, rng)
            self._seed_mobile_apps(scale)
            self._seed_apis(scale)
            self._seed_bots(scale)
            self._seed_email_systems(scale)

        self.stdout.write(
            self.style.SUCCESS(f"Extended infrastructure development data ready (scale={scale}).")
        )

    def _reset(self) -> None:
        WebsiteTechStack.objects.filter(website__name__startswith=DEMO_PREFIX).delete()
        InfrastructureResource.objects.filter(
            name__startswith=DEMO_PREFIX,
            resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
        ).delete()
        ServiceProvider.objects.filter(name__startswith=DEMO_PREFIX).delete()
        SSLCertificate.objects.filter(domain__domain_name__startswith="demo-").delete()
        MobileApp.objects.filter(name__startswith=DEMO_PREFIX).delete()
        API.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Bot.objects.filter(name__startswith=DEMO_PREFIX).delete()
        EmailSystem.objects.filter(notes__startswith=DEMO_PREFIX).delete()

    def _seed_providers(self) -> None:
        provider_specs = (
            (
                "DigitalOcean",
                ServiceProvider.Category.CLOUD,
                "https://www.digitalocean.com",
                "https://cloud.digitalocean.com/support",
                "https://status.digitalocean.com",
                "https://docs.digitalocean.com",
            ),
            (
                "Cloudflare",
                ServiceProvider.Category.CDN,
                "https://www.cloudflare.com",
                "https://dash.cloudflare.com",
                "https://www.cloudflarestatus.com",
                "https://developers.cloudflare.com",
            ),
            (
                "GitHub",
                ServiceProvider.Category.SOURCE_CONTROL,
                "https://github.com",
                "https://support.github.com",
                "https://www.githubstatus.com",
                "https://docs.github.com",
            ),
            (
                "Microsoft 365",
                ServiceProvider.Category.SAAS,
                "https://www.microsoft.com/microsoft-365",
                "https://admin.microsoft.com",
                "https://status.cloud.microsoft",
                "https://learn.microsoft.com/microsoft-365",
            ),
        )
        providers: list[ServiceProvider] = []
        for index, (name, category, website, support, status, docs) in enumerate(
            provider_specs, start=1
        ):
            provider, _ = ServiceProvider.objects.update_or_create(
                slug=f"demo-provider-{index}",
                defaults={
                    "name": f"{DEMO_PREFIX} {name}",
                    "category": category,
                    "website_url": website,
                    "support_url": support,
                    "status_page_url": status,
                    "documentation_url": docs,
                    "notes": "Generated development provider catalogue entry.",
                    "is_active": True,
                },
            )
            providers.append(provider)

        clients = list(Client.objects.filter(status="active").order_by("id")[:2])
        account_specs: list[tuple[str, ServiceProvider, str, Client | None, str, str]] = [
            ("ADB DigitalOcean", providers[0], OwnershipType.INTERNAL, None, "ADB-DO-DEMO", "lon1"),
            ("ADB GitHub", providers[2], OwnershipType.INTERNAL, None, "adb-demo", "global"),
        ]
        for index, client in enumerate(clients, start=1):
            account_specs.append(
                (
                    f"{client} Cloudflare",
                    providers[1],
                    OwnershipType.CLIENT,
                    client,
                    f"CF-DEMO-{index:03d}",
                    "global",
                )
            )

        for name, provider, ownership_type, account_client, identifier, region in account_specs:
            resource, _ = InfrastructureResource.objects.update_or_create(
                name=f"{DEMO_PREFIX} {name}",
                resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
                defaults={
                    "ownership_type": ownership_type,
                    "client": account_client,
                    "lifecycle_status": InfrastructureResource.LifecycleStatus.ACTIVE,
                    "environment": InfrastructureResource.Environment.SHARED,
                    "criticality": InfrastructureResource.Criticality.HIGH,
                    "description": "Generated provider account with safe metadata only.",
                    "is_portal_visible": False,
                },
            )
            ProviderAccount.objects.update_or_create(
                resource=resource,
                defaults={
                    "provider": provider,
                    "account_identifier": identifier,
                    "tenant_id": f"tenant-{identifier.lower()}",
                    "portal_url": provider.support_url or provider.website_url,
                    "default_region": region,
                    "support_plan": "Development demo plan",
                    "billing_reference": f"DEMO-{resource.id:04d}",
                },
            )

    def _seed_website_technology(self, websites: list[Website]) -> None:
        technologies = [
            ("Next.js", "frontend", "16"),
            ("Django", "backend", "5.2"),
            ("PostgreSQL", "database", "17"),
            ("Redis", "other", "8"),
        ]
        for website in websites:
            for technology, category, version in technologies:
                WebsiteTechStack.objects.update_or_create(
                    website=website,
                    technology=technology,
                    defaults={"category": category, "version": version},
                )

    def _seed_ssl(self, domains: list[Domain], rng: random.Random) -> None:
        today = timezone.localdate()
        for index, domain in enumerate(domains, start=1):
            SSLCertificate.objects.update_or_create(
                domain=domain,
                provider="letsencrypt",
                defaults={
                    "cert_type": "DV",
                    "expiry_date": today + timedelta(days=rng.randint(10, 90)),
                },
            )

    def _seed_mobile_apps(self, scale: int) -> None:
        for index in range(1, (6 * scale) + 1):
            MobileApp.objects.update_or_create(
                name=f"{DEMO_PREFIX} Mobile App {index:02d}",
                defaults={
                    "platform": "both",
                    "framework": "flutter",
                    "bundle_id": f"uk.co.example.demo{index}",
                    "current_version": f"1.{index}.0",
                    "release_status": "live" if index % 3 else "testing",
                    "backend_api": f"https://api-demo-{index}.example.test",
                    "github_repository": "https://github.com/example/demo-mobile-app",
                    "notes": "Generated development mobile application.",
                },
            )

    def _seed_apis(self, scale: int) -> None:
        for index in range(1, (8 * scale) + 1):
            API.objects.update_or_create(
                name=f"{DEMO_PREFIX} API {index:02d}",
                defaults={
                    "api_type": "rest" if index % 2 else "graphql",
                    "description": "Generated development API inventory record.",
                    "base_url": f"https://api-{index}.example.test",
                    "visibility": "private_session",
                    "authentication": "session" if index % 2 else "oauth",
                    "versioning_strategy": "URL path versioning",
                    "rate_limiting": "100 requests/minute (demo)",
                    "documentation_url": f"https://api-{index}.example.test/docs",
                    "github_repository": "https://github.com/example/demo-api",
                    "notes": "Generated development API.",
                },
            )

    def _seed_bots(self, scale: int) -> None:
        for index in range(1, (5 * scale) + 1):
            Bot.objects.update_or_create(
                name=f"{DEMO_PREFIX} Automation Bot {index:02d}",
                defaults={
                    "platform": "discord" if index % 2 else "custom",
                    "bot_type": "automation",
                    "runtime": "python",
                    "hosting_location": "DigitalOcean LON1",
                    "permissions": "Generated development scopes only",
                    "github_repository": "https://github.com/example/demo-bot",
                    "notes": "Generated development automation bot.",
                },
            )

    def _seed_email_systems(self, scale: int) -> None:
        for index in range(1, (3 * scale) + 1):
            EmailSystem.objects.update_or_create(
                provider="microsoft_365",
                domains=f"demo-mail-{index}.example.test",
                defaults={
                    "admin_portal_url": "https://admin.microsoft.com",
                    "spf_status": "valid",
                    "dkim_status": "valid",
                    "dmarc_status": "quarantine",
                    "notes": f"{DEMO_PREFIX} Generated development email system {index}.",
                },
            )

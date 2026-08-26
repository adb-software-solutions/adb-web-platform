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
    IPAddress,
    MobileApp,
    Network,
    NetworkInterface,
    ProviderAccount,
    ServerProfile,
    ServiceProvider,
    SSLCertificate,
    Subnet,
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
            self._seed_structured_compute()
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
        InfrastructureResource.objects.filter(
            name__startswith=DEMO_PREFIX,
            resource_type__in=[
                InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
                InfrastructureResource.ResourceType.SERVER,
                InfrastructureResource.ResourceType.NETWORK,
                InfrastructureResource.ResourceType.SUBNET,
            ],
        ).delete()
        WebsiteTechStack.objects.filter(website__name__startswith=DEMO_PREFIX).delete()
        SSLCertificate.objects.filter(domain__domain_name__startswith="demo-").delete()
        MobileApp.objects.filter(name__startswith=DEMO_PREFIX).delete()
        API.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Bot.objects.filter(name__startswith=DEMO_PREFIX).delete()
        EmailSystem.objects.filter(notes__startswith=DEMO_PREFIX).delete()

    def _resource(
        self,
        *,
        name: str,
        resource_type: str,
        ownership_type: str = OwnershipType.INTERNAL,
        client: Client | None = None,
        environment: str = InfrastructureResource.Environment.PRODUCTION,
        criticality: str = InfrastructureResource.Criticality.NORMAL,
        description: str = "",
    ) -> InfrastructureResource:
        resource, _ = InfrastructureResource.objects.update_or_create(
            name=name,
            resource_type=resource_type,
            defaults={
                "ownership_type": ownership_type,
                "client": client,
                "lifecycle_status": InfrastructureResource.LifecycleStatus.ACTIVE,
                "environment": environment,
                "criticality": criticality,
                "description": description,
            },
        )
        resource.full_clean()
        resource.save()
        return resource

    def _seed_structured_compute(self) -> None:
        provider, _ = ServiceProvider.objects.update_or_create(
            slug="digitalocean",
            defaults={
                "name": "DigitalOcean",
                "category": ServiceProvider.Category.CLOUD,
                "website_url": "https://www.digitalocean.com",
                "is_active": True,
            },
        )
        provider_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB DigitalOcean",
            resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
            environment=InfrastructureResource.Environment.SHARED,
            description="Shared development provider account for structured infrastructure demos.",
        )
        provider_account, _ = ProviderAccount.objects.update_or_create(
            resource=provider_resource,
            defaults={
                "provider": provider,
                "account_identifier": "demo-adb-do",
                "default_region": "lon1",
            },
        )
        provider_account.full_clean()
        provider_account.save()

        network_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Production VPC",
            resource_type=InfrastructureResource.ResourceType.NETWORK,
            description="Development VPC demonstrating native structured networking.",
        )
        network, _ = Network.objects.update_or_create(
            resource=network_resource,
            defaults={
                "network_type": Network.NetworkType.VPC,
                "provider_account": provider_account,
                "provider_network_id": "demo-vpc-lon1",
                "cidr": "10.42.0.0/16",
                "gateway": "10.42.0.1",
                "region": "lon1",
                "dns_servers": ["1.1.1.1", "1.0.0.1"],
            },
        )
        network.full_clean()
        network.save()

        subnet_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Web Subnet",
            resource_type=InfrastructureResource.ResourceType.SUBNET,
            description="Development subnet for web workloads.",
        )
        subnet, _ = Subnet.objects.update_or_create(
            resource=subnet_resource,
            defaults={
                "network": network,
                "cidr": "10.42.10.0/24",
                "gateway": "10.42.10.1",
                "availability_zone": "lon1",
                "purpose": "Public-facing web workloads",
            },
        )
        subnet.full_clean()
        subnet.save()

        server_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB LON Web 01",
            resource_type=InfrastructureResource.ResourceType.SERVER,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Development structured server with native network and IP data.",
        )
        server, _ = ServerProfile.objects.update_or_create(
            resource=server_resource,
            defaults={
                "hostname": "demo-adb-lon-ws01",
                "fqdn": "demo-adb-lon-ws01.internal.example.test",
                "purpose": "Primary development web workload",
                "role": "Web server",
                "compute_type": ServerProfile.ComputeType.CLOUD_VM,
                "architecture": "x86_64",
                "cpu_model": "AMD EPYC",
                "cpu_cores": 4,
                "ram_mb": 8192,
                "root_disk_gb": 160,
                "os_family": ServerProfile.OSFamily.LINUX,
                "distribution": "Ubuntu",
                "os_version": "24.04",
                "provider_account": provider_account,
                "provider_resource_id": "demo-droplet-1001",
                "region": "lon1",
                "ssh_port": 22,
                "timezone": "Europe/London",
                "automatic_updates": True,
                "patch_window": "Sunday 03:00 Europe/London",
            },
        )
        server.full_clean()
        server.save()
        interface, _ = NetworkInterface.objects.update_or_create(
            server=server,
            name="eth0",
            defaults={
                "network": network,
                "subnet": subnet,
                "mac_address": "02:00:00:00:10:01",
                "mtu": 1500,
                "description": "Primary application interface",
            },
        )
        interface.full_clean()
        interface.save()
        internal_ip, _ = IPAddress.objects.update_or_create(
            resource=server_resource,
            address="10.42.10.10",
            defaults={
                "interface": interface,
                "scope": IPAddress.Scope.PRIVATE,
                "is_primary": True,
                "ptr_record": "demo-adb-lon-ws01.internal.example.test",
            },
        )
        internal_ip.full_clean()
        internal_ip.save()
        public_ip, _ = IPAddress.objects.update_or_create(
            resource=server_resource,
            address="203.0.113.10",
            defaults={
                "scope": IPAddress.Scope.PUBLIC,
                "is_primary": False,
                "description": "Reserved documentation address used for development data.",
            },
        )
        public_ip.full_clean()
        public_ip.save()

        client = Client.objects.filter(status="active").order_by("id").first()
        if client is None:
            return
        client_name = client.company or client.name
        client_server_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Web 01",
            resource_type=InfrastructureResource.ResourceType.SERVER,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned development server using shared ADB infrastructure.",
        )
        client_server, _ = ServerProfile.objects.update_or_create(
            resource=client_server_resource,
            defaults={
                "hostname": "demo-client-web01",
                "purpose": "Client production web workload",
                "role": "Web server",
                "compute_type": ServerProfile.ComputeType.CLOUD_VM,
                "cpu_cores": 2,
                "ram_mb": 4096,
                "root_disk_gb": 80,
                "os_family": ServerProfile.OSFamily.LINUX,
                "distribution": "Ubuntu",
                "os_version": "24.04",
                "provider_account": provider_account,
                "provider_resource_id": "demo-droplet-client-01",
                "region": "lon1",
                "ssh_port": 22,
            },
        )
        client_server.full_clean()
        client_server.save()

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
        for domain in domains:
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

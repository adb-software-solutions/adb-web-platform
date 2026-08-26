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
    ApplicationEnvironment,
    ApplicationProfile,
    ApplicationRepositoryLink,
    Bot,
    DatabaseInstance,
    Domain,
    EmailSystem,
    InfrastructureResource,
    IPAddress,
    LogicalDatabase,
    MobileApp,
    Network,
    NetworkInterface,
    ProviderAccount,
    ServerProfile,
    ServiceProvider,
    SourceRepository,
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
            self._seed_structured_data_applications()
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
                InfrastructureResource.ResourceType.DATABASE_INSTANCE,
                InfrastructureResource.ResourceType.LOGICAL_DATABASE,
                InfrastructureResource.ResourceType.APPLICATION,
                InfrastructureResource.ResourceType.APPLICATION_ENVIRONMENT,
                InfrastructureResource.ResourceType.SOURCE_REPOSITORY,
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

    def _seed_structured_data_applications(self) -> None:
        shared_cloud_account = ProviderAccount.objects.select_related("resource").get(
            resource__name=f"{DEMO_PREFIX} ADB DigitalOcean"
        )
        internal_server = ServerProfile.objects.select_related("resource").get(
            resource__name=f"{DEMO_PREFIX} ADB LON Web 01"
        )

        github_provider, _ = ServiceProvider.objects.update_or_create(
            slug="github",
            defaults={
                "name": "GitHub",
                "category": ServiceProvider.Category.SOURCE_CONTROL,
                "website_url": "https://github.com",
                "is_active": True,
            },
        )
        github_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB GitHub",
            resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
            environment=InfrastructureResource.Environment.SHARED,
            description="Shared source-control provider account used by development applications.",
        )
        github_account, _ = ProviderAccount.objects.update_or_create(
            resource=github_resource,
            defaults={
                "provider": github_provider,
                "account_identifier": "adb-software-solutions-demo",
                "portal_url": "https://github.com/adb-software-solutions",
            },
        )
        github_account.full_clean()
        github_account.save()

        database_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB PostgreSQL",
            resource_type=InfrastructureResource.ResourceType.DATABASE_INSTANCE,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Self-hosted PostgreSQL service for the structured application demo.",
        )
        database_instance, _ = DatabaseInstance.objects.update_or_create(
            resource=database_resource,
            defaults={
                "engine": DatabaseInstance.Engine.POSTGRESQL,
                "engine_version": "18",
                "hosting_type": DatabaseInstance.HostingType.SELF_HOSTED,
                "server": internal_server,
                "provider_account": shared_cloud_account,
                "endpoint": "10.42.10.10",
                "port": 5432,
                "region": "lon1",
                "tls_mode": DatabaseInstance.TLSMode.REQUIRED,
                "high_availability": False,
                "replica_count": 0,
                "backup_enabled": True,
                "maintenance_window": "Sunday 02:00 Europe/London",
            },
        )
        database_instance.full_clean()
        database_instance.save()

        logical_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform Database",
            resource_type=InfrastructureResource.ResourceType.LOGICAL_DATABASE,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Primary logical database for the ADB Platform demo application.",
        )
        logical_database, _ = LogicalDatabase.objects.update_or_create(
            resource=logical_resource,
            defaults={
                "instance": database_instance,
                "database_name": "adb_platform_demo",
                "purpose": "Application data",
                "default_schema": "public",
                "charset": "UTF8",
            },
        )
        logical_database.full_clean()
        logical_database.save()

        application_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform",
            resource_type=InfrastructureResource.ResourceType.APPLICATION,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Logical ADB Platform application used by structured infrastructure demos.",
        )
        application, _ = ApplicationProfile.objects.update_or_create(
            resource=application_resource,
            defaults={
                "application_type": ApplicationProfile.ApplicationType.SAAS,
                "owner_team": "ADB Software Solutions",
                "primary_language": "Python / TypeScript",
                "framework": "Django / Next.js",
            },
        )
        application.full_clean()
        application.save()

        environment_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform Production",
            resource_type=InfrastructureResource.ResourceType.APPLICATION_ENVIRONMENT,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Production-like deployment context for the ADB Platform demo.",
        )
        application_environment, _ = ApplicationEnvironment.objects.update_or_create(
            resource=environment_resource,
            defaults={
                "application": application,
                "deployment_type": ApplicationEnvironment.DeploymentType.SERVER,
                "server": internal_server,
                "provider_account": shared_cloud_account,
                "provider_resource_id": "demo-adb-platform-production",
                "runtime": "Python / Node.js",
                "runtime_version": "3.12 / 22",
                "release_version": "demo-main",
                "region": "lon1",
                "branch_or_ref": "main",
                "automatic_deployments": True,
            },
        )
        application_environment.full_clean()
        application_environment.save()

        repository_resource = self._resource(
            name=f"{DEMO_PREFIX} ADB Platform Repository",
            resource_type=InfrastructureResource.ResourceType.SOURCE_REPOSITORY,
            environment=InfrastructureResource.Environment.SHARED,
            description="Primary source repository for the structured ADB Platform demo.",
        )
        repository, _ = SourceRepository.objects.update_or_create(
            resource=repository_resource,
            defaults={
                "provider_account": github_account,
                "web_url": "https://github.com/adb-software-solutions/adb-web-platform",
                "clone_url": "git@github.com:adb-software-solutions/adb-web-platform.git",
                "provider_repository_id": "demo-adb-web-platform",
                "owner_name": "adb-software-solutions",
                "repository_name": "adb-web-platform",
                "default_branch": "main",
                "visibility": SourceRepository.Visibility.PRIVATE,
                "is_fork": False,
            },
        )
        repository.full_clean()
        repository.save()
        repository_link, _ = ApplicationRepositoryLink.objects.update_or_create(
            application=application,
            repository=repository,
            role=ApplicationRepositoryLink.Role.PRIMARY,
            path="",
            defaults={"notes": "Primary monorepo for the development application."},
        )
        repository_link.full_clean()
        repository_link.save()

        client = Client.objects.filter(status="active").order_by("id").first()
        if client is None:
            return
        client_name = client.company or client.name
        client_server = ServerProfile.objects.select_related("resource").get(
            resource__name=f"{DEMO_PREFIX} {client_name} Web 01"
        )
        client_database_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} PostgreSQL",
            resource_type=InfrastructureResource.ResourceType.DATABASE_INSTANCE,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned PostgreSQL service using the Client demo server.",
        )
        client_database, _ = DatabaseInstance.objects.update_or_create(
            resource=client_database_resource,
            defaults={
                "engine": DatabaseInstance.Engine.POSTGRESQL,
                "engine_version": "18",
                "hosting_type": DatabaseInstance.HostingType.SELF_HOSTED,
                "server": client_server,
                "provider_account": shared_cloud_account,
                "endpoint": "demo-client-web01",
                "port": 5432,
                "region": "lon1",
                "tls_mode": DatabaseInstance.TLSMode.REQUIRED,
                "high_availability": False,
                "backup_enabled": True,
                "maintenance_window": "Saturday 02:00 Europe/London",
            },
        )
        client_database.full_clean()
        client_database.save()

        client_logical_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Application Database",
            resource_type=InfrastructureResource.ResourceType.LOGICAL_DATABASE,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned logical application database.",
        )
        client_logical, _ = LogicalDatabase.objects.update_or_create(
            resource=client_logical_resource,
            defaults={
                "instance": client_database,
                "database_name": "client_application_demo",
                "purpose": "Client application data",
                "default_schema": "public",
                "charset": "UTF8",
            },
        )
        client_logical.full_clean()
        client_logical.save()

        client_application_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Application",
            resource_type=InfrastructureResource.ResourceType.APPLICATION,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned logical application in the structured infrastructure graph.",
        )
        client_application, _ = ApplicationProfile.objects.update_or_create(
            resource=client_application_resource,
            defaults={
                "application_type": ApplicationProfile.ApplicationType.WEB_APP,
                "owner_team": "ADB Software Solutions",
                "primary_language": "Python / TypeScript",
                "framework": "Django / Next.js",
            },
        )
        client_application.full_clean()
        client_application.save()

        client_environment_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Production",
            resource_type=InfrastructureResource.ResourceType.APPLICATION_ENVIRONMENT,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            criticality=InfrastructureResource.Criticality.HIGH,
            description="Client-owned production deployment using the Client demo server.",
        )
        client_environment, _ = ApplicationEnvironment.objects.update_or_create(
            resource=client_environment_resource,
            defaults={
                "application": client_application,
                "deployment_type": ApplicationEnvironment.DeploymentType.SERVER,
                "server": client_server,
                "provider_account": shared_cloud_account,
                "provider_resource_id": "demo-client-production",
                "runtime": "Python / Node.js",
                "runtime_version": "3.12 / 22",
                "release_version": "demo-production",
                "region": "lon1",
                "branch_or_ref": "main",
                "automatic_deployments": True,
            },
        )
        client_environment.full_clean()
        client_environment.save()

        client_repository_resource = self._resource(
            name=f"{DEMO_PREFIX} {client_name} Repository",
            resource_type=InfrastructureResource.ResourceType.SOURCE_REPOSITORY,
            ownership_type=OwnershipType.CLIENT,
            client=client,
            environment=InfrastructureResource.Environment.SHARED,
            description="Client-owned source repository managed through the shared ADB GitHub account.",
        )
        client_repository, _ = SourceRepository.objects.update_or_create(
            resource=client_repository_resource,
            defaults={
                "provider_account": github_account,
                "web_url": "https://github.com/example/client-application-demo",
                "clone_url": "git@github.com:example/client-application-demo.git",
                "provider_repository_id": "demo-client-application",
                "owner_name": "example",
                "repository_name": "client-application-demo",
                "default_branch": "main",
                "visibility": SourceRepository.Visibility.PRIVATE,
                "is_fork": False,
            },
        )
        client_repository.full_clean()
        client_repository.save()
        client_repository_link, _ = ApplicationRepositoryLink.objects.update_or_create(
            application=client_application,
            repository=client_repository,
            role=ApplicationRepositoryLink.Role.PRIMARY,
            path="",
            defaults={"notes": "Primary Client application repository."},
        )
        client_repository_link.full_clean()
        client_repository_link.save()

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

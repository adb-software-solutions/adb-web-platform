from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.core.ownership import OwnershipType
from apps.infrastructure.models import InfrastructureResource
from apps.monitoring.models import MonitorCheck, MonitorIncident, MonitorResult

DEMO_PREFIX = "[DEMO]"


class Command(BaseCommand):
    help = "Populate deterministic monitoring checks, history, and incidents for development."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--scale", type=int, default=1)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_monitoring_development is disabled when DEBUG=False. "
                "Use --force only in a disposable environment."
            )

        scale = max(1, options["scale"])
        if not InfrastructureResource.objects.filter(name__startswith=DEMO_PREFIX).exists():
            raise CommandError("Run seed_infrastructure_development first.")

        with transaction.atomic():
            if options["reset"]:
                MonitorCheck.objects.filter(name__startswith=DEMO_PREFIX).delete()
            checks = self._seed_checks()
            history_points = 48 * scale
            for check, status, failure_tail in checks:
                self._seed_history(
                    check,
                    status=status,
                    failure_tail=failure_tail,
                    history_points=history_points,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Monitoring development data ready ({len(checks)} checks, scale={scale})."
            )
        )

    def _resource(
        self,
        resource_type: str,
        *,
        ownership_type: str = OwnershipType.INTERNAL,
        name: str | None = None,
    ) -> InfrastructureResource:
        resources = InfrastructureResource.objects.filter(
            resource_type=resource_type,
            ownership_type=ownership_type,
            lifecycle_status=InfrastructureResource.LifecycleStatus.ACTIVE,
        )
        if name is not None:
            resources = resources.filter(name=name)
        resource = resources.order_by("id").first()
        if resource is None:
            raise CommandError(
                f"No seeded {ownership_type} {resource_type} resource is available for monitoring."
            )
        return resource

    def _check(
        self,
        *,
        resource: InfrastructureResource,
        name: str,
        check_type: str,
        target: str,
        severity: str = MonitorCheck.Severity.ERROR,
        port: int | None = None,
        expected_value: str = "",
        interval_seconds: int = 300,
        failure_threshold: int = 3,
        expiry_warning_days: int = 30,
    ) -> MonitorCheck:
        check, _ = MonitorCheck.objects.update_or_create(
            resource=resource,
            name=f"{DEMO_PREFIX} {name}",
            defaults={
                "check_type": check_type,
                "severity": severity,
                "enabled": True,
                "target": target,
                "port": port,
                "expected_value": expected_value,
                "forbidden_value": "",
                "interval_seconds": interval_seconds,
                "timeout_seconds": 10,
                "failure_threshold": failure_threshold,
                "recovery_threshold": 2,
                "expiry_warning_days": expiry_warning_days,
                "credential": None,
            },
        )
        check.full_clean()
        check.save()
        return check

    def _seed_checks(self) -> list[tuple[MonitorCheck, str, int]]:
        internal_server = self._resource(
            InfrastructureResource.ResourceType.SERVER,
            name=f"{DEMO_PREFIX} ADB LON Web 01",
        )
        internal_database = self._resource(
            InfrastructureResource.ResourceType.DATABASE_INSTANCE,
            name=f"{DEMO_PREFIX} ADB PostgreSQL",
        )
        internal_endpoint = self._resource(
            InfrastructureResource.ResourceType.WEBSITE_ENDPOINT,
            name=f"{DEMO_PREFIX} ADB Platform Website Production",
        )
        internal_domain = self._resource(
            InfrastructureResource.ResourceType.DOMAIN,
            name=f"{DEMO_PREFIX} ADB Platform Domain",
        )
        internal_dns = self._resource(
            InfrastructureResource.ResourceType.DNS_ZONE,
            name=f"{DEMO_PREFIX} ADB Platform DNS",
        )
        internal_tls = self._resource(
            InfrastructureResource.ResourceType.TLS_CERTIFICATE,
            name=f"{DEMO_PREFIX} ADB Platform TLS",
        )

        seeded: list[tuple[MonitorCheck, str, int]] = [
            (
                self._check(
                    resource=internal_server,
                    name="Server reachability",
                    check_type=MonitorCheck.CheckType.ICMP,
                    target="203.0.113.10",
                    severity=MonitorCheck.Severity.CRITICAL,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_database,
                    name="PostgreSQL port",
                    check_type=MonitorCheck.CheckType.TCP,
                    target="10.42.10.10",
                    port=5432,
                    severity=MonitorCheck.Severity.CRITICAL,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_endpoint,
                    name="Primary website",
                    check_type=MonitorCheck.CheckType.HTTP,
                    target="https://adb-platform.example.test",
                    severity=MonitorCheck.Severity.CRITICAL,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_endpoint,
                    name="Homepage content",
                    check_type=MonitorCheck.CheckType.CONTENT,
                    target="https://adb-platform.example.test",
                    expected_value="ADB",
                    severity=MonitorCheck.Severity.WARNING,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_dns,
                    name="Authoritative DNS",
                    check_type=MonitorCheck.CheckType.DNS,
                    target="adb-platform.example.test",
                    severity=MonitorCheck.Severity.ERROR,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_tls,
                    name="Certificate validity",
                    check_type=MonitorCheck.CheckType.TLS,
                    target="adb-platform.example.test",
                    severity=MonitorCheck.Severity.ERROR,
                    expiry_warning_days=30,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
            (
                self._check(
                    resource=internal_domain,
                    name="Registration expiry",
                    check_type=MonitorCheck.CheckType.DOMAIN_EXPIRY,
                    target="adb-platform.example.test",
                    severity=MonitorCheck.Severity.WARNING,
                    interval_seconds=3600,
                    failure_threshold=1,
                    expiry_warning_days=30,
                ),
                MonitorCheck.Status.HEALTHY,
                0,
            ),
        ]

        client_endpoint = self._resource(
            InfrastructureResource.ResourceType.WEBSITE_ENDPOINT,
            ownership_type=OwnershipType.CLIENT,
        )
        client_tls = self._resource(
            InfrastructureResource.ResourceType.TLS_CERTIFICATE,
            ownership_type=OwnershipType.CLIENT,
        )
        seeded.extend(
            [
                (
                    self._check(
                        resource=client_endpoint,
                        name="Client website",
                        check_type=MonitorCheck.CheckType.HTTP,
                        target="https://client-application.example.test",
                        severity=MonitorCheck.Severity.ERROR,
                    ),
                    MonitorCheck.Status.DEGRADED,
                    2,
                ),
                (
                    self._check(
                        resource=client_tls,
                        name="Client certificate expiry",
                        check_type=MonitorCheck.CheckType.TLS,
                        target="client-application.example.test",
                        severity=MonitorCheck.Severity.ERROR,
                        failure_threshold=3,
                        expiry_warning_days=30,
                    ),
                    MonitorCheck.Status.FAILING,
                    4,
                ),
            ]
        )
        return seeded

    def _seed_history(
        self,
        check: MonitorCheck,
        *,
        status: str,
        failure_tail: int,
        history_points: int,
    ) -> None:
        check.results.all().delete()
        check.incidents.all().delete()

        now = timezone.now()
        results: list[MonitorResult] = []
        for index in range(history_points):
            started_at = now - timedelta(minutes=((history_points - index) * 30) + 5)
            is_tail_failure = index >= history_points - failure_tail
            is_historical_failure = (
                status == MonitorCheck.Status.HEALTHY
                and history_points >= 24
                and index == history_points - 20
            )
            failed = is_tail_failure or is_historical_failure
            duration_ms = 110 + ((index * 37 + check.id * 13) % 260)
            results.append(
                MonitorResult(
                    monitor_check=check,
                    outcome=(
                        MonitorResult.Outcome.FAILURE
                        if failed
                        else MonitorResult.Outcome.SUCCESS
                    ),
                    started_at=started_at,
                    finished_at=started_at + timedelta(milliseconds=duration_ms),
                    duration_ms=duration_ms,
                    status_code=(503 if failed else 200)
                    if check.check_type
                    in [MonitorCheck.CheckType.HTTP, MonitorCheck.CheckType.CONTENT]
                    else None,
                    observed_value="",
                    message="Synthetic development failure."
                    if failed
                    else "Synthetic development check succeeded.",
                )
            )
        MonitorResult.objects.bulk_create(results)

        latest = results[-1]
        check.status = status
        check.consecutive_failures = failure_tail
        check.consecutive_successes = 0 if failure_tail else 12
        check.last_checked_at = latest.started_at
        check.last_duration_ms = latest.duration_ms
        check.last_message = latest.message
        check.next_run_at = now + timedelta(seconds=check.interval_seconds)
        check.save(
            update_fields=[
                "status",
                "consecutive_failures",
                "consecutive_successes",
                "last_checked_at",
                "last_duration_ms",
                "last_message",
                "next_run_at",
                "updated_at",
            ]
        )

        if status == MonitorCheck.Status.FAILING:
            opened_at = now - timedelta(minutes=max(1, failure_tail) * 30)
            MonitorIncident.objects.create(
                monitor_check=check,
                status=MonitorIncident.Status.OPEN,
                severity=check.severity,
                opened_at=opened_at,
                failure_count=failure_tail,
                summary="Synthetic development incident for the current failing check.",
            )
        elif status == MonitorCheck.Status.HEALTHY and check.check_type == MonitorCheck.CheckType.HTTP:
            opened_at = now - timedelta(days=3, minutes=20)
            MonitorIncident.objects.create(
                monitor_check=check,
                status=MonitorIncident.Status.RESOLVED,
                severity=check.severity,
                opened_at=opened_at,
                resolved_at=opened_at + timedelta(minutes=20),
                failure_count=check.failure_threshold,
                summary="Synthetic resolved incident retained for monitoring history.",
            )

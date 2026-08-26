from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Callable
from urllib.parse import urlparse

from django.utils import timezone

from .models import MonitorCheck
from .services import CheckObservation


def _timed_observation(
    operation: Callable[[], tuple[bool, str, int | None, str]],
) -> CheckObservation:
    started_at = timezone.now()
    started = time.monotonic()
    try:
        successful, message, status_code, observed_value = operation()
        execution_error = False
    except (OSError, ValueError, urllib.error.URLError) as error:
        successful = False
        message = str(error)
        status_code = None
        observed_value = ""
        execution_error = True
    finished_at = timezone.now()
    return CheckObservation(
        successful=successful,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(0, round((time.monotonic() - started) * 1000)),
        message=message,
        status_code=status_code,
        observed_value=observed_value,
        execution_error=execution_error,
    )


def execute_check(check: MonitorCheck) -> CheckObservation:
    """Execute supported unauthenticated probes without persisting secret material."""
    timeout = check.timeout_seconds

    if check.check_type == MonitorCheck.CheckType.TCP:
        def tcp_probe() -> tuple[bool, str, int | None, str]:
            assert check.port is not None
            with socket.create_connection((check.target, check.port), timeout=timeout):
                return True, "TCP connection succeeded.", None, f"{check.target}:{check.port}"

        return _timed_observation(tcp_probe)

    if check.check_type in [MonitorCheck.CheckType.HTTP, MonitorCheck.CheckType.CONTENT]:
        def http_probe() -> tuple[bool, str, int | None, str]:
            request = urllib.request.Request(
                check.target,
                headers={"User-Agent": "ADB-Monitor/1.0"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(1_000_000).decode("utf-8", errors="replace")
                status_code = response.status
            successful = 200 <= status_code < 400
            if check.check_type == MonitorCheck.CheckType.CONTENT:
                if check.expected_value and check.expected_value not in body:
                    return False, "Expected content was not present.", status_code, ""
                if check.forbidden_value and check.forbidden_value in body:
                    return False, "Forbidden content was present.", status_code, ""
            return successful, f"HTTP {status_code}.", status_code, ""

        return _timed_observation(http_probe)

    if check.check_type == MonitorCheck.CheckType.DNS:
        def dns_probe() -> tuple[bool, str, int | None, str]:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(check.target, None)})
            observed = ", ".join(addresses)
            matches = not check.expected_value or check.expected_value in addresses
            return matches, "DNS lookup succeeded." if matches else "DNS value did not match.", None, observed

        return _timed_observation(dns_probe)

    if check.check_type == MonitorCheck.CheckType.TLS:
        def tls_probe() -> tuple[bool, str, int | None, str]:
            parsed = urlparse(check.target if "://" in check.target else f"https://{check.target}")
            hostname = parsed.hostname
            if not hostname:
                raise ValueError("TLS target does not contain a hostname.")
            port = parsed.port or check.port or 443
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=timeout) as raw_socket:
                with context.wrap_socket(raw_socket, server_hostname=hostname) as tls_socket:
                    certificate = tls_socket.getpeercert()
            expiry_text = str(certificate.get("notAfter", ""))
            expiry = datetime.strptime(expiry_text, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
            days = (expiry - timezone.now()).days
            return (
                days >= check.expiry_warning_days,
                f"TLS certificate expires in {days} days.",
                None,
                expiry.isoformat(),
            )

        return _timed_observation(tls_probe)

    now = timezone.now()
    return CheckObservation(
        successful=False,
        started_at=now,
        finished_at=now,
        duration_ms=0,
        message=f"{check.get_check_type_display()} execution is not implemented yet.",
        execution_error=True,
    )

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .execution import execute_check
from .models import MonitorCheck
from .services import record_observation


@shared_task(name="monitoring.enqueue_due_checks", queue="general")
def enqueue_due_checks() -> int:
    due_ids = list(
        MonitorCheck.objects.filter(enabled=True)
        .filter(Q(next_run_at__isnull=True) | Q(next_run_at__lte=timezone.now()))
        .values_list("id", flat=True)
    )
    for check_id in due_ids:
        run_monitor_check.delay(check_id)
    return len(due_ids)


@shared_task(name="monitoring.run_check", queue="general")
def run_monitor_check(check_id: int) -> None:
    check = MonitorCheck.objects.select_related("resource", "credential").filter(id=check_id).first()
    if check is None or not check.enabled:
        return
    record_observation(check.id, execute_check(check))

from __future__ import annotations

from typing import cast

from django.db.models import Q
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router

from apps.core.ownership import OwnershipType
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .admin_views import _build_task_summary, _permission_problem, _scoped_tasks
from .focus_schemas import TaskFocusCountsOut, TaskFocusPageOut, TaskFocusView

focus_router = Router(tags=["admin-task-focus"])


def _focus_counts(request: HttpRequest) -> TaskFocusCountsOut:
    today = timezone.localdate()
    mine = _scoped_tasks(request).filter(assigned_to_id=request.user.id)
    open_tasks = mine.filter(completed_at__isnull=True)
    return TaskFocusCountsOut(
        my=open_tasks.count(),
        today=open_tasks.filter(due_date=today).count(),
        upcoming=open_tasks.filter(due_date__gt=today).count(),
        overdue=open_tasks.filter(due_date__lt=today).count(),
        completed=mine.filter(completed_at__isnull=False).count(),
    )


@focus_router.get(
    "/task-focus",
    response={200: TaskFocusPageOut, 401: ProblemDetail, 403: ProblemDetail},
)
def task_focus(
    request: HttpRequest,
    focus: TaskFocusView = "my",
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    ownership_type: str | None = None,
    completed: bool | None = None,
) -> TaskFocusPageOut | tuple[int, dict[str, object]]:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return cast(tuple[int, dict[str, object]], problem)

    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    today = timezone.localdate()
    user = cast(User, request.user)
    tasks = _scoped_tasks(request)
    mine = tasks.filter(assigned_to=user)

    if focus == "my":
        tasks = mine.filter(completed_at__isnull=True)
    elif focus == "today":
        tasks = mine.filter(completed_at__isnull=True, due_date=today)
    elif focus == "upcoming":
        tasks = mine.filter(completed_at__isnull=True, due_date__gt=today)
    elif focus == "overdue":
        tasks = mine.filter(completed_at__isnull=True, due_date__lt=today)
    elif focus == "completed":
        tasks = mine.filter(completed_at__isnull=False)
    elif completed is not None:
        tasks = tasks.filter(completed_at__isnull=not completed)
    else:
        tasks = tasks.filter(completed_at__isnull=True)

    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
    if ownership_type in {OwnershipType.INTERNAL, OwnershipType.CLIENT}:
        tasks = tasks.filter(ownership_type=ownership_type)

    tasks = tasks.order_by("completed_at", "due_date", "-priority", "-created_at")
    total = tasks.count()
    start = (page - 1) * page_size
    items = [_build_task_summary(task) for task in tasks[start : start + page_size]]
    return TaskFocusPageOut(
        focus=focus,
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        counts=_focus_counts(request),
    )

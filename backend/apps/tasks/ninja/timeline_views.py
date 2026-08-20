from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .timeline_schemas import ProjectTimelineOut, ProjectTimelineTaskOut
from .workspace_views import (
    StaffProblem,
    _permission_problem,
    _problem,
    _user_name,
    _visible_projects,
    _visible_tasks,
)

timeline_router = Router(tags=["admin-task-timeline"])


@timeline_router.get(
    "/task-timeline/projects/{project_id}",
    response={
        200: ProjectTimelineOut,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def project_timeline(
    request: HttpRequest,
    project_id: int,
) -> ProjectTimelineOut | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem
    user = cast(User, request.user)
    project = _visible_projects(user).filter(id=project_id).first()
    if project is None:
        return _problem("Project not found or outside your access scope.", "not_found", 404)

    tasks = (
        _visible_tasks(user)
        .filter(project=project)
        .exclude(start_date__isnull=True, due_date__isnull=True)
        .prefetch_related("dependency_links")
        .order_by("start_date", "due_date", "sort_order", "id")
    )
    return ProjectTimelineOut(
        project_id=project.id,
        project_name=project.name,
        tasks=[
            ProjectTimelineTaskOut(
                id=task.id,
                title=task.title,
                start_date=task.start_date,
                due_date=task.due_date,
                completed=task.completed_at is not None,
                priority=task.priority,
                assigned_to_name=_user_name(task.assigned_to),
                parent_task_id=task.parent_task_id,
                blocked_by_ids=[
                    dependency.blocking_task_id for dependency in task.dependency_links.all()
                ],
            )
            for task in tasks
        ],
    )

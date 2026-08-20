from __future__ import annotations

from typing import cast

from django.db import transaction
from django.http import HttpRequest
from ninja import Router

from apps.tasks.models import TaskSection
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .section_schemas import TaskSectionMoveIn, TaskSectionMutationOut, TaskSectionUpdateIn
from .workspace_views import (
    StaffProblem,
    _midpoint,
    _permission_problem,
    _problem,
    _visible_task_lists,
)

section_router = Router(tags=["admin-task-sections"])


def _section_out(section: TaskSection) -> TaskSectionMutationOut:
    return TaskSectionMutationOut(
        id=section.id,
        name=section.name,
        sort_order=section.sort_order,
    )


@section_router.patch(
    "/task-workspaces/lists/{task_list_id}/sections/{section_id}",
    response={
        200: TaskSectionMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def update_task_section(
    request: HttpRequest,
    task_list_id: int,
    section_id: int,
    payload: TaskSectionUpdateIn,
) -> TaskSectionMutationOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_tasklist")
    if problem:
        return problem
    user = cast(User, request.user)
    task_list = _visible_task_lists(user).filter(id=task_list_id).first()
    if task_list is None:
        return _problem("Task list not found or outside your access scope.", "not_found", 404)
    section = task_list.sections.filter(id=section_id).first()
    if section is None:
        return _problem("Task section not found.", "not_found", 404)

    name = payload.name.strip()
    if not name:
        return _problem("Section name is required.", "validation_error")
    section.name = name
    section.save(update_fields=["name", "updated_at"])
    return _section_out(section)


@section_router.post(
    "/task-workspaces/lists/{task_list_id}/sections/{section_id}/move",
    response={
        200: TaskSectionMutationOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
@transaction.atomic
def move_task_section(
    request: HttpRequest,
    task_list_id: int,
    section_id: int,
    payload: TaskSectionMoveIn,
) -> TaskSectionMutationOut | StaffProblem:
    problem = _permission_problem(request, "tasks.change_tasklist")
    if problem:
        return problem
    user = cast(User, request.user)
    task_list = _visible_task_lists(user).filter(id=task_list_id).first()
    if task_list is None:
        return _problem("Task list not found or outside your access scope.", "not_found", 404)

    section = (
        TaskSection.objects.select_for_update().filter(task_list=task_list, id=section_id).first()
    )
    if section is None:
        return _problem("Task section not found.", "not_found", 404)

    before = None
    after = None
    if payload.before_section_id is not None:
        before = task_list.sections.filter(id=payload.before_section_id).first()
        if before is None:
            return _problem(
                "Move neighbours must belong to this task list.",
                "context_mismatch",
            )
    if payload.after_section_id is not None:
        after = task_list.sections.filter(id=payload.after_section_id).first()
        if after is None:
            return _problem(
                "Move neighbours must belong to this task list.",
                "context_mismatch",
            )
    if before is not None and before.id == section.id:
        before = None
    if after is not None and after.id == section.id:
        after = None

    section.sort_order = _midpoint(
        before.sort_order if before else None,
        after.sort_order if after else None,
    )
    section.save(update_fields=["sort_order", "updated_at"])
    return _section_out(section)

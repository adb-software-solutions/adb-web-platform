from __future__ import annotations

from typing import cast

from django.http import HttpRequest
from ninja import Router

from apps.core.models import AuditEvent
from apps.tasks.models import TaskComment
from authentication.models import User
from authentication.ninja.schemas import ProblemDetail

from .comment_schemas import TaskCommentIn, TaskCommentOut
from .relations_views import StaffProblem, _permission_problem, _problem, _visible_tasks

comment_router = Router(tags=["admin-task-comments"])


def _author_name(comment: TaskComment) -> str:
    if comment.author is None:
        return "Former staff member"
    return (
        f"{comment.author.first_name} {comment.author.last_name}".strip()
        or comment.author.email
    )


def _comment_out(comment: TaskComment) -> TaskCommentOut:
    return TaskCommentOut(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        author_name=_author_name(comment),
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@comment_router.get(
    "/task-comments/tasks/{task_id}",
    response={
        200: list[TaskCommentOut],
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def list_task_comments(
    request: HttpRequest,
    task_id: int,
) -> list[TaskCommentOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.view_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)

    comments = task.comments.select_related("author").order_by("created_at", "id")
    return [_comment_out(comment) for comment in comments]


@comment_router.post(
    "/task-comments/tasks/{task_id}",
    response={
        201: TaskCommentOut,
        400: ProblemDetail,
        401: ProblemDetail,
        403: ProblemDetail,
        404: ProblemDetail,
    },
)
def create_task_comment(
    request: HttpRequest,
    task_id: int,
    payload: TaskCommentIn,
) -> tuple[int, TaskCommentOut] | StaffProblem:
    problem = _permission_problem(request, "tasks.change_task")
    if problem:
        return problem
    user = cast(User, request.user)
    task = _visible_tasks(user).filter(id=task_id).first()
    if task is None:
        return _problem("Task not found or outside your access scope.", "not_found", 404)

    body = payload.body.strip()
    if not body:
        return _problem("Comment text is required.", "validation_error")
    comment = TaskComment.objects.create(task=task, author=user, body=body)
    AuditEvent.record(
        action="tasks.comment_added",
        actor=user,
        target=task,
        metadata={"comment_id": comment.id},
    )
    return 201, _comment_out(comment)

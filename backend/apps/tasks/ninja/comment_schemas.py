from datetime import datetime
from uuid import UUID

from ninja import Schema


class TaskCommentIn(Schema):
    body: str


class TaskCommentOut(Schema):
    id: int
    task_id: int
    author_id: UUID | None
    author_name: str
    body: str
    created_at: datetime
    updated_at: datetime

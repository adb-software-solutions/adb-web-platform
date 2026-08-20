from decimal import Decimal

from ninja import Schema


class TaskSectionUpdateIn(Schema):
    name: str


class TaskSectionMoveIn(Schema):
    before_section_id: int | None = None
    after_section_id: int | None = None


class TaskSectionMutationOut(Schema):
    id: int
    name: str
    sort_order: Decimal

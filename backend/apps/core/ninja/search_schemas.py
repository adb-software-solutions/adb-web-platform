from datetime import datetime

from ninja import Schema
from pydantic import Field


class OperationalSearchIn(Schema):
    q: str
    client_id: int | None = None
    per_type: int = 5


class OperationalSearchResultOut(Schema):
    kind: str
    id: int
    title: str
    subtitle: str = ""
    context: str = ""
    href: str
    client_id: int | None = None
    client_name: str | None = None
    updated_at: datetime | None = None


class OperationalSearchGroupOut(Schema):
    kind: str
    label: str
    results: list[OperationalSearchResultOut] = Field(default_factory=list)


class OperationalSearchOut(Schema):
    query: str
    client_id: int | None = None
    client_name: str | None = None
    total_results: int = 0
    groups: list[OperationalSearchGroupOut] = Field(default_factory=list)

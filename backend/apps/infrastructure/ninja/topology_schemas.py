from __future__ import annotations

from ninja import Schema


class TopologyNodeOut(Schema):
    id: int
    name: str
    resource_type: str
    resource_type_label: str
    lifecycle_status: str
    environment: str
    criticality: str
    client_id: int | None
    client_name: str | None
    href: str
    is_root: bool = False


class TopologyEdgeOut(Schema):
    id: int
    source_id: int
    target_id: int
    relationship_type: str
    relationship_label: str
    label: str


class ResourceTopologyOut(Schema):
    root_id: int
    depth: int
    nodes: list[TopologyNodeOut]
    edges: list[TopologyEdgeOut]
    truncated: bool

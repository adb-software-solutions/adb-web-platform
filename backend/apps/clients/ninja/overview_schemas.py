from ninja import Schema


class ClientOverviewItemOut(Schema):
    id: int
    name: str
    company: str
    email: str
    status: str
    contact_count: int
    project_count: int
    active_project_count: int


class ClientOverviewStatsOut(Schema):
    total: int
    active: int
    inactive: int
    archived: int
    contacts: int
    projects: int


class ClientOverviewOut(Schema):
    items: list[ClientOverviewItemOut]
    stats: ClientOverviewStatsOut
    page: int
    page_size: int
    total: int
    total_pages: int

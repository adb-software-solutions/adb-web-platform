from __future__ import annotations

from django.db.models import Q, QuerySet

from apps.access_control.policies import scope_clients_for_user, scope_ticket_queues_for_user
from apps.clients.models import Client, ClientContact, Project
from apps.core.ownership import OwnershipType
from apps.credentials.policies import scope_credentials_for_user
from apps.crm.models import Lead
from apps.infrastructure.policies import scope_infrastructure_resources_for_user
from apps.knowledge_base.models import KnowledgeBaseDocument
from apps.tasks.models import Task
from apps.ticketing.models import Ticket
from authentication.models import User

from .ninja.search_schemas import OperationalSearchGroupOut, OperationalSearchResultOut

GROUP_LABELS = {
    "clients": "Clients",
    "contacts": "Contacts",
    "leads": "Leads",
    "tickets": "Tickets",
    "projects": "Projects",
    "tasks": "Tasks",
    "knowledge": "Knowledge Base",
    "infrastructure": "Infrastructure",
    "credentials": "Credentials",
}


def _owner_context(client: Client | None) -> tuple[int | None, str | None, str]:
    if client is None:
        return None, None, "Internal"
    name = str(client)
    return client.id, name, name


def _client_owned_scope(user: User, client: Client | None) -> Q:
    if client is not None:
        return Q(client=client)
    if user.is_superuser:
        return Q()
    return Q(ownership_type=OwnershipType.INTERNAL) | Q(
        client__in=scope_clients_for_user(user)
    )


def _append_group(
    groups: list[OperationalSearchGroupOut],
    kind: str,
    results: list[OperationalSearchResultOut],
) -> None:
    if not results:
        return
    groups.append(
        OperationalSearchGroupOut(
            kind=kind,
            label=GROUP_LABELS[kind],
            results=results,
        )
    )


def _search_clients(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("clients.view_client"):
        return []
    clients = scope_clients_for_user(user)
    if client is not None:
        clients = clients.filter(id=client.id)
    rows = clients.filter(
        Q(name__icontains=query)
        | Q(company__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
    ).order_by("company", "name", "id")[:limit]
    return [
        OperationalSearchResultOut(
            kind="clients",
            id=row.id,
            title=str(row),
            subtitle=row.email,
            context=row.get_status_display(),
            href=f"/admin/clients/{row.id}",
            client_id=row.id,
            client_name=str(row),
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _search_contacts(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not (
        user.has_perm("clients.view_client")
        and user.has_perm("clients.view_clientcontact")
    ):
        return []
    clients = scope_clients_for_user(user)
    contacts: QuerySet[ClientContact] = ClientContact.objects.select_related(
        "client"
    ).filter(client__in=clients)
    if client is not None:
        contacts = contacts.filter(client=client)
    rows = contacts.filter(
        Q(name__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
        | Q(role__icontains=query)
    ).order_by("name", "id")[:limit]
    return [
        OperationalSearchResultOut(
            kind="contacts",
            id=row.id,
            title=row.name,
            subtitle=" · ".join(part for part in [row.role, row.email] if part),
            context=str(row.client),
            href=f"/admin/clients/{row.client_id}/contacts/{row.id}",
            client_id=row.client_id,
            client_name=str(row.client),
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _search_leads(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("crm.view_lead"):
        return []
    leads = Lead.objects.select_related("brand", "status", "converted_client")
    if client is not None:
        leads = leads.filter(converted_client=client)
    rows = leads.filter(
        Q(name__icontains=query)
        | Q(company__icontains=query)
        | Q(email__icontains=query)
        | Q(phone__icontains=query)
    ).order_by("-updated_at", "-id")[:limit]
    return [
        OperationalSearchResultOut(
            kind="leads",
            id=row.id,
            title=row.company or row.name,
            subtitle=" · ".join(
                part
                for part in [
                    row.name if row.company else "",
                    row.email,
                    row.status.name if row.status else "",
                ]
                if part
            ),
            context=row.brand.name if row.brand else "Lead",
            href=f"/admin/leads/{row.id}",
            client_id=row.converted_client_id,
            client_name=str(row.converted_client) if row.converted_client else None,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _visible_tickets(user: User, client: Client | None) -> QuerySet[Ticket]:
    queues = scope_ticket_queues_for_user(user)
    tickets = Ticket.objects.select_related("queue", "client").filter(queue__in=queues)
    if client is not None:
        return tickets.filter(client=client)
    if user.is_superuser:
        return tickets
    clients = scope_clients_for_user(user)
    return tickets.filter(Q(client__isnull=True) | Q(client__in=clients)).distinct()


def _search_tickets(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("ticketing.view_ticket"):
        return []
    tickets = _visible_tickets(user, client)
    rows = (
        tickets.filter(
            Q(reference__icontains=query)
            | Q(subject__icontains=query)
            | Q(messages__subject__icontains=query)
            | Q(messages__body_text_normalised__icontains=query)
            | Q(messages__sender_name__icontains=query)
            | Q(messages__sender_address__icontains=query)
        )
        .distinct()
        .order_by("-last_message_at", "-created_at")[:limit]
    )
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, context = _owner_context(row.client)
        results.append(
            OperationalSearchResultOut(
                kind="tickets",
                id=row.id,
                title=row.subject,
                subtitle=(
                    f"{row.reference} · {row.queue.name} · {row.get_status_display()}"
                ),
                context=context,
                href=f"/admin/tickets/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def _search_projects(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("clients.view_project"):
        return []
    projects = Project.objects.select_related("client").filter(
        _client_owned_scope(user, client)
    )
    rows = projects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).order_by("-updated_at", "-id")[:limit]
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, context = _owner_context(row.client)
        results.append(
            OperationalSearchResultOut(
                kind="projects",
                id=row.id,
                title=row.name,
                subtitle=row.get_status_display(),
                context=context,
                href=f"/admin/projects/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def _search_tasks(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("tasks.view_task"):
        return []
    tasks = Task.objects.select_related("client", "project", "status").filter(
        _client_owned_scope(user, client)
    )
    rows = (
        tasks.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(task_list__name__icontains=query)
        )
        .distinct()
        .order_by("-updated_at", "-id")[:limit]
    )
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, context = _owner_context(row.client)
        task_context = row.project.name if row.project else context
        results.append(
            OperationalSearchResultOut(
                kind="tasks",
                id=row.id,
                title=row.title,
                subtitle=row.status.name if row.status else "No status",
                context=task_context,
                href=f"/admin/tasks/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def _search_knowledge(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("knowledge_base.view_knowledgebasedocument"):
        return []
    documents = KnowledgeBaseDocument.objects.select_related("client", "section").filter(
        _client_owned_scope(user, client)
    )
    rows = (
        documents.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(content__icontains=query)
            | Q(section__name__icontains=query)
            | Q(tags__name__icontains=query)
        )
        .distinct()
        .order_by("-updated_at", "-id")[:limit]
    )
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, owner = _owner_context(row.client)
        state = "Archived" if row.archived_at else "Current"
        results.append(
            OperationalSearchResultOut(
                kind="knowledge",
                id=row.id,
                title=row.title,
                subtitle=" · ".join(part for part in [row.section.name, state] if part),
                context=owner,
                href=f"/admin/knowledge-base/documents/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def _search_infrastructure(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("infrastructure.view_infrastructureresource"):
        return []
    resources = scope_infrastructure_resources_for_user(user).select_related("client")
    if client is not None:
        resources = resources.filter(client=client)
    rows = (
        resources.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
        )
        .distinct()
        .order_by("name", "id")[:limit]
    )
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, context = _owner_context(row.client)
        results.append(
            OperationalSearchResultOut(
                kind="infrastructure",
                id=row.id,
                title=row.name,
                subtitle=(
                    f"{row.get_resource_type_display()} · "
                    f"{row.get_lifecycle_status_display()}"
                ),
                context=context,
                href=f"/admin/infrastructure/resources/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def _search_credentials(
    user: User,
    query: str,
    client: Client | None,
    limit: int,
) -> list[OperationalSearchResultOut]:
    if not user.has_perm("credentials.view_storedcredential"):
        return []
    credentials = scope_credentials_for_user(user).select_related(
        "client", "credential_type"
    )
    if client is not None:
        credentials = credentials.filter(client=client)
    # Deliberately search only fields already exposed by ordinary Credential metadata
    # views. Legacy plaintext secret fields, encrypted payloads and secret metadata are
    # never part of the search predicate or result projection.
    rows = credentials.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(username__icontains=query)
        | Q(url__icontains=query)
        | Q(credential_type__name__icontains=query)
    ).order_by("name", "id")[:limit]
    results: list[OperationalSearchResultOut] = []
    for row in rows:
        client_id, client_name, context = _owner_context(row.client)
        credential_type = row.credential_type.name if row.credential_type else "Credential"
        results.append(
            OperationalSearchResultOut(
                kind="credentials",
                id=row.id,
                title=row.name,
                subtitle=f"{credential_type} · {row.get_status_display()}",
                context=context,
                href=f"/admin/credentials/{row.id}",
                client_id=client_id,
                client_name=client_name,
                updated_at=row.updated_at,
            )
        )
    return results


def search_operational_records(
    *,
    user: User,
    query: str,
    client: Client | None = None,
    per_type: int = 5,
) -> list[OperationalSearchGroupOut]:
    """Search safe operational metadata inside the caller's existing capabilities/scope."""
    limit = max(1, min(per_type, 10))
    groups: list[OperationalSearchGroupOut] = []
    searches = (
        ("clients", _search_clients),
        ("contacts", _search_contacts),
        ("leads", _search_leads),
        ("tickets", _search_tickets),
        ("projects", _search_projects),
        ("tasks", _search_tasks),
        ("knowledge", _search_knowledge),
        ("infrastructure", _search_infrastructure),
        ("credentials", _search_credentials),
    )
    for kind, search in searches:
        _append_group(groups, kind, search(user, query, client, limit))
    return groups

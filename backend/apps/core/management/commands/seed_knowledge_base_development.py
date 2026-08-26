from __future__ import annotations

import random
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.clients.models import Client
from apps.core.ownership import OwnershipType
from apps.credentials.models import StoredCredential
from apps.infrastructure.models import InfrastructureResource
from apps.knowledge_base.models import (
    KnowledgeBaseCredentialLink,
    KnowledgeBaseDocument,
    KnowledgeBaseResourceLink,
    KnowledgeBaseSection,
    KnowledgeBaseTag,
)
from apps.knowledge_base.services import DocumentWrite, create_document, update_document

DEMO_PREFIX = "[DEMO] KB"


class Command(BaseCommand):
    help = "Populate realistic scoped Knowledge Base development data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--scale", type=int, default=1)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_knowledge_base_development is disabled when DEBUG=False. "
                "Use --force only in a disposable environment."
            )

        scale = max(1, options["scale"])
        rng = random.Random(20260826)
        clients = list(
            Client.objects.filter(company__startswith="[DEMO]").order_by("id")[: max(4, 4 * scale)]
        )
        if not clients:
            raise CommandError("Run seed_development before seeding Knowledge Base data.")

        with transaction.atomic():
            if options["reset"]:
                KnowledgeBaseDocument.objects.filter(title__startswith="[DEMO]").delete()
                KnowledgeBaseSection.objects.filter(name__startswith=DEMO_PREFIX).delete()
                KnowledgeBaseTag.objects.filter(name__startswith="demo-kb-").delete()

            internal_sections = self._seed_internal_sections()
            client_sections = self._seed_client_sections(clients)
            self._seed_internal_documents(rng, internal_sections, scale)
            self._seed_client_documents(rng, clients, client_sections, scale)

        self.stdout.write(
            self.style.SUCCESS(f"Knowledge Base development data ready (scale={scale}).")
        )

    def _seed_internal_sections(self) -> dict[str, KnowledgeBaseSection]:
        operations, _ = KnowledgeBaseSection.objects.update_or_create(
            ownership_type=OwnershipType.INTERNAL,
            client=None,
            parent=None,
            name=f"{DEMO_PREFIX} Operations",
            defaults={"description": "ADB internal operational runbooks.", "order": 10},
        )
        deployments, _ = KnowledgeBaseSection.objects.update_or_create(
            ownership_type=OwnershipType.INTERNAL,
            client=None,
            parent=operations,
            name=f"{DEMO_PREFIX} Deployments",
            defaults={"description": "Deployment and rollback procedures.", "order": 10},
        )
        incidents, _ = KnowledgeBaseSection.objects.update_or_create(
            ownership_type=OwnershipType.INTERNAL,
            client=None,
            parent=operations,
            name=f"{DEMO_PREFIX} Incidents",
            defaults={"description": "Incident response procedures.", "order": 20},
        )
        return {
            "operations": operations,
            "deployments": deployments,
            "incidents": incidents,
        }

    def _seed_client_sections(
        self,
        clients: list[Client],
    ) -> dict[int, dict[str, KnowledgeBaseSection]]:
        result: dict[int, dict[str, KnowledgeBaseSection]] = {}
        for client in clients:
            root, _ = KnowledgeBaseSection.objects.update_or_create(
                ownership_type=OwnershipType.CLIENT,
                client=client,
                parent=None,
                name=f"{DEMO_PREFIX} Operations",
                defaults={
                    "description": "Client-specific operational documentation.",
                    "order": 10,
                },
            )
            hosting, _ = KnowledgeBaseSection.objects.update_or_create(
                ownership_type=OwnershipType.CLIENT,
                client=client,
                parent=root,
                name=f"{DEMO_PREFIX} Hosting",
                defaults={"description": "Hosting and deployment procedures.", "order": 10},
            )
            support, _ = KnowledgeBaseSection.objects.update_or_create(
                ownership_type=OwnershipType.CLIENT,
                client=client,
                parent=root,
                name=f"{DEMO_PREFIX} Support",
                defaults={"description": "Support and troubleshooting notes.", "order": 20},
            )
            result[client.id] = {"root": root, "hosting": hosting, "support": support}
        return result

    def _seed_internal_documents(
        self,
        rng: random.Random,
        sections: dict[str, KnowledgeBaseSection],
        scale: int,
    ) -> None:
        templates = [
            (
                "Production deployment checklist",
                sections["deployments"],
                "A repeatable checklist for production releases.",
                (
                    "# Production deployment\n\n"
                    "## Before release\n\n"
                    "- Confirm CI is green.\n"
                    "- Review migrations.\n"
                    "- Confirm rollback plan.\n\n"
                    "## After release\n\n"
                    "1. Verify health checks.\n"
                    "2. Review logs.\n"
                    "3. Record the deployment outcome.\n"
                ),
            ),
            (
                "Service incident triage",
                sections["incidents"],
                "First-response steps for service incidents.",
                (
                    "# Incident triage\n\n"
                    "> Protect customer data first.\n\n"
                    "1. Confirm impact and scope.\n"
                    "2. Check monitoring and recent changes.\n"
                    "3. Preserve useful logs.\n"
                    "4. Escalate when the recovery path is unclear.\n"
                ),
            ),
        ]
        for copy_index in range(scale):
            for title, section, summary, content in templates:
                self._upsert_document(
                    title=f"{DEMO_PREFIX} {title} {copy_index + 1:02d}",
                    summary=summary,
                    section=section,
                    content=content,
                    ownership_type=OwnershipType.INTERNAL,
                    client=None,
                    rng=rng,
                )

    def _seed_client_documents(
        self,
        rng: random.Random,
        clients: list[Client],
        sections: dict[int, dict[str, KnowledgeBaseSection]],
        scale: int,
    ) -> None:
        for client_index, client in enumerate(clients, start=1):
            client_sections = sections[client.id]
            for article_index in range(1, (3 * scale) + 1):
                section = (
                    client_sections["hosting"] if article_index % 2 else client_sections["support"]
                )
                document = self._upsert_document(
                    title=(
                        f"{DEMO_PREFIX} {client.company.removeprefix('[DEMO]').strip()} "
                        f"runbook {article_index:02d}"
                    ),
                    summary=("Generated client runbook for the Stage 4 Knowledge Base workspace."),
                    section=section,
                    content=(
                        "# Client runbook\n\n"
                        "This article is generated development data.\n\n"
                        "## Procedure\n\n"
                        "1. Confirm the affected service and environment.\n"
                        "2. Review the linked infrastructure resource.\n"
                        "3. Use Credential Vault metadata to locate the correct secret.\n"
                        "4. Record the outcome without copying secrets into this document.\n"
                    ),
                    ownership_type=OwnershipType.CLIENT,
                    client=client,
                    rng=rng,
                )
                self._link_client_context(
                    document,
                    client,
                    client_index + article_index,
                )

    def _upsert_document(
        self,
        *,
        title: str,
        summary: str,
        section: KnowledgeBaseSection,
        content: str,
        ownership_type: str,
        client: Client | None,
        rng: random.Random,
    ) -> KnowledgeBaseDocument:
        document = KnowledgeBaseDocument.objects.filter(title=title).first()
        write = DocumentWrite(
            ownership_type=ownership_type,
            client_id=client.id if client else None,
            title=title,
            summary=summary,
            section=section,
            content=content,
            change_summary="Seed realistic runbook content",
        )
        if document is None:
            document = create_document(write=write, editor=None)
        elif document.archived_at is None:
            document = update_document(document.id, write=write, editor=None)

        tag_names = [
            "demo-kb-runbook",
            "demo-kb-operations",
            rng.choice(
                [
                    "demo-kb-deployment",
                    "demo-kb-support",
                    "demo-kb-incident",
                ]
            ),
        ]
        tags: list[KnowledgeBaseTag] = []
        for name in tag_names:
            tag, _ = KnowledgeBaseTag.objects.get_or_create(
                name=name,
                defaults={"slug": name},
            )
            tags.append(tag)
        document.tags.set(tags)

        if document.versions.count() == 1:
            revised = DocumentWrite(
                ownership_type=ownership_type,
                client_id=client.id if client else None,
                title=title,
                summary=summary,
                section=section,
                content=(
                    f"{content}\n## Verification\n\n"
                    "- Confirm monitoring is healthy before closing the task.\n"
                ),
                change_summary="Add verification section",
            )
            document = update_document(document.id, write=revised, editor=None)
        return document

    def _link_client_context(
        self,
        document: KnowledgeBaseDocument,
        client: Client,
        offset: int,
    ) -> None:
        resources = list(
            InfrastructureResource.objects.filter(
                ownership_type=OwnershipType.CLIENT,
                client=client,
            ).order_by("id")[:3]
        )
        if resources:
            resource = resources[offset % len(resources)]
            resource_link, created = KnowledgeBaseResourceLink.objects.get_or_create(
                document=document,
                resource=resource,
            )
            if created:
                resource_link.full_clean()

        credentials = list(
            StoredCredential.objects.filter(
                ownership_type=OwnershipType.CLIENT,
                client=client,
                status=StoredCredential.Status.ACTIVE,
            ).order_by("id")[:3]
        )
        if credentials:
            credential = credentials[offset % len(credentials)]
            credential_link, created = KnowledgeBaseCredentialLink.objects.get_or_create(
                document=document,
                credential=credential,
            )
            if created:
                credential_link.full_clean()

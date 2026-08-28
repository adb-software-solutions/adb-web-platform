from datetime import date

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from apps.access_control.models import StaffAccessProfile
from apps.clients.models import Client, Project
from apps.core.models import Brand
from apps.core.ownership import OwnershipType
from apps.credentials.models import CredentialType, StoredCredential
from apps.infrastructure.models import InfrastructureResource
from apps.knowledge_base.models import KnowledgeBaseDocument, KnowledgeBaseSection
from apps.tasks.models import Task, TaskStatus
from apps.ticketing.models import Ticket, TicketMessage, TicketQueue
from authentication.models import User


class OperationalSearchAPITests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="search.staff@example.com",
            password="test-password",
            first_name="Search",
            last_name="Staff",
            is_staff=True,
        )
        self.client_a = Client.objects.create(
            name="Allowed Client",
            company="Allowed Client Ltd",
            email="allowed@example.test",
        )
        self.client_b = Client.objects.create(
            name="Hidden Client",
            company="Hidden Client Ltd",
            email="hidden@example.test",
        )
        self.profile = StaffAccessProfile.objects.create(user=self.user)
        self.profile.client_grants.create(client=self.client_a)

        self.brand = Brand.objects.create(
            name="Search Test Brand",
            slug="search-test-brand",
            domain="search-test.example.test",
        )
        self.queue_a = TicketQueue.objects.create(
            name="Allowed Queue",
            key="search-allowed-queue",
            brand=self.brand,
            ordering=1,
        )
        self.queue_b = TicketQueue.objects.create(
            name="Hidden Queue",
            key="search-hidden-queue",
            brand=self.brand,
            ordering=2,
        )
        self.profile.ticket_queue_grants.create(queue=self.queue_a)
        self.client.force_login(self.user)

    def _grant(self, app_label: str, codename: str) -> None:
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app_label, codename=codename)
        )

    @staticmethod
    def _flatten(payload: dict[str, object]) -> list[dict[str, object]]:
        groups = payload["groups"]
        assert isinstance(groups, list)
        return [result for group in groups for result in group["results"]]

    def test_search_respects_client_and_ticket_queue_scope(self) -> None:
        self._grant("clients", "view_project")
        self._grant("tasks", "view_task")
        self._grant("ticketing", "view_ticket")

        allowed_project = Project.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Needle allowed project",
            start_date=date.today(),
        )
        Project.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_b,
            name="Needle hidden project",
            start_date=date.today(),
        )
        internal_project = Project.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            name="Needle internal project",
            start_date=date.today(),
        )
        task_status = TaskStatus.objects.create(name="Search Open", order=1)
        allowed_task = Task.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            title="Needle allowed task",
            status=task_status,
        )
        Task.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_b,
            title="Needle hidden task",
            status=task_status,
        )
        allowed_ticket = Ticket.objects.create(
            brand=self.brand,
            queue=self.queue_a,
            client=self.client_a,
            subject="Needle allowed ticket",
            source=Ticket.Source.MANUAL,
        )
        Ticket.objects.create(
            brand=self.brand,
            queue=self.queue_b,
            client=self.client_a,
            subject="Needle hidden queue ticket",
            source=Ticket.Source.MANUAL,
        )
        Ticket.objects.create(
            brand=self.brand,
            queue=self.queue_a,
            client=self.client_b,
            subject="Needle hidden client ticket",
            source=Ticket.Source.MANUAL,
        )

        response = self.client.get("/api/admin/search", {"q": "needle", "per_type": 10})

        self.assertEqual(response.status_code, 200)
        results = self._flatten(response.json())
        result_keys = {(item["kind"], item["id"]) for item in results}
        self.assertIn(("projects", allowed_project.id), result_keys)
        self.assertIn(("projects", internal_project.id), result_keys)
        self.assertIn(("tasks", allowed_task.id), result_keys)
        self.assertIn(("tickets", allowed_ticket.id), result_keys)
        titles = {str(item["title"]) for item in results}
        self.assertNotIn("Needle hidden project", titles)
        self.assertNotIn("Needle hidden task", titles)
        self.assertNotIn("Needle hidden queue ticket", titles)
        self.assertNotIn("Needle hidden client ticket", titles)

    def test_ticket_message_text_can_find_only_visible_ticket(self) -> None:
        self._grant("ticketing", "view_ticket")
        visible = Ticket.objects.create(
            brand=self.brand,
            queue=self.queue_a,
            client=self.client_a,
            subject="Visible conversation",
            source=Ticket.Source.EMAIL,
        )
        hidden = Ticket.objects.create(
            brand=self.brand,
            queue=self.queue_b,
            client=self.client_a,
            subject="Hidden conversation",
            source=Ticket.Source.EMAIL,
        )
        for ticket in (visible, hidden):
            TicketMessage.objects.create(
                ticket=ticket,
                direction=TicketMessage.Direction.INBOUND,
                sender_address="customer@example.test",
                body_text="Deployment codename aurora-search-marker",
                body_text_normalised="Deployment codename aurora-search-marker",
                sent_or_received_at=timezone.now(),
            )

        response = self.client.get("/api/admin/search", {"q": "aurora-search-marker"})

        self.assertEqual(response.status_code, 200)
        tickets = [
            item
            for item in self._flatten(response.json())
            if item["kind"] == "tickets"
        ]
        self.assertEqual([item["id"] for item in tickets], [visible.id])

    def test_client_context_excludes_internal_and_other_client_records(self) -> None:
        self._grant("clients", "view_client")
        self._grant("clients", "view_project")
        allowed = Project.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Context project allowed",
            start_date=date.today(),
        )
        Project.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            name="Context project internal",
            start_date=date.today(),
        )
        Project.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_b,
            name="Context project hidden",
            start_date=date.today(),
        )

        response = self.client.get(
            "/api/admin/search",
            {"q": "context project", "client_id": self.client_a.id, "per_type": 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["client_id"], self.client_a.id)
        projects = [
            item
            for item in self._flatten(response.json())
            if item["kind"] == "projects"
        ]
        self.assertEqual([item["id"] for item in projects], [allowed.id])

    def test_inaccessible_client_context_returns_not_found(self) -> None:
        self._grant("clients", "view_client")

        response = self.client.get(
            "/api/admin/search",
            {"q": "hidden", "client_id": self.client_b.id},
        )

        self.assertEqual(response.status_code, 404)

    def test_credential_search_never_queries_legacy_secret_fields(self) -> None:
        self._grant("credentials", "view_storedcredential")
        credential_type = CredentialType.objects.create(
            name="Search Login",
            slug="search-login",
        )
        visible = StoredCredential.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Metadata needle credential",
            credential_type=credential_type,
            description="Safe searchable metadata",
            password="legacy-secret-marker",
            encrypted_secret_payload="legacy-secret-marker-encrypted",
        )
        StoredCredential.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_b,
            name="Metadata needle hidden credential",
            credential_type=credential_type,
        )

        metadata_response = self.client.get("/api/admin/search", {"q": "metadata needle"})
        secret_response = self.client.get("/api/admin/search", {"q": "legacy-secret-marker"})

        self.assertEqual(metadata_response.status_code, 200)
        credential_results = [
            item
            for item in self._flatten(metadata_response.json())
            if item["kind"] == "credentials"
        ]
        self.assertEqual([item["id"] for item in credential_results], [visible.id])
        self.assertEqual(secret_response.status_code, 200)
        self.assertFalse(
            any(item["kind"] == "credentials" for item in self._flatten(secret_response.json()))
        )

    def test_knowledge_and_infrastructure_search_obey_capabilities(self) -> None:
        section = KnowledgeBaseSection.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Runbooks",
        )
        document = KnowledgeBaseDocument.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            section=section,
            title="Orion runbook",
            content="Operational orion-marker procedure",
        )
        resource = InfrastructureResource.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Orion API",
            resource_type=InfrastructureResource.ResourceType.API,
        )

        no_permission = self.client.get("/api/admin/search", {"q": "orion"})
        self.assertEqual(no_permission.status_code, 200)
        self.assertEqual(no_permission.json()["groups"], [])

        self._grant("knowledge_base", "view_knowledgebasedocument")
        self._grant("infrastructure", "view_infrastructureresource")
        allowed = self.client.get("/api/admin/search", {"q": "orion"})

        result_keys = {(item["kind"], item["id"]) for item in self._flatten(allowed.json())}
        self.assertIn(("knowledge", document.id), result_keys)
        self.assertIn(("infrastructure", resource.id), result_keys)

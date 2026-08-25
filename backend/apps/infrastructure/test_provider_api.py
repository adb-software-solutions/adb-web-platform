from typing import cast

from django.contrib.auth.models import Permission
from django.http import HttpRequest
from django.test import RequestFactory, TestCase

from apps.access_control.models import ClientAccessGrant, StaffAccessProfile
from apps.clients.models import Client
from apps.core.models import AuditEvent
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import InfrastructureResource, ProviderAccount, ServiceProvider
from apps.infrastructure.ninja.provider_schemas import (
    ProviderAccountCreateIn,
    ProviderAccountDetailOut,
    ProviderAccountPageOut,
    ProviderAccountUpdateIn,
    ServiceProviderCreateIn,
    ServiceProviderDetailOut,
    ServiceProviderPageOut,
)
from apps.infrastructure.ninja.provider_views import (
    archive_provider_account,
    create_provider_account,
    create_service_provider,
    get_provider_account,
    list_provider_accounts,
    list_service_providers,
    update_provider_account,
)
from apps.infrastructure.ninja.resource_schemas import InfrastructureResourceDetailOut
from apps.infrastructure.ninja.resource_views import get_infrastructure_resource
from authentication.models import User


class ProviderApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.client_a = Client.objects.create(
            name="Client A", company="Client A Ltd", email="a@example.test"
        )
        self.client_b = Client.objects.create(
            name="Client B", company="Client B Ltd", email="b@example.test"
        )
        self.provider = ServiceProvider.objects.create(
            name="DigitalOcean",
            slug="digitalocean",
            category=ServiceProvider.Category.CLOUD,
            website_url="https://www.digitalocean.com",
        )
        self.internal_account = self._account("ADB Cloud", OwnershipType.INTERNAL)
        self.client_a_account = self._account("Client A Cloud", OwnershipType.CLIENT, self.client_a)
        self.client_b_account = self._account("Client B Cloud", OwnershipType.CLIENT, self.client_b)

    def _account(
        self,
        name: str,
        ownership_type: str,
        client: Client | None = None,
        lifecycle: str = InfrastructureResource.LifecycleStatus.ACTIVE,
    ) -> ProviderAccount:
        resource = InfrastructureResource.objects.create(
            ownership_type=ownership_type,
            client=client,
            name=name,
            resource_type=InfrastructureResource.ResourceType.PROVIDER_ACCOUNT,
            lifecycle_status=lifecycle,
        )
        return ProviderAccount.objects.create(
            resource=resource,
            provider=self.provider,
            account_identifier=f"acct-{resource.id}",
        )

    def _user(self, email: str, permissions: tuple[str, ...]) -> User:
        user = User.objects.create_user(
            email=email,
            password="test-password",
            first_name="Provider",
            last_name="User",
            is_staff=True,
        )
        for permission in permissions:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="infrastructure",
                    codename=permission,
                )
            )
        return User.objects.get(pk=user.pk)

    def _request(self, user: User, method: str = "get") -> HttpRequest:
        request = getattr(self.factory, method)("/api/admin/infrastructure/provider-accounts")
        request.user = user
        return request

    def test_provider_catalogue_requires_its_own_view_permission(self) -> None:
        user = self._user("accounts-only@example.test", ("view_provideraccount",))

        result = list_service_providers(self._request(user))

        self.assertIsInstance(result, tuple)
        self.assertEqual(cast(tuple[int, dict[str, object]], result)[0], 403)

    def test_provider_catalogue_is_server_filtered_and_paginated(self) -> None:
        user = self._user("providers@example.test", ("view_serviceprovider",))
        ServiceProvider.objects.create(
            name="GitHub",
            slug="github",
            category=ServiceProvider.Category.SOURCE_CONTROL,
            is_active=False,
        )

        current = cast(ServiceProviderPageOut, list_service_providers(self._request(user)))
        inactive = cast(
            ServiceProviderPageOut,
            list_service_providers(self._request(user), active="inactive", page_size=1),
        )

        self.assertEqual([item.name for item in current.items], ["DigitalOcean"])
        self.assertEqual([item.name for item in inactive.items], ["GitHub"])
        self.assertEqual(inactive.page_size, 1)
        self.assertEqual(inactive.total, 1)

    def test_provider_creation_is_permissioned_and_audited(self) -> None:
        user = self._user("provider-create@example.test", ("add_serviceprovider",))

        status, result = create_service_provider(
            self._request(user, "post"),
            ServiceProviderCreateIn(name="Cloudflare", category="cdn"),
        )

        self.assertEqual(status, 201)
        self.assertEqual(cast(ServiceProviderDetailOut, result).slug, "cloudflare")
        event = AuditEvent.objects.get(action="infrastructure.provider_created")
        self.assertEqual(event.actor, user)
        self.assertEqual(event.metadata, {})

    def test_selected_client_scope_hides_other_client_accounts(self) -> None:
        user = self._user(
            "scoped@example.test",
            ("view_provideraccount", "view_infrastructureresource"),
        )
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        result = cast(ProviderAccountPageOut, list_provider_accounts(self._request(user)))

        self.assertSetEqual(
            {item.id for item in result.items},
            {self.internal_account.id, self.client_a_account.id},
        )
        self.assertNotIn(self.client_b_account.id, {item.id for item in result.items})

    def test_provider_accounts_are_current_first(self) -> None:
        archived = self._account(
            "Archived Cloud",
            OwnershipType.INTERNAL,
            lifecycle=InfrastructureResource.LifecycleStatus.ARCHIVED,
        )
        user = self._user(
            "history@example.test",
            ("view_provideraccount", "view_infrastructureresource"),
        )

        current = cast(ProviderAccountPageOut, list_provider_accounts(self._request(user)))
        history = cast(
            ProviderAccountPageOut,
            list_provider_accounts(self._request(user), lifecycle="archived"),
        )

        self.assertNotIn(archived.id, {item.id for item in current.items})
        self.assertEqual([item.id for item in history.items], [archived.id])

    def test_create_client_account_atomically_creates_scoped_resource(self) -> None:
        user = self._user(
            "create@example.test",
            ("add_provideraccount", "add_infrastructureresource"),
        )
        StaffAccessProfile.objects.create(user=user, all_clients=True)

        status, result = create_provider_account(
            self._request(user, "post"),
            ProviderAccountCreateIn(
                name="Client A Cloudflare",
                provider_id=self.provider.id,
                ownership_type="client",
                client_id=self.client_a.id,
                account_identifier="CF-123",
                tenant_id="zone-owner",
                portal_url="https://dash.cloudflare.com",
            ),
        )

        detail = cast(ProviderAccountDetailOut, result)
        self.assertEqual(status, 201)
        self.assertEqual(detail.client_id, self.client_a.id)
        self.assertEqual(detail.account_identifier, "CF-123")
        resource = InfrastructureResource.objects.get(id=detail.resource_id)
        self.assertEqual(resource.resource_type, "provider_account")
        self.assertEqual(resource.created_by, user)
        event = AuditEvent.objects.get(action="infrastructure.provider_account_created")
        self.assertEqual(event.metadata, {"provider_id": self.provider.id})

    def test_client_account_cannot_use_an_unscoped_client(self) -> None:
        user = self._user(
            "restricted-create@example.test",
            ("add_provideraccount", "add_infrastructureresource"),
        )
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        status, _ = create_provider_account(
            self._request(user, "post"),
            ProviderAccountCreateIn(
                name="Forbidden account",
                provider_id=self.provider.id,
                ownership_type="client",
                client_id=self.client_b.id,
            ),
        )

        self.assertEqual(status, 404)
        self.assertFalse(
            ProviderAccount.objects.filter(resource__name="Forbidden account").exists()
        )

    def test_internal_account_rejects_client_reference(self) -> None:
        user = self._user(
            "invalid-owner@example.test",
            ("add_provideraccount", "add_infrastructureresource"),
        )

        status, _ = create_provider_account(
            self._request(user, "post"),
            ProviderAccountCreateIn(
                name="Invalid account",
                provider_id=self.provider.id,
                ownership_type="internal",
                client_id=self.client_a.id,
            ),
        )

        self.assertEqual(status, 400)
        self.assertFalse(ProviderAccount.objects.filter(resource__name="Invalid account").exists())

    def test_update_requires_both_specialist_and_resource_permissions(self) -> None:
        user = self._user(
            "partial-edit@example.test",
            ("change_provideraccount", "view_provideraccount", "view_infrastructureresource"),
        )

        result = update_provider_account(
            self._request(user, "put"),
            self.internal_account.id,
            ProviderAccountUpdateIn(name="Changed"),
        )

        self.assertIsInstance(result, tuple)
        self.assertEqual(cast(tuple[int, dict[str, object]], result)[0], 403)
        self.internal_account.resource.refresh_from_db()
        self.assertEqual(self.internal_account.resource.name, "ADB Cloud")

    def test_archiving_is_explicit_and_audited(self) -> None:
        user = self._user(
            "archive@example.test",
            (
                "delete_provideraccount",
                "view_provideraccount",
                "view_infrastructureresource",
            ),
        )

        result = cast(
            ProviderAccountDetailOut,
            archive_provider_account(self._request(user, "post"), self.internal_account.id),
        )

        self.assertEqual(result.lifecycle_status, "archived")
        self.assertTrue(
            AuditEvent.objects.filter(
                action="infrastructure.provider_account_archived",
                target_id=str(self.internal_account.resource_id),
            ).exists()
        )

    def test_provider_account_detail_is_scope_protected(self) -> None:
        user = self._user(
            "detail-scope@example.test",
            ("view_provideraccount", "view_infrastructureresource"),
        )
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        result = get_provider_account(self._request(user), self.client_b_account.id)

        self.assertIsInstance(result, tuple)
        self.assertEqual(cast(tuple[int, dict[str, object]], result)[0], 404)

    def test_resource_detail_projects_safe_provider_account_metadata(self) -> None:
        self.internal_account.tenant_id = "safe-tenant-id"
        self.internal_account.portal_url = "https://cloud.example.test"
        self.internal_account.save(update_fields=["tenant_id", "portal_url", "updated_at"])
        user = self._user(
            "resource-detail@example.test",
            ("view_infrastructureresource",),
        )

        result = cast(
            InfrastructureResourceDetailOut,
            get_infrastructure_resource(self._request(user), self.internal_account.resource_id),
        )

        self.assertIsNotNone(result.provider_account)
        assert result.provider_account is not None
        self.assertEqual(result.provider_account.provider_name, "DigitalOcean")
        self.assertEqual(result.provider_account.tenant_id, "safe-tenant-id")
        self.assertNotIn("password", result.provider_account.model_dump())
        self.assertNotIn("token", result.provider_account.model_dump())

    def test_provider_account_model_has_no_secret_fields(self) -> None:
        field_names = {field.name for field in ProviderAccount._meta.get_fields()}

        self.assertTrue(
            {"password", "api_key", "token", "secret", "private_key"}.isdisjoint(field_names)
        )

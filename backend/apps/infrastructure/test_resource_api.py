from typing import cast

from django.contrib.auth.models import Permission
from django.http import HttpRequest
from django.test import RequestFactory, TestCase

from apps.access_control.models import ClientAccessGrant, StaffAccessProfile
from apps.clients.models import Client
from apps.core.ownership import OwnershipType
from apps.infrastructure.models import InfrastructureResource, ResourceRelationship
from apps.infrastructure.ninja.resource_schemas import (
    InfrastructureResourceDetailOut,
    InfrastructureResourcePageOut,
)
from apps.infrastructure.ninja.resource_views import (
    get_infrastructure_resource,
    list_infrastructure_resources,
)
from authentication.models import User


class InfrastructureResourceApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.client_a = Client.objects.create(
            name="Client A",
            company="Client A Ltd",
            email="a@example.com",
        )
        self.client_b = Client.objects.create(
            name="Client B",
            company="Client B Ltd",
            email="b@example.com",
        )
        self.internal = InfrastructureResource.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            name="ADB shared server",
            resource_type=InfrastructureResource.ResourceType.SERVER,
        )
        self.resource_a = InfrastructureResource.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_a,
            name="Client A production app",
            resource_type=InfrastructureResource.ResourceType.APPLICATION,
            environment=InfrastructureResource.Environment.PRODUCTION,
        )
        self.resource_b = InfrastructureResource.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.client_b,
            name="Client B website",
            resource_type=InfrastructureResource.ResourceType.WEBSITE,
        )
        self.archived = InfrastructureResource.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            name="Retired server",
            resource_type=InfrastructureResource.ResourceType.SERVER,
            lifecycle_status=InfrastructureResource.LifecycleStatus.ARCHIVED,
        )
        ResourceRelationship.objects.create(
            source_resource=self.resource_a,
            target_resource=self.internal,
            relationship_type=ResourceRelationship.RelationshipType.HOSTED_ON,
        )

    def _user(self, email: str, *, with_permission: bool = True) -> User:
        user = User.objects.create_user(
            email=email,
            password="test-password",
            first_name="Infra",
            last_name="User",
            is_staff=True,
        )
        if with_permission:
            permission = Permission.objects.get(
                content_type__app_label="infrastructure",
                codename="view_infrastructureresource",
            )
            user.user_permissions.add(permission)
        return user

    def _request(self, user: User | None) -> HttpRequest:
        request = self.factory.get("/api/admin/infrastructure/resources")
        request.user = user if user is not None else cast(User, _AnonymousUser())
        return request

    def test_unauthenticated_request_is_rejected(self) -> None:
        result = list_infrastructure_resources(self._request(None))

        self.assertIsInstance(result, tuple)
        status, payload = cast(tuple[int, dict[str, object]], result)
        self.assertEqual(status, 401)
        self.assertEqual(payload["code"], "unauthenticated")

    def test_superuser_sees_all_current_resources(self) -> None:
        user = User.objects.create_superuser(
            email="super-infra@example.com",
            password="test-password",
            first_name="Super",
            last_name="Infra",
        )

        result = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user)),
        )

        self.assertSetEqual(
            {resource.id for resource in result.items},
            {self.internal.id, self.resource_a.id, self.resource_b.id},
        )
        self.assertNotIn(self.archived.id, {resource.id for resource in result.items})

    def test_all_clients_scope_sees_internal_and_all_client_resources(self) -> None:
        user = self._user("all-clients-infra@example.com")
        StaffAccessProfile.objects.create(user=user, all_clients=True)

        result = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user)),
        )

        self.assertSetEqual(
            {resource.id for resource in result.items},
            {self.internal.id, self.resource_a.id, self.resource_b.id},
        )

    def test_selected_client_scope_excludes_other_clients(self) -> None:
        user = self._user("selected-client-infra@example.com")
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        result = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user)),
        )

        self.assertSetEqual(
            {resource.id for resource in result.items},
            {self.internal.id, self.resource_a.id},
        )
        self.assertNotIn(self.resource_b.id, {resource.id for resource in result.items})

    def test_missing_access_profile_still_allows_internal_resources_only(self) -> None:
        user = self._user("internal-only-infra@example.com")

        result = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user)),
        )

        self.assertEqual([resource.id for resource in result.items], [self.internal.id])

    def test_missing_capability_is_forbidden(self) -> None:
        user = self._user("no-infra-permission@example.com", with_permission=False)
        StaffAccessProfile.objects.create(user=user, all_clients=True)

        result = list_infrastructure_resources(self._request(user))

        self.assertIsInstance(result, tuple)
        status, payload = cast(tuple[int, dict[str, object]], result)
        self.assertEqual(status, 403)
        self.assertEqual(payload["code"], "forbidden")

    def test_inaccessible_client_resource_detail_is_not_found(self) -> None:
        user = self._user("client-a-infra@example.com")
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        result = get_infrastructure_resource(self._request(user), self.resource_b.id)

        self.assertIsInstance(result, tuple)
        status, payload = cast(tuple[int, dict[str, object]], result)
        self.assertEqual(status, 404)
        self.assertEqual(payload["code"], "not_found")

    def test_detail_includes_visible_relationships(self) -> None:
        user = self._user("relationship-infra@example.com")
        profile = StaffAccessProfile.objects.create(user=user)
        ClientAccessGrant.objects.create(profile=profile, client=self.client_a)

        result = cast(
            InfrastructureResourceDetailOut,
            get_infrastructure_resource(self._request(user), self.resource_a.id),
        )

        self.assertEqual(result.id, self.resource_a.id)
        self.assertEqual(len(result.relationships), 1)
        relationship = result.relationships[0]
        self.assertEqual(relationship.direction, "outgoing")
        self.assertEqual(relationship.related_resource_id, self.internal.id)

    def test_archived_resources_require_explicit_history_filter(self) -> None:
        user = self._user("history-infra@example.com")

        current = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user)),
        )
        history = cast(
            InfrastructureResourcePageOut,
            list_infrastructure_resources(self._request(user), lifecycle="archived"),
        )

        self.assertNotIn(self.archived.id, {resource.id for resource in current.items})
        self.assertEqual([resource.id for resource in history.items], [self.archived.id])


class _AnonymousUser:
    is_authenticated = False
    is_staff = False
    is_superuser = False

    def has_perm(self, permission: str) -> bool:
        return False

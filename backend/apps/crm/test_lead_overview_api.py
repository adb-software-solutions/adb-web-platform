from typing import cast

from django.http import HttpRequest
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.crm.models import Lead, LeadSource, LeadStatus
from apps.crm.ninja.overview_schemas import LeadOverviewOut
from apps.crm.ninja.overview_views import lead_overview
from authentication.models import User


class LeadOverviewApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            email="lead-overview@example.com",
            password="test-password",
        )
        self.status_new = LeadStatus.objects.create(name="New", order=10)
        self.status_qualified = LeadStatus.objects.create(name="Qualified", order=20)
        self.source = LeadSource.objects.create(name="Referral")

    def _request(self) -> HttpRequest:
        request = self.factory.get("/api/admin/lead-overview")
        request.user = self.user
        return request

    def test_overview_filters_paginates_and_returns_pipeline_stats(self) -> None:
        for index in range(27):
            lead = Lead.objects.create(
                name=f"Lead {index:02d}",
                email=f"lead-{index:02d}@example.com",
                company=f"Company {index:02d}",
                status=self.status_new if index < 15 else self.status_qualified,
                source=self.source,
                assigned_to=self.user if index % 2 else None,
                message="Website redesign enquiry" if index == 0 else "General enquiry",
            )
            if index >= 24:
                lead.converted_at = timezone.now()
                lead.save(update_fields=["converted_at"])

        result = lead_overview(
            self._request(),
            page=2,
            page_size=10,
            status_id=self.status_new.id,
        )
        overview = cast(LeadOverviewOut, result)

        self.assertEqual(overview.stats.total, 27)
        self.assertEqual(overview.stats.converted, 3)
        self.assertEqual(overview.stats.open, 24)
        self.assertEqual(overview.total, 15)
        self.assertEqual(overview.total_pages, 2)
        self.assertEqual(overview.page, 2)
        self.assertEqual(len(overview.items), 5)

        search_result = lead_overview(self._request(), search="redesign")
        search_overview = cast(LeadOverviewOut, search_result)
        self.assertEqual(search_overview.total, 1)
        self.assertEqual(search_overview.items[0].name, "Lead 00")

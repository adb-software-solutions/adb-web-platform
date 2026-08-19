from datetime import timedelta

from django.contrib.auth.models import Permission
from django.http import HttpRequest
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.access_control.models import ClientAccessGrant, StaffAccessProfile
from apps.clients.models import Client, Project
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task, TaskList, TaskStatus
from apps.tasks.ninja.admin_views import (
    complete_task_view,
    create_task,
    create_task_list,
    get_task,
    list_tasks,
)
from apps.tasks.ninja.schemas import TaskIn, TaskListIn, TaskPageOut
from authentication.models import User


class TaskAdminApiTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            email="task-admin@example.com",
            password="test-password",
            first_name="Task",
            last_name="Admin",
        )
        self.primary_client = Client.objects.create(
            name="Primary",
            company="Primary Ltd",
            email="primary@example.com",
        )
        self.other_client = Client.objects.create(
            name="Other",
            company="Other Ltd",
            email="other@example.com",
        )
        self.client_project = Project.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.primary_client,
            name="Client project",
            start_date=timezone.localdate(),
        )
        self.internal_project = Project.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            client=None,
            name="Internal project",
            start_date=timezone.localdate(),
        )
        self.todo = TaskStatus.objects.create(name="To do", color="#38bdf8", order=10)
        self.done = TaskStatus.objects.create(name="Done", color="#22c55e", order=20)

    def _request(self, user: User, method: str = "get") -> HttpRequest:
        request = getattr(self.factory, method)("/api/admin/tasks")
        request.user = user
        return request

    def test_project_context_is_authoritative_for_client_task(self) -> None:
        result = create_task(
            self._request(self.superuser, "post"),
            TaskIn(
                title="Client project task",
                ownership_type="internal",
                project_id=self.client_project.id,
                client_id=None,
                status_id=self.todo.id,
            ),
        )

        self.assertIsInstance(result, tuple)
        status, detail = result
        self.assertEqual(status, 201)
        task = Task.objects.get(id=detail.id)
        self.assertEqual(task.ownership_type, OwnershipType.CLIENT)
        self.assertEqual(task.client, self.primary_client)
        self.assertEqual(task.project, self.client_project)

    def test_internal_project_never_requires_fake_client(self) -> None:
        result = create_task(
            self._request(self.superuser, "post"),
            TaskIn(
                title="Internal project task",
                ownership_type="client",
                project_id=self.internal_project.id,
                client_id=self.primary_client.id,
                status_id=self.todo.id,
            ),
        )

        self.assertIsInstance(result, tuple)
        status, detail = result
        self.assertEqual(status, 201)
        task = Task.objects.get(id=detail.id)
        self.assertEqual(task.ownership_type, OwnershipType.INTERNAL)
        self.assertIsNone(task.client)
        self.assertEqual(task.project, self.internal_project)

    def test_standalone_internal_task_is_first_class(self) -> None:
        result = create_task(
            self._request(self.superuser, "post"),
            TaskIn(
                title="Send monthly invoices",
                ownership_type="internal",
                status_id=self.todo.id,
                due_date=timezone.localdate(),
                recurrence_frequency="monthly",
            ),
        )

        self.assertIsInstance(result, tuple)
        status, detail = result
        self.assertEqual(status, 201)
        task = Task.objects.get(id=detail.id)
        self.assertIsNone(task.client)
        self.assertIsNone(task.project)
        self.assertEqual(task.recurrence_rule, "FREQ=MONTHLY;INTERVAL=1")

    def test_recurring_completion_creates_one_future_occurrence(self) -> None:
        today = timezone.localdate()
        task = Task.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            title="Daily administration",
            status=self.todo,
            due_date=today,
            recurrence_rule="FREQ=DAILY;INTERVAL=1",
            created_by=self.superuser,
        )

        first = complete_task_view(self._request(self.superuser, "post"), task.id)
        second = complete_task_view(self._request(self.superuser, "post"), task.id)

        self.assertNotIsInstance(first, tuple)
        self.assertNotIsInstance(second, tuple)
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(task.status, self.done)
        next_task = task.next_occurrence
        self.assertEqual(next_task.due_date, today + timedelta(days=1))
        self.assertIsNone(next_task.completed_at)
        self.assertEqual(next_task.previous_occurrence, task)
        self.assertEqual(Task.objects.filter(previous_occurrence=task).count(), 1)

    def test_recurring_task_requires_due_date(self) -> None:
        result = create_task(
            self._request(self.superuser, "post"),
            TaskIn(
                title="Invalid recurring task",
                ownership_type="internal",
                recurrence_frequency="daily",
            ),
        )

        self.assertIsInstance(result, tuple)
        status, problem = result
        self.assertEqual(status, 400)
        self.assertEqual(problem["code"], "recurrence_requires_due_date")

    def test_task_list_can_be_internal_without_client(self) -> None:
        result = create_task_list(
            self._request(self.superuser, "post"),
            TaskListIn(
                name="Monthly admin",
                ownership_type="internal",
            ),
        )

        self.assertIsInstance(result, tuple)
        status, detail = result
        self.assertEqual(status, 201)
        task_list = TaskList.objects.get(id=detail.id)
        self.assertEqual(task_list.ownership_type, OwnershipType.INTERNAL)
        self.assertIsNone(task_list.client)

    def test_task_list_inherits_project_context(self) -> None:
        result = create_task_list(
            self._request(self.superuser, "post"),
            TaskListIn(
                name="Delivery",
                ownership_type="internal",
                project_id=self.client_project.id,
            ),
        )

        self.assertIsInstance(result, tuple)
        status, detail = result
        self.assertEqual(status, 201)
        task_list = TaskList.objects.get(id=detail.id)
        self.assertEqual(task_list.ownership_type, OwnershipType.CLIENT)
        self.assertEqual(task_list.client, self.primary_client)
        self.assertEqual(task_list.project, self.client_project)

    def test_client_scope_hides_other_client_tasks_but_keeps_internal(self) -> None:
        user = User.objects.create_user(
            email="task-agent@example.com",
            password="test-password",
            first_name="Task",
            last_name="Agent",
            is_staff=True,
        )
        view_permission = Permission.objects.get(
            content_type__app_label="tasks",
            codename="view_task",
        )
        user.user_permissions.add(view_permission)
        StaffAccessProfile.objects.create(user=user, all_clients=False)
        ClientAccessGrant.objects.create(user=user, client=self.primary_client)

        primary = Task.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.primary_client,
            title="Primary task",
            status=self.todo,
        )
        Task.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.other_client,
            title="Other task",
            status=self.todo,
        )
        internal = Task.objects.create(
            ownership_type=OwnershipType.INTERNAL,
            title="Internal task",
            status=self.todo,
        )

        page = list_tasks(self._request(user))

        self.assertIsInstance(page, TaskPageOut)
        ids = {task.id for task in page.items}
        self.assertIn(primary.id, ids)
        self.assertIn(internal.id, ids)
        self.assertEqual(len(ids), 2)

    def test_inaccessible_task_detail_returns_not_found(self) -> None:
        user = User.objects.create_user(
            email="restricted-agent@example.com",
            password="test-password",
            first_name="Restricted",
            last_name="Agent",
            is_staff=True,
        )
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="tasks",
                codename="view_task",
            )
        )
        StaffAccessProfile.objects.create(user=user, all_clients=False)
        ClientAccessGrant.objects.create(user=user, client=self.primary_client)
        task = Task.objects.create(
            ownership_type=OwnershipType.CLIENT,
            client=self.other_client,
            title="Hidden task",
            status=self.todo,
        )

        result = get_task(self._request(user), task.id)

        self.assertIsInstance(result, tuple)
        status, problem = result
        self.assertEqual(status, 404)
        self.assertEqual(problem["code"], "not_found")

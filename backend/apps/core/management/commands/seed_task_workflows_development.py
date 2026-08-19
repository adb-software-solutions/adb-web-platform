from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.clients.models import Project, TimeEntry
from apps.core.ownership import OwnershipType
from apps.tasks.models import Task, TaskDependency, TaskList, TaskSection

DEMO_PREFIX = "[DEMO]"
PROJECT_BOARD_PREFIX = f"{DEMO_PREFIX} Project"
INTERNAL_TIME_PREFIX = f"{DEMO_PREFIX} Internal workflow time"


class Command(BaseCommand):
    help = "Enrich development data with task boards, relationships and task-linked time."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset generated task-workflow development records before reseeding.",
        )
        parser.add_argument(
            "--scale",
            type=int,
            default=1,
            help="Multiply generated workflow examples. Defaults to 1.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow seeding when DEBUG is disabled in a disposable environment.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_task_workflows_development is disabled when DEBUG=False. "
                "Use --force only in a disposable environment."
            )

        scale = max(1, options["scale"])
        with transaction.atomic():
            if options["reset"]:
                self._reset_workflow_data()

            projects = list(
                Project.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")
            )
            if not projects:
                raise CommandError(
                    "No demo projects found. Run seed_development before this command."
                )

            self._seed_project_boards(projects)
            self._seed_internal_workflows(scale)

        self.stdout.write(
            self.style.SUCCESS(
                f"Task workflow development data ready (scale={scale})."
            )
        )

    def _reset_workflow_data(self) -> None:
        TaskDependency.objects.filter(
            blocked_task__title__startswith=DEMO_PREFIX
        ).delete()
        TaskDependency.objects.filter(
            blocking_task__title__startswith=DEMO_PREFIX
        ).delete()
        TimeEntry.objects.filter(description__startswith=INTERNAL_TIME_PREFIX).delete()
        TimeEntry.objects.filter(
            description__startswith=DEMO_PREFIX,
            task__title__startswith=DEMO_PREFIX,
        ).update(task=None)
        Task.objects.filter(title__startswith=f"{DEMO_PREFIX} Subtask").delete()
        Task.objects.filter(title__startswith=DEMO_PREFIX).update(
            parent_task=None,
            section=None,
            task_list=None,
        )
        TaskSection.objects.filter(task_list__name__startswith=DEMO_PREFIX).delete()
        TaskList.objects.filter(name__startswith=PROJECT_BOARD_PREFIX).delete()

    def _seed_project_boards(self, projects: list[Project]) -> None:
        for project in projects:
            task_list, _ = TaskList.objects.update_or_create(
                project=project,
                name=f"{PROJECT_BOARD_PREFIX} {project.id} delivery",
                defaults={
                    "ownership_type": project.ownership_type,
                    "client": project.client,
                    "description": "Generated project board for task workflow development testing.",
                },
            )
            sections = self._sections(
                task_list,
                ["Backlog", "In progress", "Review", "Done"],
            )
            tasks = list(
                Task.objects.filter(
                    project=project,
                    title__startswith=DEMO_PREFIX,
                    parent_task__isnull=True,
                ).order_by("id")
            )
            if not tasks:
                continue

            for index, task in enumerate(tasks):
                status_name = task.status.name.lower() if task.status else ""
                if status_name == "done":
                    section = sections["Done"]
                    completed_at = task.completed_at or (
                        timezone.now() - timedelta(days=index % 7)
                    )
                elif status_name == "in progress":
                    section = sections["In progress"]
                    completed_at = None
                elif status_name == "blocked":
                    section = sections["Review"]
                    completed_at = None
                else:
                    section = sections["Backlog"]
                    completed_at = None

                task.task_list = task_list
                task.section = section
                task.sort_order = Decimal((index + 1) * 1000)
                task.completed_at = completed_at
                if task.due_date and task.start_date is None:
                    task.start_date = task.due_date - timedelta(days=5 + (index % 8))
                task.save(
                    update_fields=[
                        "task_list",
                        "section",
                        "sort_order",
                        "completed_at",
                        "start_date",
                        "updated_at",
                    ]
                )

            parent = tasks[0]
            Task.objects.update_or_create(
                title=f"{DEMO_PREFIX} Subtask for task {parent.id}",
                defaults={
                    "ownership_type": parent.ownership_type,
                    "client": parent.client,
                    "project": parent.project,
                    "task_list": parent.task_list,
                    "section": parent.section,
                    "parent_task": parent,
                    "status": parent.status,
                    "priority": parent.priority,
                    "start_date": parent.start_date,
                    "due_date": parent.due_date,
                    "sort_order": Decimal(1000),
                    "description": "Generated subtask for task-detail workflow testing.",
                },
            )
            if len(tasks) > 1:
                TaskDependency.objects.get_or_create(
                    blocked_task=tasks[1],
                    blocking_task=tasks[0],
                )

            self._link_project_time(project, tasks)

    def _seed_internal_workflows(self, scale: int) -> None:
        task_lists = list(
            TaskList.objects.filter(
                ownership_type=OwnershipType.INTERNAL,
                project__isnull=True,
                name__startswith=DEMO_PREFIX,
            ).order_by("id")
        )
        tasks = list(
            Task.objects.filter(
                ownership_type=OwnershipType.INTERNAL,
                project__isnull=True,
                title__startswith=f"{DEMO_PREFIX} Internal operations task",
                parent_task__isnull=True,
            ).order_by("id")
        )
        if not task_lists or not tasks:
            return

        sections_by_list = {
            task_list.id: self._sections(task_list, ["To do", "Doing", "Done"])
            for task_list in task_lists
        }
        for index, task in enumerate(tasks):
            task_list = task_lists[index % len(task_lists)]
            sections = sections_by_list[task_list.id]
            status_name = task.status.name.lower() if task.status else ""
            if status_name == "done":
                section = sections["Done"]
                completed_at = task.completed_at or timezone.now()
            elif status_name in {"in progress", "blocked"}:
                section = sections["Doing"]
                completed_at = None
            else:
                section = sections["To do"]
                completed_at = None

            task.task_list = task_list
            task.section = section
            task.sort_order = Decimal((index + 1) * 1000)
            task.completed_at = completed_at
            if task.due_date and task.start_date is None:
                task.start_date = task.due_date - timedelta(days=3 + (index % 5))
            task.save(
                update_fields=[
                    "task_list",
                    "section",
                    "sort_order",
                    "completed_at",
                    "start_date",
                    "updated_at",
                ]
            )

        for index, task in enumerate(tasks[: 12 * scale]):
            TimeEntry.objects.update_or_create(
                description=f"{INTERNAL_TIME_PREFIX} {task.id}",
                defaults={
                    "ownership_type": OwnershipType.INTERNAL,
                    "client": None,
                    "project": None,
                    "task": task,
                    "ticket": None,
                    "date": timezone.localdate() - timedelta(days=index % 14),
                    "duration_hours": Decimal(str([0.5, 1, 1.5, 2][index % 4])),
                    "billable": False,
                    "entry_type": TimeEntry.EntryType.MANUAL,
                },
            )

    def _sections(
        self,
        task_list: TaskList,
        names: list[str],
    ) -> dict[str, TaskSection]:
        sections: dict[str, TaskSection] = {}
        for index, name in enumerate(names, start=1):
            section, _ = TaskSection.objects.update_or_create(
                task_list=task_list,
                name=name,
                defaults={"sort_order": Decimal(index * 1000)},
            )
            sections[name] = section
        return sections

    def _link_project_time(self, project: Project, tasks: list[Task]) -> None:
        entries = list(
            TimeEntry.objects.filter(
                project=project,
                description__startswith=DEMO_PREFIX,
            )
            .order_by("date", "id")[: len(tasks) * 2]
        )
        for index, entry in enumerate(entries):
            entry.task = tasks[index % len(tasks)]
            entry.save()

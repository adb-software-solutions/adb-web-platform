import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("infrastructure", "0007_web_domain_primary_constraints"),
    ]

    operations = [
        migrations.CreateModel(
            name="StorageProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "storage_type",
                    models.CharField(
                        choices=[
                            ("block", "Block storage"),
                            ("object", "Object storage"),
                            ("file", "File storage"),
                            ("volume", "Volume"),
                            ("disk", "Disk"),
                            ("bucket", "Bucket"),
                            ("nas", "NAS"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("provider_resource_id", models.CharField(blank=True, max_length=200)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("capacity_gb", models.PositiveBigIntegerField(blank=True, null=True)),
                ("filesystem", models.CharField(blank=True, max_length=100)),
                ("storage_class", models.CharField(blank=True, max_length=100)),
                ("mount_path", models.CharField(blank=True, max_length=500)),
                ("endpoint_url", models.URLField(blank=True)),
                ("encrypted", models.BooleanField(blank=True, null=True)),
                ("retention_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="storage_profiles",
                        to="infrastructure.provideraccount",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="storage_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
        migrations.CreateModel(
            name="BackupPlanProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "backup_type",
                    models.CharField(
                        choices=[
                            ("snapshot", "Snapshot"),
                            ("file", "File backup"),
                            ("database", "Database backup"),
                            ("image", "Image"),
                            ("volume", "Volume backup"),
                            ("object", "Object backup"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("schedule", models.CharField(blank=True, max_length=200)),
                ("timezone", models.CharField(blank=True, max_length=100)),
                ("retention_days", models.PositiveIntegerField(blank=True, null=True)),
                ("retention_copies", models.PositiveIntegerField(blank=True, null=True)),
                ("encrypted", models.BooleanField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_failure_at", models.DateTimeField(blank=True, null=True)),
                ("last_restore_test_at", models.DateTimeField(blank=True, null=True)),
                ("recovery_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "destination_storage",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backup_plans",
                        to="infrastructure.storageprofile",
                    ),
                ),
                (
                    "provider_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backup_plans",
                        to="infrastructure.provideraccount",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backup_plan_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
        migrations.CreateModel(
            name="BackupSource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("scope", models.CharField(blank=True, max_length=500)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "backup_plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sources",
                        to="infrastructure.backupplanprofile",
                    ),
                ),
                (
                    "source_resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backup_sources",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "backup_plan__resource__name",
                    "source_resource__name",
                    "id",
                ]
            },
        ),
        migrations.AddConstraint(
            model_name="backupsource",
            constraint=models.UniqueConstraint(
                fields=("backup_plan", "source_resource"),
                name="unique_backup_plan_source_resource",
            ),
        ),
        migrations.CreateModel(
            name="ContainerStackProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "orchestrator",
                    models.CharField(
                        choices=[
                            ("docker_compose", "Docker Compose"),
                            ("docker_swarm", "Docker Swarm"),
                            ("nomad", "Nomad"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("project_name", models.CharField(blank=True, max_length=200)),
                ("orchestrator_version", models.CharField(blank=True, max_length=100)),
                ("compose_path", models.CharField(blank=True, max_length=500)),
                ("working_directory", models.CharField(blank=True, max_length=500)),
                ("management_url", models.URLField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "host_resource",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hosted_container_stacks",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="container_stack_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
        migrations.CreateModel(
            name="ContainerService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("image", models.CharField(blank=True, max_length=500)),
                ("replicas", models.PositiveIntegerField(blank=True, null=True)),
                ("ports", models.JSONField(blank=True, default=list)),
                ("volumes", models.JSONField(blank=True, default=list)),
                ("healthcheck", models.CharField(blank=True, max_length=500)),
                ("restart_policy", models.CharField(blank=True, max_length=100)),
                (
                    "environment_notes",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Describe environment/configuration shape only. "
                            "Do not store secret values."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stack",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="services",
                        to="infrastructure.containerstackprofile",
                    ),
                ),
            ],
            options={"ordering": ["stack__resource__name", "name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="containerservice",
            constraint=models.UniqueConstraint(
                fields=("stack", "name"),
                name="unique_container_service_name_per_stack",
            ),
        ),
        migrations.CreateModel(
            name="KubernetesClusterProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("distribution", models.CharField(blank=True, max_length=100)),
                ("version", models.CharField(blank=True, max_length=100)),
                ("api_server_url", models.URLField(blank=True)),
                ("management_url", models.URLField(blank=True)),
                ("provider_cluster_id", models.CharField(blank=True, max_length=200)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("node_count", models.PositiveIntegerField(blank=True, null=True)),
                ("high_availability", models.BooleanField(blank=True, null=True)),
                ("upgrade_channel", models.CharField(blank=True, max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "provider_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kubernetes_clusters",
                        to="infrastructure.provideraccount",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kubernetes_cluster_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
        migrations.CreateModel(
            name="KubernetesNamespaceProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("namespace", models.CharField(max_length=253)),
                ("purpose", models.CharField(blank=True, max_length=255)),
                ("resource_quota_summary", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="namespaces",
                        to="infrastructure.kubernetesclusterprofile",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kubernetes_namespace_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={
                "ordering": ["cluster__resource__name", "namespace", "id"]
            },
        ),
        migrations.AddConstraint(
            model_name="kubernetesnamespaceprofile",
            constraint=models.UniqueConstraint(
                fields=("cluster", "namespace"),
                name="unique_kubernetes_namespace_per_cluster",
            ),
        ),
        migrations.CreateModel(
            name="KubernetesWorkloadProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "workload_kind",
                    models.CharField(
                        choices=[
                            ("deployment", "Deployment"),
                            ("stateful_set", "StatefulSet"),
                            ("daemon_set", "DaemonSet"),
                            ("job", "Job"),
                            ("cron_job", "CronJob"),
                            ("replica_set", "ReplicaSet"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("workload_name", models.CharField(max_length=253)),
                ("replicas_desired", models.PositiveIntegerField(blank=True, null=True)),
                ("image_summary", models.TextField(blank=True)),
                ("selector_summary", models.CharField(blank=True, max_length=500)),
                ("service_account", models.CharField(blank=True, max_length=253)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workloads",
                        to="infrastructure.kubernetesnamespaceprofile",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kubernetes_workload_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "namespace__cluster__resource__name",
                    "workload_name",
                    "id",
                ]
            },
        ),
        migrations.AddConstraint(
            model_name="kubernetesworkloadprofile",
            constraint=models.UniqueConstraint(
                fields=("namespace", "workload_kind", "workload_name"),
                name="unique_kubernetes_workload_per_namespace_kind",
            ),
        ),
        migrations.CreateModel(
            name="KubernetesService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=253)),
                (
                    "service_type",
                    models.CharField(
                        choices=[
                            ("cluster_ip", "ClusterIP"),
                            ("node_port", "NodePort"),
                            ("load_balancer", "LoadBalancer"),
                            ("external_name", "ExternalName"),
                            ("headless", "Headless"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("cluster_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("external_hostname", models.CharField(blank=True, max_length=253)),
                ("ports", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="services",
                        to="infrastructure.kubernetesnamespaceprofile",
                    ),
                ),
                (
                    "workload",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="services",
                        to="infrastructure.kubernetesworkloadprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["namespace__cluster__resource__name", "name", "id"]
            },
        ),
        migrations.AddConstraint(
            model_name="kubernetesservice",
            constraint=models.UniqueConstraint(
                fields=("namespace", "name"),
                name="unique_kubernetes_service_per_namespace",
            ),
        ),
        migrations.CreateModel(
            name="KubernetesIngress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=253)),
                ("ingress_class", models.CharField(blank=True, max_length=100)),
                ("hosts", models.JSONField(blank=True, default=list)),
                ("tls_enabled", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ingresses",
                        to="infrastructure.kubernetesnamespaceprofile",
                    ),
                ),
                (
                    "target_service",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ingresses",
                        to="infrastructure.kubernetesservice",
                    ),
                ),
            ],
            options={
                "ordering": ["namespace__cluster__resource__name", "name", "id"]
            },
        ),
        migrations.AddConstraint(
            model_name="kubernetesingress",
            constraint=models.UniqueConstraint(
                fields=("namespace", "name"),
                name="unique_kubernetes_ingress_per_namespace",
            ),
        ),
        migrations.CreateModel(
            name="HelmRelease",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=253)),
                ("chart", models.CharField(max_length=253)),
                ("chart_version", models.CharField(blank=True, max_length=100)),
                ("app_version", models.CharField(blank=True, max_length=100)),
                ("repository_url", models.URLField(blank=True)),
                ("status", models.CharField(blank=True, max_length=100)),
                (
                    "values_summary",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Non-secret values summary only. Store credentials in the "
                            "Credential Vault."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="helm_releases",
                        to="infrastructure.kubernetesnamespaceprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["namespace__cluster__resource__name", "name", "id"]
            },
        ),
        migrations.AddConstraint(
            model_name="helmrelease",
            constraint=models.UniqueConstraint(
                fields=("namespace", "name"),
                name="unique_helm_release_per_namespace",
            ),
        ),
        migrations.CreateModel(
            name="KubernetesPersistentStorage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=253)),
                ("storage_class", models.CharField(blank=True, max_length=100)),
                ("capacity_gb", models.PositiveBigIntegerField(blank=True, null=True)),
                ("access_modes", models.JSONField(blank=True, default=list)),
                ("volume_name", models.CharField(blank=True, max_length=253)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "backing_storage",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kubernetes_volumes",
                        to="infrastructure.storageprofile",
                    ),
                ),
                (
                    "namespace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="persistent_storage",
                        to="infrastructure.kubernetesnamespaceprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["namespace__cluster__resource__name", "name", "id"]
            },
        ),
        migrations.AddConstraint(
            model_name="kubernetespersistentstorage",
            constraint=models.UniqueConstraint(
                fields=("namespace", "name"),
                name="unique_kubernetes_storage_per_namespace",
            ),
        ),
        migrations.CreateModel(
            name="SystemServiceProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "manager",
                    models.CharField(
                        choices=[
                            ("systemd", "systemd"),
                            ("supervisor", "Supervisor"),
                            ("windows_service", "Windows Service"),
                            ("launchd", "launchd"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("unit_name", models.CharField(max_length=253)),
                ("display_name", models.CharField(blank=True, max_length=253)),
                ("expected_state", models.CharField(blank=True, max_length=100)),
                ("startup_type", models.CharField(blank=True, max_length=100)),
                ("executable", models.CharField(blank=True, max_length=500)),
                ("config_path", models.CharField(blank=True, max_length=500)),
                ("working_directory", models.CharField(blank=True, max_length=500)),
                ("log_location", models.CharField(blank=True, max_length=500)),
                ("restart_policy", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "host_resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="system_services",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="system_service_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["host_resource__name", "unit_name", "id"]},
        ),
        migrations.CreateModel(
            name="ScheduledJobProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "scheduler",
                    models.CharField(
                        choices=[
                            ("cron", "cron"),
                            ("systemd_timer", "systemd timer"),
                            ("celery_beat", "Celery Beat"),
                            ("kubernetes_cron_job", "Kubernetes CronJob"),
                            ("windows_task", "Windows scheduled task"),
                            ("other", "Other"),
                        ],
                        max_length=40,
                    ),
                ),
                ("schedule_expression", models.CharField(blank=True, max_length=255)),
                ("timezone", models.CharField(blank=True, max_length=100)),
                (
                    "command_summary",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "Non-secret command/job summary. Store credentials in the "
                            "Credential Vault."
                        ),
                    ),
                ),
                ("config_path", models.CharField(blank=True, max_length=500)),
                ("working_directory", models.CharField(blank=True, max_length=500)),
                ("run_as", models.CharField(blank=True, max_length=200)),
                ("enabled", models.BooleanField(default=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_failure_at", models.DateTimeField(blank=True, null=True)),
                ("next_run_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "host_resource",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduled_jobs",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
                (
                    "resource",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scheduled_job_profile",
                        to="infrastructure.infrastructureresource",
                    ),
                ),
            ],
            options={"ordering": ["resource__name", "id"]},
        ),
    ]

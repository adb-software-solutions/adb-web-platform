import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("credentials", "0006_alter_storedcredential_credential_type"),
        ("infrastructure", "0007_web_domain_primary_constraints"),
    ]
    operations = [
        migrations.CreateModel(
            name="MonitorCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("check_type", models.CharField(choices=[("icmp", "ICMP/ping"), ("tcp", "TCP port"), ("http", "HTTP/HTTPS"), ("content", "Expected/forbidden content"), ("tls", "TLS certificate"), ("dns", "DNS record"), ("domain_expiry", "Domain registration expiry")], max_length=30)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("critical", "Critical")], default="error", max_length=20)),
                ("enabled", models.BooleanField(db_index=True, default=True)),
                ("target", models.CharField(max_length=500)),
                ("port", models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(65535)])),
                ("expected_value", models.TextField(blank=True)),
                ("forbidden_value", models.TextField(blank=True)),
                ("interval_seconds", models.PositiveIntegerField(default=300, validators=[django.core.validators.MinValueValidator(30)])),
                ("timeout_seconds", models.PositiveIntegerField(default=10, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(300)])),
                ("failure_threshold", models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)])),
                ("recovery_threshold", models.PositiveSmallIntegerField(default=2, validators=[django.core.validators.MinValueValidator(1)])),
                ("expiry_warning_days", models.PositiveSmallIntegerField(default=30, validators=[django.core.validators.MinValueValidator(1)])),
                ("status", models.CharField(choices=[("pending", "Pending"), ("healthy", "Healthy"), ("degraded", "Degraded"), ("failing", "Failing"), ("paused", "Paused")], db_index=True, default="pending", max_length=20)),
                ("consecutive_failures", models.PositiveIntegerField(default=0)),
                ("consecutive_successes", models.PositiveIntegerField(default=0)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("next_run_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("last_message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("credential", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitor_checks", to="credentials.storedcredential")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monitor_checks", to="infrastructure.infrastructureresource")),
            ],
            options={"ordering": ["resource__name", "name", "id"]},
        ),
        migrations.CreateModel(
            name="MonitorResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("outcome", models.CharField(choices=[("success", "Success"), ("failure", "Failure"), ("error", "Execution error")], max_length=20)),
                ("started_at", models.DateTimeField()),
                ("finished_at", models.DateTimeField()),
                ("duration_ms", models.PositiveIntegerField()),
                ("status_code", models.PositiveIntegerField(blank=True, null=True)),
                ("observed_value", models.CharField(blank=True, max_length=500)),
                ("message", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("check", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="monitoring.monitorcheck")),
            ],
            options={"ordering": ["-started_at", "-id"]},
        ),
        migrations.CreateModel(
            name="MonitorIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")], default="open", max_length=20)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("critical", "Critical")], max_length=20)),
                ("opened_at", models.DateTimeField()),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("failure_count", models.PositiveIntegerField(default=1)),
                ("summary", models.CharField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("check", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incidents", to="monitoring.monitorcheck")),
            ],
            options={"ordering": ["status", "-opened_at", "-id"]},
        ),
        migrations.AddConstraint(model_name="monitorcheck", constraint=models.UniqueConstraint(fields=("resource", "name"), name="unique_monitor_check_name_per_resource")),
        migrations.AddIndex(model_name="monitorcheck", index=models.Index(fields=["enabled", "next_run_at"], name="monitor_due_check_idx")),
        migrations.AddIndex(model_name="monitorcheck", index=models.Index(fields=["resource", "status"], name="monitor_resource_status_idx")),
        migrations.AddIndex(model_name="monitorresult", index=models.Index(fields=["check", "-started_at"], name="monitor_result_history_idx")),
        migrations.AddConstraint(model_name="monitorincident", constraint=models.UniqueConstraint(condition=models.Q(("status__in", ["open", "acknowledged"])), fields=("check",), name="unique_active_monitor_incident")),
        migrations.AddIndex(model_name="monitorincident", index=models.Index(fields=["status", "-opened_at"], name="monitor_incident_idx")),
    ]

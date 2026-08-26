from django.contrib import admin

from .models import MonitorCheck, MonitorIncident, MonitorResult


@admin.register(MonitorCheck)
class MonitorCheckAdmin(admin.ModelAdmin):
    list_display = ("name", "resource", "check_type", "status", "severity", "enabled")
    list_filter = ("check_type", "status", "severity", "enabled")
    search_fields = ("name", "target", "resource__name")
    raw_id_fields = ("resource", "credential")


@admin.register(MonitorResult)
class MonitorResultAdmin(admin.ModelAdmin):
    list_display = ("check", "outcome", "started_at", "duration_ms", "status_code")
    list_filter = ("outcome",)
    search_fields = ("check__name", "check__resource__name", "message")
    raw_id_fields = ("check",)


@admin.register(MonitorIncident)
class MonitorIncidentAdmin(admin.ModelAdmin):
    list_display = ("check", "status", "severity", "opened_at", "resolved_at")
    list_filter = ("status", "severity")
    search_fields = ("check__name", "check__resource__name", "summary")
    raw_id_fields = ("check",)

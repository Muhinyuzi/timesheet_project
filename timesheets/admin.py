from django.contrib import admin
from .models import WeeklyTimesheet, DailyEntry


class DailyEntryInline(admin.TabularInline):
    model = DailyEntry
    extra = 0


@admin.register(WeeklyTimesheet)
class WeeklyTimesheetAdmin(admin.ModelAdmin):
    list_display = ("employee", "week_start", "status", "total_hours", "regular_hours", "overtime_hours")
    list_filter = ("status", "week_start")
    search_fields = ("employee__full_name",)
    inlines = [DailyEntryInline]


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    list_display = ("timesheet", "day", "entry_type", "day_shift_hours", "evening_shift_hours", "total_hours")
    list_filter = ("entry_type", "day")
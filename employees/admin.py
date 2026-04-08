from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "job_title", "hourly_rate", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("full_name", "job_title", "user__username", "user__email")
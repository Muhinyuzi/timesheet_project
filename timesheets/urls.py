from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("timesheet/current/", views.current_timesheet, name="current_timesheet"),
    path("timesheet/<int:pk>/", views.timesheet_detail, name="timesheet_detail"),
    path("timesheet/<int:pk>/submit/", views.submit_timesheet, name="submit_timesheet"),
    path("manager/timesheets/", views.manager_timesheets, name="manager_timesheets"),
    path("manager/timesheets/<int:pk>/approve/", views.approve_timesheet, name="approve_timesheet"),
]
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DailyEntryFormSet
from .models import DailyEntry, WeeklyTimesheet


def get_current_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())


def get_employee_or_404(user):
    try:
        return user.employee_profile
    except Exception:
        raise Http404("Aucun profil employé lié à cet utilisateur.")


@login_required
def dashboard(request):
    employee = get_employee_or_404(request.user)

    timesheets = WeeklyTimesheet.objects.filter(employee=employee).order_by("-week_start")

    return render(
        request,
        "timesheets/dashboard.html",
        {
            "employee": employee,
            "timesheets": timesheets,
        },
    )


@login_required
def current_timesheet(request):
    employee = get_employee_or_404(request.user)
    monday = get_current_monday()

    timesheet, _ = WeeklyTimesheet.objects.get_or_create(
        employee=employee,
        week_start=monday,
    )

    return redirect("timesheet_detail", pk=timesheet.pk)


@login_required
def timesheet_detail(request, pk):
    timesheet = get_object_or_404(WeeklyTimesheet, pk=pk)

    user_employee = get_employee_or_404(request.user)
    is_owner = timesheet.employee.user == request.user
    is_manager = user_employee.role == "manager"

    if not is_owner and not is_manager:
        raise Http404("Accès refusé")

    for day in range(7):
        DailyEntry.objects.get_or_create(
            timesheet=timesheet,
            day=day,
            defaults={"entry_type": "work"},
        )

    if request.method == "POST":
        if not is_owner or timesheet.status != "draft":
            raise Http404("Modification interdite")

        formset = DailyEntryFormSet(request.POST, instance=timesheet)
        if formset.is_valid():
            formset.save()
            return redirect("timesheet_detail", pk=pk)
    else:
        formset = DailyEntryFormSet(instance=timesheet)

    return render(
        request,
        "timesheets/timesheet_detail.html",
        {
            "timesheet": timesheet,
            "formset": formset,
        },
    )


@login_required
def submit_timesheet(request, pk):
    if request.method != "POST":
        raise Http404("Méthode non autorisée")

    timesheet = get_object_or_404(WeeklyTimesheet, pk=pk)

    if timesheet.employee.user != request.user:
        raise Http404("Accès refusé")

    if timesheet.status != "draft":
        raise Http404("Cette feuille ne peut plus être soumise")

    if timesheet.total_hours == 0:
        raise Http404("Impossible de soumettre une feuille vide")

    timesheet.status = "submitted"
    timesheet.submitted_at = timezone.now()
    timesheet.save()

    return redirect("timesheet_detail", pk=pk)


@login_required
def manager_timesheets(request):
    employee = get_employee_or_404(request.user)

    if employee.role != "manager":
        raise Http404("Accès refusé")

    timesheets = WeeklyTimesheet.objects.filter(status="submitted").order_by("-week_start")

    return render(
        request,
        "timesheets/manager_list.html",
        {
            "timesheets": timesheets,
        },
    )


@login_required
def approve_timesheet(request, pk):
    if request.method != "POST":
        raise Http404("Méthode non autorisée")

    employee = get_employee_or_404(request.user)
    if employee.role != "manager":
        raise Http404("Accès refusé")

    timesheet = get_object_or_404(WeeklyTimesheet, pk=pk)

    if timesheet.status != "submitted":
        raise Http404("Cette feuille ne peut pas être approuvée")

    timesheet.status = "approved"
    timesheet.save()

    return redirect("manager_timesheets")

@login_required
def reject_timesheet(request, pk):
    if request.method != "POST":
        raise Http404()

    if request.user.employee_profile.role != "manager":
        raise Http404()

    timesheet = get_object_or_404(WeeklyTimesheet, pk=pk)

    if timesheet.status != "submitted":
        raise Http404()

    timesheet.status = "rejected"
    timesheet.save()

    return redirect("manager_timesheets")
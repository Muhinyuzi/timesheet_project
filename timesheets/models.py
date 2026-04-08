from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from employees.models import Employee


class WeeklyTimesheet(models.Model):
    STATUS_CHOICES = [
        ("draft", "Brouillon"),
        ("submitted", "Soumise"),
        ("approved", "Approuvée"),
        ("rejected", "Refusée"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="timesheets"
    )
    week_start = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "week_start"],
                name="unique_employee_week"
            )
        ]
        ordering = ["-week_start"]

    def _q(self, value):
        return Decimal(value).quantize(Decimal("0.01"))

    def clean(self):
        if self.week_start and self.week_start.weekday() != 0:
            raise ValidationError("La semaine doit commencer un lundi.")

    @property
    def total_hours(self):
        total = sum((entry.total_hours for entry in self.entries.all()), Decimal("0.00"))
        return self._q(total)

    @property
    def standard_hours(self):
        return self._q(self.employee.weekly_regular_hours)

    @property
    def regular_hours(self):
        return self._q(min(self.total_hours, self.standard_hours))

    @property
    def extra_hours(self):
        extra = self.total_hours - self.standard_hours
        return self._q(max(extra, Decimal("0.00")))

    @property
    def overtime_hours(self):
        return self.extra_hours

    @property
    def missing_hours(self):
        missing = self.standard_hours - self.total_hours
        return self._q(max(missing, Decimal("0.00")))

    # 1 semaine complète = 1h de vacances
    # et on limite à 1h max par semaine
    @property
    def vacation_hours_earned(self):
        if self.standard_hours == 0:
            return self._q("0.00")

        ratio = self.payable_hours / self.standard_hours
        earned = min(ratio, Decimal("1.00"))
        return self._q(earned)

    # banque consommée cette semaine selon les heures manquantes
    @property
    def bank_hours_used(self):
        previous_balance = self.previous_approved_bank_balance
        return self._q(min(previous_balance, self.missing_hours))

    # banque ajoutée cette semaine selon les heures en surplus
    @property
    def bank_hours_added(self):
        return self.extra_hours

    # variation nette de banque sur cette feuille
    @property
    def bank_hours_delta(self):
        return self._q(self.bank_hours_added - self.bank_hours_used)

    # total payable = heures travaillées + banque utilisée
    @property
    def payable_hours(self):
        result = self.total_hours + self.bank_hours_used
        return self._q(result)

    # feuilles approuvées avant celle-ci, dans l'ordre chrono
    @property
    def previous_approved_timesheets(self):
        return (
            WeeklyTimesheet.objects
            .filter(
                employee=self.employee,
                status="approved",
                week_start__lt=self.week_start
            )
            .order_by("week_start")
        )

    @property
    def previous_approved_bank_balance(self):
        total = sum(
            (timesheet.bank_hours_delta for timesheet in self.previous_approved_timesheets),
            Decimal("0.00")
        )
        return self._q(total)

    @property
    def ending_bank_hours(self):
        result = self.previous_approved_bank_balance + self.bank_hours_delta
        return self._q(result)

    @property
    def previous_approved_vacation_balance(self):
        total = sum(
            (timesheet.vacation_hours_earned for timesheet in self.previous_approved_timesheets),
            Decimal("0.00")
        )
        return self._q(total)

    @property
    def ending_vacation_hours(self):
        return self._q(self.previous_approved_vacation_balance + self.vacation_hours_earned)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.week_start}"


class DailyEntry(models.Model):
    DAY_CHOICES = [
        (0, "Lundi"),
        (1, "Mardi"),
        (2, "Mercredi"),
        (3, "Jeudi"),
        (4, "Vendredi"),
        (5, "Samedi"),
        (6, "Dimanche"),
    ]

    ENTRY_TYPE_CHOICES = [
        ("work", "Travail"),
        ("vacation", "Vacances"),
        ("sick", "Maladie"),
        ("holiday", "Férié"),
        ("unpaid", "Sans solde"),
    ]

    timesheet = models.ForeignKey(
        WeeklyTimesheet,
        on_delete=models.CASCADE,
        related_name="entries"
    )
    day = models.IntegerField(choices=DAY_CHOICES)
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        default="work"
    )

    morning_in = models.TimeField(null=True, blank=True)
    lunch_out = models.TimeField(null=True, blank=True)
    lunch_in = models.TimeField(null=True, blank=True)
    day_shift_out = models.TimeField(null=True, blank=True)

    evening_shift_in = models.TimeField(null=True, blank=True)
    evening_shift_out = models.TimeField(null=True, blank=True)

    note = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["timesheet", "day"],
                name="unique_day_per_timesheet"
            )
        ]
        ordering = ["day"]

    def _hours_between(self, start, end):
        if not start or not end:
            return Decimal("0.00")

        start_dt = datetime.combine(datetime.today(), start)
        end_dt = datetime.combine(datetime.today(), end)

        diff = end_dt - start_dt
        return Decimal(diff.total_seconds() / 3600).quantize(Decimal("0.01"))

    @property
    def day_shift_hours(self):
        if self.entry_type != "work":
            return Decimal("0.00")

        morning = self._hours_between(self.morning_in, self.lunch_out)
        afternoon = self._hours_between(self.lunch_in, self.day_shift_out)
        return (morning + afternoon).quantize(Decimal("0.01"))

    @property
    def evening_shift_hours(self):
        if self.entry_type != "work":
            return Decimal("0.00")

        return self._hours_between(self.evening_shift_in, self.evening_shift_out)

    @property
    def total_hours(self):
        if self.entry_type != "work":
            return Decimal("0.00")

        return (self.day_shift_hours + self.evening_shift_hours).quantize(Decimal("0.01"))

    def clean(self):
        if self.entry_type != "work":
            self.morning_in = None
            self.lunch_out = None
            self.lunch_in = None
            self.day_shift_out = None
            self.evening_shift_in = None
            self.evening_shift_out = None
            return

        day_fields = [self.morning_in, self.lunch_out, self.lunch_in, self.day_shift_out]
        if any(day_fields) and not all(day_fields):
            raise ValidationError("Le shift de jour doit être complet si commencé.")

        if all(day_fields):
            if not (self.morning_in < self.lunch_out < self.lunch_in < self.day_shift_out):
                raise ValidationError("Ordre des heures invalide pour le shift de jour.")

        if (self.evening_shift_in and not self.evening_shift_out) or (
            self.evening_shift_out and not self.evening_shift_in
        ):
            raise ValidationError("Le shift de soir doit avoir une heure d’arrivée et de départ.")

        if self.evening_shift_in and self.evening_shift_out:
            if self.evening_shift_in >= self.evening_shift_out:
                raise ValidationError("Ordre des heures invalide pour le shift de soir.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.timesheet} - jour {self.day}"
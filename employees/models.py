from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Employee(models.Model):
    ROLE_CHOICES = [
        ("employee", "Employé"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile"
    )
    full_name = models.CharField(max_length=150)
    job_title = models.CharField(max_length=100, blank=True)

    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    weekly_regular_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("40.00")
    )

    # Tu peux les garder comme champs informatifs ou cache,
    # mais la vraie logique utilisera les propriétés calculées plus bas.
    vacation_balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00")
    )

    banked_hours_balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.00")
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="employee"
    )

    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def _q(self, value):
        return Decimal(value).quantize(Decimal("0.01"))

    def clean(self):
        if self.manager and self.manager == self:
            raise ValidationError("Un employé ne peut pas être son propre manager.")

    @property
    def approved_timesheets(self):
        return self.timesheets.filter(status="approved").order_by("week_start")

    @property
    def calculated_vacation_balance(self):
        total = sum(
            (timesheet.vacation_hours_earned for timesheet in self.approved_timesheets),
            Decimal("0.00")
        )
        return self._q(total)

    @property
    def calculated_banked_hours_balance(self):
        total = sum(
            (timesheet.bank_hours_delta for timesheet in self.approved_timesheets),
            Decimal("0.00")
        )
        return self._q(total)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
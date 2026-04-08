from django import forms
from django.forms import inlineformset_factory

from .models import DailyEntry, WeeklyTimesheet


class DailyEntryForm(forms.ModelForm):
    is_leave = forms.BooleanField(required=False, label="Congé")

    class Meta:
        model = DailyEntry
        fields = [
            "day",
            "entry_type",
            "morning_in",
            "lunch_out",
            "lunch_in",
            "day_shift_out",
            "evening_shift_in",
            "evening_shift_out",
            "note",
        ]
        widgets = {
            "day": forms.HiddenInput(),
            "entry_type": forms.HiddenInput(),
            "morning_in": forms.TimeInput(attrs={"type": "time"}),
            "lunch_out": forms.TimeInput(attrs={"type": "time"}),
            "lunch_in": forms.TimeInput(attrs={"type": "time"}),
            "day_shift_out": forms.TimeInput(attrs={"type": "time"}),
            "evening_shift_in": forms.TimeInput(attrs={"type": "time"}),
            "evening_shift_out": forms.TimeInput(attrs={"type": "time"}),
            "note": forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        entry_type = self.instance.entry_type if self.instance and self.instance.pk else "work"
        self.fields["is_leave"].initial = entry_type != "work"

    def clean(self):
        cleaned = super().clean()

        is_leave = cleaned.get("is_leave")

        if is_leave:
            cleaned["entry_type"] = "vacation"
            cleaned["morning_in"] = None
            cleaned["lunch_out"] = None
            cleaned["lunch_in"] = None
            cleaned["day_shift_out"] = None
            cleaned["evening_shift_in"] = None
            cleaned["evening_shift_out"] = None
            return cleaned

        cleaned["entry_type"] = "work"

        morning_in = cleaned.get("morning_in")
        lunch_out = cleaned.get("lunch_out")
        lunch_in = cleaned.get("lunch_in")
        day_shift_out = cleaned.get("day_shift_out")

        evening_shift_in = cleaned.get("evening_shift_in")
        evening_shift_out = cleaned.get("evening_shift_out")

        # Validation shift de jour
        day_fields = [morning_in, lunch_out, lunch_in, day_shift_out]

        if any(day_fields) and not all(day_fields):
            raise forms.ValidationError("Le shift de jour doit être complet.")

        if all(day_fields):
            if not (morning_in < lunch_out < lunch_in < day_shift_out):
                raise forms.ValidationError("Ordre des heures invalide pour le shift de jour.")

        # Validation shift de soir
        if (evening_shift_in and not evening_shift_out) or (
            evening_shift_out and not evening_shift_in
        ):
            raise forms.ValidationError("Le shift de soir doit être complet.")

        if evening_shift_in and evening_shift_out:
            if evening_shift_in >= evening_shift_out:
                raise forms.ValidationError("Ordre des heures invalide pour le shift de soir.")

        return cleaned


DailyEntryFormSet = inlineformset_factory(
    WeeklyTimesheet,
    DailyEntry,
    form=DailyEntryForm,
    extra=0,
    max_num=7,
    can_delete=False,
)
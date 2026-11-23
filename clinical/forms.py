from django import forms

from .models import ClinicalLog
from .suggestions import CASES_BY_AREA


class ClinicalLogForm(forms.ModelForm):
    class Meta:
        model = ClinicalLog
        fields = ['hospital', 'duty_date', 'duty_time', 'area', 'case_type']
        widgets = {
            'duty_date': forms.DateInput(attrs={'type': 'date'}),
            'duty_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_area = self.data.get('area') or self.initial.get('area') or getattr(self.instance, 'area', '')
        cases = CASES_BY_AREA.get(selected_area, [])
        self.fields['case_type'].widget = forms.Select(choices=[('', 'Choose a case')] + [(case, case) for case in cases])
        self.fields['case_type'].widget.attrs['data-case-select'] = 'true'

    def clean(self):
        cleaned = super().clean()
        area = cleaned.get('area')
        case_type = cleaned.get('case_type')
        if area and case_type not in CASES_BY_AREA.get(area, []):
            self.add_error('case_type', 'Choose a case from the selected OR or DR list.')
        return cleaned

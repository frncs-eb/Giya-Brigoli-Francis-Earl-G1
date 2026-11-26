from django import forms
from .models import NotificationPreference

class PreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = ('budget', 'schedule', 'task', 'clinical', 'system', 'class_lead_minutes')
        widgets = {'class_lead_minutes': forms.NumberInput(attrs={'min': 15, 'max': 180})}

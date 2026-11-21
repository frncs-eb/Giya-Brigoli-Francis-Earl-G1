from django import forms
from .models import ClassSchedule


class ClassScheduleForm(forms.ModelForm):
    day_of_week = forms.TypedChoiceField(choices=ClassSchedule.DAY_CHOICES, coerce=int, label='Day')

    class Meta:
        model = ClassSchedule
        fields = ['subject_name', 'day_of_week', 'start_time', 'end_time', 'room']
        labels = {'subject_name': 'Subject', 'room': 'Room (optional)'}
        widgets = {'start_time': forms.TimeInput(attrs={'type': 'time'}), 'end_time': forms.TimeInput(attrs={'type': 'time'})}

    def __init__(self, *args, user=None, **kwargs):
        self.user = user or getattr(kwargs.get('instance'), 'user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        start, end, day = data.get('start_time'), data.get('end_time'), data.get('day_of_week')
        if start and end and end <= start:
            self.add_error('end_time', 'End time must be later than start time.')
        if start and end and day and self.user and end > start:
            qs = ClassSchedule.objects.filter(user=self.user, day_of_week=day, start_time__lt=end, end_time__gt=start)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('start_time', 'This class overlaps another class on the same day.')
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.user:
            obj.user = self.user
        if commit:
            obj.save()
        return obj

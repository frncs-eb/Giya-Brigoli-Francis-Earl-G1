from django import forms

from .models import Task


class QuickTaskForm(forms.Form):
    course = forms.CharField(
        max_length=100,
        strip=True,
        error_messages={"required": "Enter a course or subject."},
    )
    title = forms.CharField(
        max_length=150,
        strip=True,
        label="Activity",
        error_messages={"required": "Enter an activity name."},
    )
    due_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    def __init__(self, *args, course_suggestions=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].widget.attrs.update({"list": "course-suggestions", "autocomplete": "off"})

    def clean_course(self):
        course = self.cleaned_data["course"].strip()
        if not course:
            raise forms.ValidationError("Enter a course or subject.")
        return course

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Enter an activity name.")
        return title


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["course", "title", "description", "due_date", "priority", "status"]
        labels = {"title": "Activity", "due_date": "Deadline"}
        widgets = {
            "course": forms.TextInput(attrs={"list": "course-suggestions", "autocomplete": "off"}),
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, course_suggestions=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_date"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["course"].error_messages["required"] = "Enter a course or subject."
        self.fields["title"].error_messages["required"] = "Enter an activity name."
        self.fields["due_date"].error_messages["required"] = "Enter a deadline."

    def clean_course(self):
        course = self.cleaned_data["course"].strip()
        if not course:
            raise forms.ValidationError("Enter a course or subject.")
        return course

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Enter an activity name.")
        return title

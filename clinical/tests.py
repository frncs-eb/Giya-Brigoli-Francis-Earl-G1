from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import ClinicalLogForm
from .models import ClinicalLog


class ClinicalLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='student', password='pass')

    def test_case_dropdown_depends_on_area(self):
        or_form = ClinicalLogForm(initial={'area': ClinicalLog.Area.OR})
        dr_form = ClinicalLogForm(initial={'area': ClinicalLog.Area.DR})
        self.assertIn(('Appendectomy', 'Appendectomy'), or_form.fields['case_type'].widget.choices)
        self.assertNotIn(('Normal spontaneous vaginal delivery', 'Normal spontaneous vaginal delivery'), or_form.fields['case_type'].widget.choices)
        self.assertIn(('Normal spontaneous vaginal delivery', 'Normal spontaneous vaginal delivery'), dr_form.fields['case_type'].widget.choices)

    def test_form_requires_case_for_selected_area(self):
        form = ClinicalLogForm(data={
            'hospital': 'General Hospital', 'duty_date': '2026-03-02', 'duty_time': '08:00',
            'area': 'DR', 'case_type': 'Appendectomy',
        })
        self.assertFalse(form.is_valid())

    def test_log_page_requires_login_and_saves_only_for_user(self):
        url = reverse('clinical:home')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.post(url, {
            'hospital': 'General Hospital', 'duty_date': '2026-03-02', 'duty_time': '08:00',
            'area': 'OR', 'case_type': 'Appendectomy',
        })
        self.assertRedirects(response, url)
        log = ClinicalLog.objects.get()
        self.assertEqual(log.user, self.user)
        self.assertContains(self.client.get(url), 'General Hospital')

    def test_log_list_is_user_scoped(self):
        other = get_user_model().objects.create_user(username='other', password='pass')
        ClinicalLog.objects.create(user=other, hospital='Private Hospital', duty_date=date(2026, 3, 2), duty_time=time(9), area='DR', case_type='Postpartum care')
        self.client.force_login(self.user)
        response = self.client.get(reverse('clinical:home'))
        self.assertNotContains(response, 'Private Hospital')

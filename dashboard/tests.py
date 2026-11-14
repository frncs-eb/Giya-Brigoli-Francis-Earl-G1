from django.test import TestCase


class DashboardAccessTests(TestCase):
    def test_dashboard_requires_login_and_redirects_back(self):
        response = self.client.get('/dashboard/')

        self.assertRedirects(response, '/login/?next=/dashboard/')

    def test_signed_in_user_can_open_dashboard(self):
        self.client.post(
            '/register/',
            {'username': 'giya-user', 'password1': 'StrongPass!234', 'password2': 'StrongPass!234'},
        )

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Giya, giya-user!')

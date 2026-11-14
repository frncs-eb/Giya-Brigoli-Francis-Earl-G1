from django.contrib.auth import get_user_model
from django.test import TestCase


class AccountFlowTests(TestCase):
    def test_registration_creates_user_and_signs_them_in(self):
        response = self.client.post(
            '/register/',
            {'username': 'giya-user', 'password1': 'StrongPass!234', 'password2': 'StrongPass!234'},
        )

        self.assertRedirects(response, '/dashboard/')
        self.assertTrue(get_user_model().objects.filter(username='giya-user').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_and_logout(self):
        user = get_user_model().objects.create_user(
            username='giya-user',
            password='StrongPass!234',
        )

        response = self.client.post(
            '/login/',
            {'username': user.username, 'password': 'StrongPass!234'},
        )
        self.assertRedirects(response, '/dashboard/')
        self.assertIn('_auth_user_id', self.client.session)

        response = self.client.post('/logout/')
        self.assertRedirects(response, '/login/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            '/register/',
            {'username': 'giya-user', 'password1': 'StrongPass!234', 'password2': 'DifferentPass!234'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username='giya-user').exists())

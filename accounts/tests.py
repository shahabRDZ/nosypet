from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SignupFlowTests(TestCase):
    def test_signup_creates_user_and_pet(self):
        res = self.client.post(
            reverse("accounts:signup"),
            data={
                "username": "newuser",
                "email": "n@example.com",
                "password1": "Sup3rSecret!23",
                "password2": "Sup3rSecret!23",
            },
        )
        # Should redirect into the dashboard.
        self.assertEqual(res.status_code, 302)
        u = User.objects.get(username="newuser")
        self.assertEqual(u.email, "n@example.com")
        self.assertTrue(hasattr(u, "pet"))

    def test_signup_rejects_missing_email(self):
        res = self.client.post(
            reverse("accounts:signup"),
            data={
                "username": "noemail",
                "password1": "Sup3rSecret!23",
                "password2": "Sup3rSecret!23",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "This field is required")

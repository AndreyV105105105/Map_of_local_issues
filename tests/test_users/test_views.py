from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from django.core import mail

User = get_user_model()


class UserLoginLogoutProfileTest(TestCase):
    """Тесты входа, выхода и профиля."""

    def setUp(self):
        self.citizen = User.objects.create_user(
            email="citizen@test.com",
            password="pass123",
            first_name="Елена",
            last_name="Соколова",
            role="citizen",
            email_verified=True,
        )
        self.official = User.objects.create_user(
            email="official@test.com",
            password="pass123",
            role="official",
            email_verified=True,
        )

    def test_login_view_invalid_credentials(self):
        response = self.client.post(reverse('users:login'), {
            'username': 'citizen@test.com',
            'password': 'wrong',
        })
        self.assertContains(response, "Неверный email", status_code=200)

    def test_login_view_unverified_email(self):
        unverified = User.objects.create_user(
            email="unverified@test.com",
            password="pass123",
            email_verified=False,
        )
        response = self.client.post(
            reverse('users:login'),
            {
                'username': 'unverified@test.com',
                'password': 'pass123',
            },
            follow=True
        )
        # Пользователь НЕ должен быть залогинен
        self.assertNotIn('_auth_user_id', self.client.session)
        # Должно быть сообщение об ошибке
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(
            any("подтвердите email" in m.lower() for m in messages),
            f"Expected email verification message. Got: {messages}"
        )

    def test_profile_view_access_own(self):
        self.client.login(email="citizen@test.com", password="pass123")
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Соколова Елена")

    def test_profile_view_requires_login(self):
        response = self.client.get(reverse('users:profile'))
        self.assertRedirects(response, f"{reverse('users:login')}?next={reverse('users:profile')}")
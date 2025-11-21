from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from PIL import Image

from users.models import CustomUser
from issues.models import Issue


class RBACIntegrationTest(TestCase):
    """Интеграционные тесты прав доступа (RBAC)."""

    def setUp(self):
        self.citizen = CustomUser.objects.create_user(
            email="citizen@test.com", password="pass", role="citizen", email_verified=True
        )
        self.official = CustomUser.objects.create_user(
            email="official@test.com", password="pass", role="official", email_verified=True
        )

        self.issue = Issue.objects.create(
            title="Тест RBAC",
            description="Проверка прав",
            location=Point(69.0, 61.0),
            reporter=self.citizen,
            status=Issue.STATUS_OPEN,
        )

    def _login(self, user):
        self.client.login(email=user.email, password="pass")

    def test_citizen_can_create_issue(self):
        self._login(self.citizen)
        response = self.client.get(reverse('issues:create_issue'))
        self.assertEqual(response.status_code, 200)

    def test_official_cannot_create_issue(self):
        self._login(self.official)
        response = self.client.get(reverse('issues:create_issue'))
        self.assertRedirects(response, reverse('issues:map'))
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Только граждане" in str(m) for m in messages))

    def test_citizen_can_vote(self):
        self._login(self.citizen)
        response = self.client.post(
            reverse('issues:vote_issue', args=[self.issue.id]),
            {'vote': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_official_cannot_vote(self):
        self._login(self.official)
        response = self.client.post(
            reverse('issues:vote_issue', args=[self.issue.id]),
            {'vote': '1'}
        )
        self.assertEqual(response.status_code, 403)

    def test_official_can_update_status(self):
        self._login(self.official)
        response = self.client.post(
            reverse('issues:update_issue_status', args=[self.issue.id]),
            {'status': Issue.STATUS_IN_PROGRESS}
        )
        self.assertRedirects(response, reverse('issues:issue_detail', args=[self.issue.id]))
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, Issue.STATUS_IN_PROGRESS)
        self.assertEqual(self.issue.assigned_to, self.official)


    def test_official_can_delete_issue(self):
        self._login(self.official)
        response = self.client.post(reverse('issues:delete_issue', args=[self.issue.id]))
        self.assertRedirects(response, reverse('issues:map'))
        self.assertFalse(Issue.objects.filter(id=self.issue.id).exists())

    def test_citizen_cannot_delete_issue(self):
        self._login(self.citizen)
        response = self.client.post(reverse('issues:delete_issue', args=[self.issue.id]))
        self.assertRedirects(response, reverse('issues:map'))
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Только должностные лица" in str(m) for m in messages))
        # Обращение не удалено
        self.assertTrue(Issue.objects.filter(id=self.issue.id).exists())
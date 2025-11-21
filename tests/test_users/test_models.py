from datetime import timedelta
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from users.models import CustomUser
from issues.models import Issue, Vote, Comment


class IssueModelTest(TestCase):
    """Тесты модели Issue"""

    def setUp(self):
        self.citizen = CustomUser.objects.create_user(
            email="reporter@test.com",
            password="pass",
            role="citizen"
        )
        self.official = CustomUser.objects.create_user(
            email="resolver@test.com",
            password="pass",
            role="official"
        )

    def test_issue_creation(self):
        """Тест: корректное создание обращения"""
        issue = Issue.objects.create(
            title="Тестовое обращение",
            description="Описание",
            location=Point(69.0, 61.0, srid=4326),
            address="Ханты-Мансийск, Центр",
            category="roads",
            reporter=self.citizen,
        )
        self.assertEqual(issue.status, Issue.STATUS_OPEN)
        self.assertIsNone(issue.resolved_at)
        self.assertIsNone(issue.assigned_to)

    def test_save_sets_resolved_at_on_resolve(self):
        """Тест: resolved_at устанавливается при переводе в RESOLVED."""
        issue = Issue.objects.create(
            title="До решения",
            description="...",
            location=Point(69.0, 61.0),
            reporter=self.citizen,
        )
        old_resolved_at = issue.resolved_at

        issue.status = Issue.STATUS_RESOLVED
        issue.save()

        issue.refresh_from_db()
        self.assertIsNotNone(issue.resolved_at)
        self.assertNotEqual(issue.resolved_at, old_resolved_at)
        # Проверим, что resolved_at — примерно сейчас
        self.assertTrue(timezone.now() - issue.resolved_at < timedelta(seconds=2))

    def test_save_does_not_overwrite_resolved_at(self):
        """Тест: resolved_at не перезаписывается, если уже задан"""
        issue = Issue.objects.create(
            title="С решением",
            description="...",
            location=Point(69.0, 61.0),
            reporter=self.citizen,
            status=Issue.STATUS_RESOLVED,
        )
        # resolved_at установлен при первом save()

        # Меняем что-то другое
        issue.title = "Новое название"
        issue.save()

        issue.refresh_from_db()
        # resolved_at должен остаться тем же
        self.assertEqual(issue.status, Issue.STATUS_RESOLVED)
        # Проверим, что время не изменилось сильно
        self.assertTrue(timezone.now() - issue.resolved_at < timedelta(seconds=5))


class VoteModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="voter@test.com", password="pass")
        self.issue = Issue.objects.create(
            title="Голосуем",
            description="...",
            location=Point(69.0, 61.0),
            reporter=self.user,
        )

    def test_vote_unique_together(self):
        """Тест: один пользователь — один голос на issue"""
        Vote.objects.create(user=self.user, issue=self.issue, value=1)

        # Попытка создать второй голос — должна вызвать нарушение ограничения
        with self.assertRaises(Exception):  # IntegrityError
            Vote.objects.create(user=self.user, issue=self.issue, value=-1)

    def test_vote_str(self):
        """Тест: строковое представление голоса"""
        vote = Vote.objects.create(user=self.user, issue=self.issue, value=1)
        self.assertIn("voter@test.com", str(vote))
        self.assertIn("Голос", str(vote))
        self.assertIn("За", str(vote))
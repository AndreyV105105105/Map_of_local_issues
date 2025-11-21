from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from users.models import CustomUser
from issues.models import Issue


class HomePageViewTest(TestCase):
    """Тесты главной страницы и About."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="homeuser@test.com", password="pass", email_verified=True
        )
        # Создаём 2 обращения: 1 IN_PROGRESS, 1 RESOLVED
        Issue.objects.create(
            title="В работе",
            description="...",
            location=Point(69.0, 61.0),
            reporter=self.user,
            status=Issue.STATUS_IN_PROGRESS,
        )
        Issue.objects.create(
            title="Решено",
            description="...",
            location=Point(69.1, 61.1),
            reporter=self.user,
            status=Issue.STATUS_RESOLVED,
        )
        # Не считаем OPEN — их нет в подсчёте

    def test_home_view_counts(self):
        """GET / → контекст содержит правильные счётчики."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home_page/home.html')

        context = response.context
        self.assertEqual(context['issues_in_progress'], 1)
        self.assertEqual(context['issues_resolved'], 1)

    def test_about_site(self):
        """GET /about/ → 200, использует шаблон 'about_site.html'."""
        response = self.client.get(reverse('about_site'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about_site.html')
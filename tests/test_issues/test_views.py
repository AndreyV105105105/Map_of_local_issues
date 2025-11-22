from datetime import timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from PIL import Image
import io

from users.models import CustomUser
from issues.models import Issue, IssuePhoto, Vote


class IssueCreationTest(TestCase):
    """Тесты создания обращений (только для citizen)."""

    def setUp(self):
        self.citizen = CustomUser.objects.create_user(
            email="citizen@test.com", password="pass123", role="citizen", email_verified=True
        )
        self.official = CustomUser.objects.create_user(
            email="official@test.com", password="pass123", role="official", email_verified=True
        )

    def test_create_issue_get_renders_form_for_citizen(self):
        """GET /issues/create/ → форма для citizen."""
        self.client.login(email="citizen@test.com", password="pass123")
        response = self.client.get(reverse('issues:create_issue'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'issues/create_issue.html')
        # Дополнительно: проверим, что форма в контексте
        self.assertIn('categories', response.context)

    def test_create_issue_rejects_official(self):
        """GET /issues/create/ для official → messages.error + редирект."""
        self.client.login(email="official@test.com", password="pass123")
        response = self.client.get(reverse('issues:create_issue'), follow=True)
        self.assertRedirects(response, reverse('issues:map'))
        messages = list(response.context['messages'])  # ← context доступен только при follow=True
        self.assertTrue(any("Только граждане" in str(m) for m in messages))

    def test_create_issue_post_success(self):
        """POST: корректные данные → создаёт Issue, редирект на карту."""
        self.client.login(email="citizen@test.com", password="pass123")
        data = {
            'title': 'Яма на дороге',
            'description': 'Опасная для детей',
            'category': 'roads',
            'address': 'ул. Ленина, 5',
            'lat': '61.0066',
            'lon': '69.0223',
        }
        response = self.client.post(reverse('issues:create_issue'), data)
        self.assertRedirects(response, reverse('issues:map'))

        # Проверяем, что Issue создан
        issue = Issue.objects.get(title='Яма на дороге')
        self.assertEqual(issue.reporter, self.citizen)
        self.assertEqual(issue.status, Issue.STATUS_OPEN)
        self.assertEqual(issue.category, 'roads')
        self.assertEqual(issue.address, 'ул. Ленина, 5')
        self.assertAlmostEqual(issue.location.x, 69.0223, places=5)
        self.assertAlmostEqual(issue.location.y, 61.0066, places=5)

    def _create_test_image(self, name):
        """Вспомогательный: создаёт InMemoryUploadedFile JPEG."""
        image = Image.new('RGB', (100, 100), color='blue')
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG')
        buffer.seek(0)
        return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')

    def test_create_issue_with_photos(self):
        self.client.login(email="citizen@test.com", password="pass123")
        image1 = self._create_test_image('photo1.jpg')
        image2 = self._create_test_image('photo2.jpg')
        data = {
            'title': 'Фото-обращение',
            'description': 'С приложением изображений',
            'category': 'garbage',
            'lat': '61.0100',
            'lon': '69.0300',
            'images': [image1, image2]  # ← в data, не files=
        }
        response = self.client.post(
            reverse('issues:create_issue'),
            data,
            format='multipart'  # ← ОБЯЗАТЕЛЬНО
        )
        self.assertRedirects(response, reverse('issues:map'))
        issue = Issue.objects.get(title='Фото-обращение')
        self.assertEqual(issue.photos.count(), 2)

    def test_create_issue_too_many_photos(self):
        self.client.login(email="citizen@test.com", password="pass123")
        data = {
            'title': 'Много фото',
            'description': 'Должно остаться 5',
            'category': 'parks',
            'lat': '61.0',
            'lon': '69.0',
            'images': [self._create_test_image(f'img{i}.jpg') for i in range(7)]
        }
        response = self.client.post(
            reverse('issues:create_issue'),
            data,
            format='multipart'
        )
        self.assertRedirects(response, reverse('issues:map'))
        issue = Issue.objects.get(title='Много фото')
        self.assertEqual(issue.photos.count(), 5)



class IssueVoteTest(TestCase):
    """Тесты голосования (только для citizen)."""

    def setUp(self):
        self.citizen = CustomUser.objects.create_user(
            email="voter@test.com", password="pass", role="citizen", email_verified=True
        )
        self.official = CustomUser.objects.create_user(
            email="admin@test.com", password="pass", role="official", email_verified=True
        )
        self.issue = Issue.objects.create(
            title="Голосуем",
            description="Тест",
            location=Point(69.0, 61.0),
            reporter=self.citizen,
        )

    def test_vote_up_success(self):
        """POST /issues/<id>/vote/ → +1 (гражданин)."""
        self.client.login(email="voter@test.com", password="pass")
        response = self.client.post(
            reverse('issues:vote_issue', args=[self.issue.id]),
            {'vote': '1'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['rating'], 1)
        self.assertEqual(data['user_vote'], 1)

        # Проверяем в БД
        vote = Vote.objects.get(user=self.citizen, issue=self.issue)
        self.assertEqual(vote.value, 1)

    def test_vote_cancel(self):
        """POST с vote=0 → удаляет голос."""
        Vote.objects.create(user=self.citizen, issue=self.issue, value=1)
        self.client.login(email="voter@test.com", password="pass")
        response = self.client.post(
            reverse('issues:vote_issue', args=[self.issue.id]),
            {'vote': '0'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['rating'], 0)
        self.assertIsNone(data['user_vote'])

        # Голос удалён
        self.assertFalse(Vote.objects.filter(user=self.citizen, issue=self.issue).exists())

    def test_vote_official_forbidden(self):
        """Голосование от official → 403 JSON."""
        self.client.login(email="admin@test.com", password="pass")
        response = self.client.post(
            reverse('issues:vote_issue', args=[self.issue.id]),
            {'vote': '1'}
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn("Только граждане", data['error'])


class IssueStatusUpdateTest(TestCase):
    """Тесты изменения статуса (только для official)."""

    def setUp(self):
        self.citizen = CustomUser.objects.create_user(
            email="rep@test.com", password="pass", role="citizen"
        )
        self.official = CustomUser.objects.create_user(
            email="off@test.com", password="pass", role="official", department="ЖКХ"
        )
        self.issue = Issue.objects.create(
            title="Статус",
            description="Тест",
            location=Point(69.0, 61.0),
            reporter=self.citizen,
            status=Issue.STATUS_OPEN,
        )

    def test_official_can_set_in_progress(self):
        """Официальное лицо переводит в IN_PROGRESS → assigned_to = себя."""
        self.client.login(email="off@test.com", password="pass")
        response = self.client.post(
            reverse('issues:update_issue_status', args=[self.issue.id]),
            {'status': Issue.STATUS_IN_PROGRESS}
        )
        self.assertRedirects(response, reverse('issues:issue_detail', args=[self.issue.id]))

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, Issue.STATUS_IN_PROGRESS)
        self.assertEqual(self.issue.assigned_to, self.official)

    def test_official_can_resolve(self):
        """Официальное лицо переводит в RESOLVED → resolved_at устанавливается."""
        self.client.login(email="off@test.com", password="pass")
        old_resolved_at = self.issue.resolved_at

        response = self.client.post(
            reverse('issues:update_issue_status', args=[self.issue.id]),
            {'status': Issue.STATUS_RESOLVED}
        )
        self.assertRedirects(response, reverse('issues:issue_detail', args=[self.issue.id]))

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, Issue.STATUS_RESOLVED)
        self.assertIsNotNone(self.issue.resolved_at)
        self.assertNotEqual(self.issue.resolved_at, old_resolved_at)

    def test_citizen_cannot_update_status(self):
        """Гражданин пытается изменить статус → messages.error."""
        self.client.login(email="rep@test.com", password="pass")
        response = self.client.post(
            reverse('issues:update_issue_status', args=[self.issue.id]),
            {'status': Issue.STATUS_IN_PROGRESS}
        )
        self.assertRedirects(response, reverse('issues:issue_detail', args=[self.issue.id]))

        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("У вас нет прав" in str(m) for m in messages))

        # Статус не изменился
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, Issue.STATUS_OPEN)


class MapAndGeoJSONTest(TestCase):
    """Тесты карты и GeoJSON API."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="mapuser@test.com", password="pass", email_verified=True
        )
        Issue.objects.create(
            title="Яма 1",
            description="...",
            location=Point(69.0223, 61.0066),
            reporter=self.user,
            category="roads",
            status=Issue.STATUS_OPEN,
        )
        Issue.objects.create(
            title="Свет",
            description="...",
            location=Point(69.0300, 61.0100),
            reporter=self.user,
            category="lighting",
            status=Issue.STATUS_IN_PROGRESS,
        )

    def test_map_view(self):
        """GET /issues/map/ → 200, отображает обращения."""
        self.client.login(email="mapuser@test.com", password="pass")
        response = self.client.get(reverse('issues:map'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Яма 1")
        self.assertContains(response, "Свет")

    def test_map_geojson(self):
        """GET /issues/map/geojson/ → валидный GeoJSON FeatureCollection."""
        self.client.login(email="mapuser@test.com", password="pass")
        response = self.client.get(reverse('issues:map_geojson'))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertEqual(len(data['features']), 2)

        feature = data['features'][0]
        self.assertEqual(feature['type'], 'Feature')
        self.assertEqual(feature['geometry']['type'], 'Point')
        self.assertEqual(len(feature['geometry']['coordinates']), 2)  # [lon, lat]
        self.assertIn('properties', feature)
        props = feature['properties']
        self.assertIn('id', props)
        self.assertIn('title', props)
        self.assertIn('status', props)
        self.assertIn('vote_rating', props)

        # Проверим, что URL ведёт на деталь
        detail_url = reverse('issues:issue_detail', args=[props['id']])
        self.assertEqual(props['url'], detail_url)
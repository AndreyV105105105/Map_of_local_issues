from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from users.models import CustomUser


class GeocodingAPITest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="apiuser@test.com", password="pass", email_verified=True)
        self.client.login(email="apiuser@test.com", password="pass")

    # ✅ ИСПРАВЛЕНО: патчим issues.views.geocode_address, а не modules!
    @patch('issues.views.geocode_address')
    def test_geocode_api_success(self, mock_geocode):
        mock_geocode.return_value = (
            "ул. Ленина, 10, Ханты-Мансийск",
            Point(69.0223, 61.0066, srid=4326)
        )
        response = self.client.get(reverse('issues:geocode_api'), {'q': 'ул. Ленина'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['address'], "ул. Ленина, 10, Ханты-Мансийск")

    @patch('issues.views.geocode_address')
    def test_geocode_api_not_found(self, mock_geocode):
        mock_geocode.return_value = None
        response = self.client.get(reverse('issues:geocode_api'), {'q': 'Неизвестная улица 999'})
        self.assertEqual(response.status_code, 404)

    @patch('issues.views.reverse_geocode')
    def test_reverse_geocode_api_success(self, mock_reverse):
        mock_reverse.return_value = "ул. Мира, 5"
        response = self.client.get(reverse('issues:reverse_geocode_api'), {'lat': '61.0066', 'lon': '69.0223'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['address'], "ул. Мира, 5")

    @patch('issues.views.reverse_geocode')
    def test_reverse_geocode_api_failure(self, mock_reverse):
        mock_reverse.return_value = None
        response = self.client.get(reverse('issues:reverse_geocode_api'), {'lat': '999', 'lon': '999'})
        self.assertEqual(response.status_code, 404)  # ← твой view возвращает 404 при None

    @patch('issues.views.search_address')
    def test_search_address_api(self, mock_search):
        mock_search.return_value = [
            {"display_name": "ул. Ленина, 1", "lat": 61.0067, "lon": 69.0224},
        ]
        response = self.client.get(reverse('issues:search_address_api'), {'q': 'Ленина'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['results'][0]['display_name'], "ул. Ленина, 1")

    def test_geocode_api_requires_login(self):
        self.client.logout()
        url = reverse('issues:geocode_api') + '?q=test'
        response = self.client.get(url)
        # ✅ ИСПРАВЛЕНО: редирект на /users/login/, а не /accounts/login/
        self.assertRedirects(response, f"{reverse('users:login')}?next={url}")
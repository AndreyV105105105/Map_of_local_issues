import logging
import requests
from typing import Optional, Tuple, List, Dict
from django.contrib.gis.geos import Point

logger = logging.getLogger(__name__)

# Зеркала Nominatim (работают в РФ по состоянию на 2025)
NOMINATIM_ENDPOINTS = [
    "https://nominatim.openstreetmap.org/search",
    "https://nominatim.sulmax.net/search",
    "https://nominatim.aurora.sherp.ru/search",
]

REVERSE_ENDPOINTS = [
    "https://nominatim.openstreetmap.org/reverse",
    "https://nominatim.sulmax.net/reverse",
    "https://nominatim.aurora.sherp.ru/reverse",
]

HEADERS = {
    "User-Agent": "Khanty-Mansiysk-Issues/1.0 (you@example.com)",
    "Accept-Language": "ru-RU,ru",
}

# Viewbox для Ханты-Мансийска (min_lon, max_lat, max_lon, min_lat)
VIEWBOX = "68.75,61.15,69.30,60.75"

def search_address(query: str, limit: int = 5) -> List[Dict]:
    """
    Поиск с автодополнением → список подсказок.
    """
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "accept-language": "ru",
        "countrycodes": "ru",
        "viewbox": VIEWBOX,
        "bounded": 1,  # искать ТОЛЬКО внутри viewbox
    }

    for endpoint in NOMINATIM_ENDPOINTS:
        try:
            resp = requests.get(endpoint, params=params, headers=HEADERS, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data:
                results.append({
                    "display_name": item.get("display_name", query),
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"]),
                    "address": item.get("address", {})
                })
            return results
        except Exception as e:
            logger.info(f"SearchAddress failed at {endpoint}: {e}")
    return []


def geocode_address(address: str) -> Optional[Tuple[str, Point]]:
    """
    Геокодирование одного адреса → (display_name, Point)
    """
    results = search_address(address, limit=1)
    if results:
        r = results[0]
        return r["display_name"], Point(r["lon"], r["lat"], srid=4326)
    return None


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Обратное геокодирование: (lat, lon) → адрес
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "accept-language": "ru",
        "zoom": 18,  # уточняет детализацию
    }

    for endpoint in REVERSE_ENDPOINTS:
        try:
            resp = requests.get(endpoint, params=params, headers=HEADERS, timeout=8)
            # Не вызываем raise_for_status — некоторые эндпоинты возвращают 200 даже при ошибке
            if resp.status_code != 200:
                logger.info(f"Reverse geocode HTTP {resp.status_code} at {endpoint}")
                continue

            data = resp.json()

            # Nominatim может вернуть {"error": "..."} или пустой dict
            if not data or "error" in data:
                logger.info(f"Reverse geocode returned error/empty at {endpoint}: {data}")
                continue

            # Извлекаем display_name
            display_name = data.get("display_name", "").strip()
            if display_name:
                return display_name

            # Пытаемся собрать адрес вручную
            addr = data.get("address", {})
            parts = []
            # Порядок: улица → дом → район → город → регион
            for key in ["house", "road", "neighbourhood", "suburb", "city", "town", "village", "state"]:
                val = addr.get(key)
                if val and val not in parts:
                    parts.append(val)
            if parts:
                return ", ".join(parts)

            # Последняя надежда — координаты
            return f"Координаты: {lat:.6f}, {lon:.6f}"

        except Exception as e:
            logger.info(f"Reverse geocode failed at {endpoint}: {e}")

    return None
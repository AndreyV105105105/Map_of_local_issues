import logging
import requests
import time
from typing import List, Dict, Optional, Tuple
from django.contrib.gis.geos import Point
from django.core.cache import cache

logger = logging.getLogger(__name__)

# === КОНСТАНТЫ ===
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
REQUEST_TIMEOUT = 8.0  # Nominatim.org медленнее, но стабилен
FAST_TIMEOUT = 5.0
CACHE_TIMEOUT = 7200  # 2 часа — баланс между свежестью и нагрузкой

HEADERS = {
    # Обязательный User-Agent согласно политике Nominatim:
    # https://operations.osmfoundation.org/policies/nominatim/
    "User-Agent": "MapOfLocalIssues/1.0 (ss@yandex.ru)",
    "Accept-Language": "ru-RU,ru",
    "Accept": "application/json",
}

# Viewbox для ХМАО (весь регион)
HMAO_VIEWBOX = "60.5,58.5,80.0,67.0"
# Viewbox для Ханты-Мансийска (точнее)
KHANTY_VIEWBOX = "68.75,60.75,69.30,61.15"


def _assemble_address_from_parts(address: dict) -> str:
    """Собирает человекочитаемый адрес из частей (специфика РФ/ХМАО)"""
    parts = []

    # Порядок: дом → улица → район → город → регион
    ordering = [
        ("house_number", lambda v: f"д. {v}"),
        ("road", lambda v: f"ул. {v}" if not v.startswith("ул.") else v),
        ("pedestrian", lambda v: f"ул. {v}" if not v.startswith("ул.") else v),
        ("neighbourhood", None),
        ("suburb", None),
        ("city_district", None),
        ("city", None),
        ("town", None),
        ("village", None),
        ("state_district", None),
        ("state", None),
    ]

    for key, formatter in ordering:
        val = address.get(key)
        if val and isinstance(val, str) and val.strip():
            clean_val = val.strip()
            if formatter:
                clean_val = formatter(clean_val)
            if clean_val and clean_val.lower() not in ["россия", "рф", "югра"]:
                parts.append(clean_val)

    # Убираем дубли
    unique_parts = []
    for p in parts:
        if p not in unique_parts:
            unique_parts.append(p)

    result = ", ".join(unique_parts[:5])  # Не более 5 компонентов
    return result if result else ""


def _parse_nominatim_result(item: dict) -> Dict:
    """Парсит результат Nominatim в унифицированный формат"""
    try:
        lat = float(item.get("lat", 0))
        lon = float(item.get("lon", 0))
        address = item.get("address", {})

        # 1. Пробуем display_name (но убираем "Россия" в конце)
        display_name = item.get("display_name", "").strip()
        if display_name.endswith(", Россия"):
            display_name = display_name[:-9].strip()

        # 2. Если нет или короткий — собираем вручную
        if not display_name or len(display_name) < 8:
            display_name = _assemble_address_from_parts(address)

        # 3. Если всё ещё нет — fallback с координатами + городом
        if not display_name:
            city = address.get("city") or address.get("town") or address.get("village")
            if city:
                display_name = f"{city}, ХМАО"
            else:
                display_name = f"шир. {lat:.5f}, долг. {lon:.5f}"

        return {
            "display_name": display_name,
            "lat": lat,
            "lon": lon,
            "address": address,
            "osm_id": item.get("osm_id"),
            "osm_type": item.get("osm_type", item.get("class", "")),
        }
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Ошибка парсинга Nominatim-результата: {e}")
        return {
            "display_name": f"шир. {item.get('lat', 0):.5f}, долг. {item.get('lon', 0):.5f}",
            "lat": float(item.get("lat", 0)),
            "lon": float(item.get("lon", 0)),
            "address": {},
            "osm_id": None,
            "osm_type": "error",
        }


def _request_nominatim(endpoint: str, params: dict, timeout: float = REQUEST_TIMEOUT) -> Optional[list]:
    """Единая точка доступа к Nominatim"""
    # Добавляем обязательные параметры
    params.update({
        "format": "json",
        "addressdetails": 1,
        "accept-language": "ru",
        "polygon_geojson": 0,
    })

    cache_key = f"nominatim_{endpoint}_{hash(tuple(sorted(params.items())))}"
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug("💾 Кэш найден для Nominatim")
        return cached

    try:
        start = time.time()
        resp = requests.get(
            f"{NOMINATIM_BASE_URL}{endpoint}",
            params=params,
            headers=HEADERS,
            timeout=timeout
        )
        duration = time.time() - start

        if resp.status_code == 200:
            data = resp.json()
            # Кэшируем успешные результаты
            cache.set(cache_key, data, CACHE_TIMEOUT)
            logger.info(f"✅ Nominatim {endpoint} ответил за {duration:.2f}с")
            return data
        else:
            logger.warning(f"❌ Nominatim {endpoint} вернул {resp.status_code}")
    except requests.exceptions.Timeout:
        logger.warning(f"⏱️ Nominatim {endpoint} превысил таймаут {timeout}с")
    except Exception as e:
        logger.error(f"🔥 Nominatim {endpoint} ошибка: {e}")

    return None


# === ОСНОВНЫЕ ФУНКЦИИ ===

def search_address(query: str, limit: int = 5) -> List[Dict]:
    """
    Поиск адресов по строке.
    Приоритет: с bounded+viewbox → без bounded (если первый пуст).
    """
    if len(query.strip()) < 3:
        return []

    cache_key = f"search_addr_{hash(query.lower())}_{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start_time = time.time()
    params = {
        "q": query,
        "limit": min(limit, 5),
        "countrycodes": "ru",
    }

    results = []

    # 1️⃣ С bounded для ХМАО (приоритет)
    bounded_params = {**params, "viewbox": HMAO_VIEWBOX, "bounded": 1}
    data = _request_nominatim("/search", bounded_params, timeout=FAST_TIMEOUT)
    if data and isinstance(data, list):
        for item in data[:limit]:
            parsed = _parse_nominatim_result(item)
            if parsed["display_name"] and len(parsed["display_name"]) > 5:
                results.append(parsed)

    # 2️⃣ Если мало результатов → пробуем без bounded
    if len(results) < 2:
        data = _request_nominatim("/search", params, timeout=REQUEST_TIMEOUT)
        if data and isinstance(data, list):
            for item in data[:limit]:
                parsed = _parse_nominatim_result(item)
                if parsed["display_name"] and len(parsed["display_name"]) > 5:
                    # Не дублируем уже найденные
                    if not any(r["display_name"] == parsed["display_name"] for r in results):
                        results.append(parsed)

    # 3️⃣ Фолбэк: хотя бы 1 результат
    if not results:
        logger.warning(f"⚠️ Не найдено адресов для '{query}', используем фолбэк")
        results = [{
            "display_name": query if "ханты-мансийск" in query.lower() else f"{query}, Ханты-Мансийск",
            "lat": 61.0034,
            "lon": 69.0132,
            "address": {"city": "Ханты-Мансийск", "state": "ХМАО"},
            "osm_id": None,
            "osm_type": "fallback"
        }]

    duration = time.time() - start_time
    logger.info(f"🔍 '{query}': {len(results)} адресов за {duration:.2f}с")

    # Сохраняем в кэш
    cache.set(cache_key, results, CACHE_TIMEOUT)
    return results[:limit]


def geocode_address(address: str) -> Optional[Tuple[str, Point]]:
    """
    Однозначное геокодирование адреса → (display_name, Point)
    """
    cache_key = f"geocode_simple_{hash(address)}"
    cached = cache.get(cache_key)
    if cached:
        display_name, (lon, lat) = cached
        return display_name, Point(lon, lat, srid=4326)

    results = search_address(address, limit=1)
    if results:
        r = results[0]
        display_name = r["display_name"]
        point = Point(r["lon"], r["lat"], srid=4326)
        # Кэшируем успешный результат дольше
        cache.set(cache_key, (display_name, (r["lon"], r["lat"])), CACHE_TIMEOUT * 3)
        return display_name, point

    return None







def reverse_geocode(lat: float, lon: float) -> str:
    """Обратный геокодинг через Nominatim с соблюдением ToS"""
    cache_key = f"rev_geo_{int(lat * 10000)}_{int(lon * 10000)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {
        "User-Agent": "MapOfLocalIssues-for-HMMAO/1.0 (ss@yandex.ru)",  # ← СВОЙ email!
        "Accept-Language": "ru-RU,ru",
        "Referer": "ss@yandex.ru",  # ← важно: пустой или свой домен
    }

    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
        "zoom": 18,
        "email": "ss@yandex.ru",  # ← рекомендуется
    }

    try:
        # ⏸️ Добавляем задержку, чтобы избежать 403
        time.sleep(0.5)  # ~2 запроса/сек максимум

        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params=params,
            headers=headers,
            timeout=8.0  # Увеличиваем таймаут — сервер медленный
        )

        if resp.status_code == 200:
            data = resp.json()
            display_name = data.get("display_name", "").split(", Россия")[0].strip()

            # Улучшаем адрес для ХМАО
            if "ханты-мансийск" not in display_name.lower():
                display_name = f"{display_name}, Ханты-Мансийск"

            cache.set(cache_key, display_name, 3600 * 24)
            return display_name

        elif resp.status_code == 403:
            logger.error("❌ Nominatim вернул 403: проверьте User-Agent и частоту запросов")
        elif resp.status_code == 429:
            logger.error("⚠️ Слишком много запросов к Nominatim — ограничение 1/сек")

    except requests.exceptions.Timeout:
        logger.warning("⏱️ Nominatim таймаут (8с) — сервер недоступен/медленный")
    except Exception as e:
        logger.error(f"🔥 Ошибка Nominatim: {e}")

    # 🔚 Фолбэк (как у вас — он рабочий!)
    if 68.5 <= lon <= 69.5 and 60.5 <= lat <= 61.5:
        return "Ханты-Мансийск, ХМАО"
    elif 73.0 <= lon <= 74.0 and 61.0 <= lat <= 62.0:
        return "Сургут, ХМАО"
    elif 76.0 <= lon <= 77.0 and 60.5 <= lat <= 61.5:
        return "Нижневартовск, ХМАО"
    else:
        return f"шир. {lat:.5f}, долг. {lon:.5f}, ХМАО"
// Константы и переменные
const MAP_BOUNDS = [
    [68.75, 60.75],
    [69.30, 61.15]
];

let markers = [];
let tempMarker = null;
let map = null;
let searchTimeout = null;
let searchDebounce = null;
let selectedIndex = -1; // Для навигации по результатам поиска

// Получаем флаг роли и цвет маркера из глобальной переменной
// Эти переменные должны быть определены в HTML перед подключением этого скрипта
// window.USER_IS_CITIZEN и window.MARKER_COLOR
const userIsCitizen = window.USER_IS_CITIZEN || false;
const MARKER_COLOR = window.MARKER_COLOR || '#e74c3c'; // Значение по умолчанию, если не передано

// === ИНИЦИАЛИЗАЦИЯ КАРТЫ ===
function initMap() {
    if (!window.maplibregl) {
        console.error('MapLibre GL JS not loaded.');
        return;
    }

    map = new maplibregl.Map({
        container: 'map',
        style: {
            version: 8,
            sources: {
                'osm': {
                    type: 'raster',
                    tiles: ['https://tile.openstreetmap.de/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }
            },
            layers: [{
                id: 'osm-tiles',
                type: 'raster',
                source: 'osm',
                minzoom: 0,
                maxzoom: 19
            }]
        },
        center: [69.0179, 61.0034],
        zoom: 12,
        maxBounds: MAP_BOUNDS
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 100 }), 'bottom-left');

    // Обработка ошибок карты
    map.on('error', (e) => {
        console.error('Map error:', e);
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            mapContainer.innerHTML = `<div class="alert alert-danger p-3">❌ Ошибка карты: ${e.error?.message || 'неизвестная ошибка'}</div>`;
        }
    });

    // Обработчик клика по карте (для граждан)
    if (userIsCitizen) {
        map.on('click', async function(e) {
            // Проверяем, не кликнули ли мы по маркеру или всплывающему окну
            if (e.originalEvent.target.closest('.maplibregl-marker, .maplibregl-popup')) return;

            const lng = e.lngLat.lng;
            const lat = e.lngLat.lat;

            try {
                // Обратное геокодирование
                const resp = await fetch(`/issues/api/reverse-geocode/?lat=${lat}&lon=${lng}`);
                const data = await resp.json();
                let address = data.address || `Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;

                // Удаляем предыдущий временный маркер
                if (tempMarker) {
                    tempMarker.remove();
                    tempMarker = null;
                }

                // Создаем временный маркер
                tempMarker = new maplibregl.Marker({ color: '#3498db' })
                    .setLngLat([lng, lat])
                    .setPopup(new maplibregl.Popup().setText(address))
                    .addTo(map);
                tempMarker.togglePopup();

                // Показываем кнопку "Сообщить о проблеме"
                showReportButton(lat, lng, address);

            } catch (err) {
                console.warn('Reverse geocode failed:', err);
                // В случае ошибки показываем координаты
                const address = `Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;

                if (tempMarker) {
                    tempMarker.remove();
                    tempMarker = null;
                }

                tempMarker = new maplibregl.Marker({ color: '#3498db' })
                    .setLngLat([lng, lat])
                    .setPopup(new maplibregl.Popup().setText(address))
                    .addTo(map);
                tempMarker.togglePopup();

                showReportButton(lat, lng, address);
            }
        });
    }

    // Загрузка маркеров после загрузки стиля
    map.on('load', function() {
        // Загружаем маркеры из начальных данных (передаются из шаблона)
        // Проверяем, определена ли функция, сгенерированная в шаблоне
        if (typeof window.loadInitialMarkersFromTemplate === 'function') {
            window.loadInitialMarkersFromTemplate();
        } else {
            console.warn("Функция window.loadInitialMarkersFromTemplate не найдена. Маркеры не будут загружены при старте.");
        }
    });
}

// === ОБНОВЛЕНИЕ МАРКЕРОВ ПО ФИЛЬТРАМ ===
function updateMapMarkers(filters) {
    // Очищаем старые маркеры
    markers.forEach(marker => marker.remove());
    markers = [];

    fetch(`/issues/map/geojson/?${new URLSearchParams(filters)}`)
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сервера');
            return response.json();
        })
        .then(geojson => {
            geojson.features.forEach(feature => {
                const lng = feature.geometry.coordinates[0];
                const lat = feature.geometry.coordinates[1];
                const props = feature.properties;

                if (!isNaN(lng) && !isNaN(lat)) {
                    const popupContent = `
                        <a href="${props.url}"
                           style="text-decoration: none; color: inherit; font-weight: bold; display: block; margin-bottom: 4px;">
                            ${props.title}
                        </a>
                        <small>
                            Статус: <strong>${props.status_display}</strong><br>
                            Категория: ${props.category_display}<br>
                            Рейтинг: <strong>${props.vote_rating}</strong>
                            ${props.photos_count > 0 ? `<br>📸 ${props.photos_count} фото` : ''}
                        </small>
                    `;

                    const popup = new maplibregl.Popup({
                        closeButton: false,
                        closeOnClick: false,
                        anchor: 'top',
                        offset: [0, -8],
                        maxWidth: '220px'
                    }).setHTML(popupContent);

                    const marker = new maplibregl.Marker({ color: MARKER_COLOR }) // Используем глобальный цвет
                        .setLngLat([lng, lat])
                        .setPopup(popup)
                        .addTo(map);

                    const markerEl = marker.getElement();
                    if (markerEl) {
                        markerEl.addEventListener('mouseenter', (e) => {
                            e.stopPropagation();
                            popup.addTo(map);
                        });
                        markerEl.addEventListener('mouseleave', (e) => {
                            e.stopPropagation();
                            if (popup.isOpen()) popup.remove();
                        });

                        markerEl.addEventListener('click', (e) => {
                            e.stopPropagation();
                            window.location.href = props.url;
                        });
                    }

                    markers.push(marker);
                }
            });
        })
        .catch(error => {
            console.error('Error updating map markers:', error);
            // В случае ошибки при загрузке GeoJSON, отображаем начальные маркеры
            // Проверяем, определена ли функция, сгенерированная в шаблоне для ошибки
            if (typeof window.loadInitialMarkersOnError === 'function') {
                window.loadInitialMarkersOnError();
            } else {
                 console.error("Функция window.loadInitialMarkersOnError не определена в шаблоне.");
                 // Fallback: попробовать перезагрузить страницу или показать ошибку
                 // location.reload();
            }
        });
}

// === ЗАГРУЗКА СПИСКА ОБРАЩЕНИЙ С ФИЛЬТРАМИ ===
function loadIssuesWithFilters(filters) {
    const url = new URL(window.location.href);
    Object.entries(filters).forEach(([key, value]) => {
        value ? url.searchParams.set(key, value) : url.searchParams.delete(key);
    });
    history.pushState({}, '', url);

    const btn = document.querySelector('#filter-form button[type="submit"]');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Применить';
    }

    fetch(`/issues/map/?${new URLSearchParams(filters)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(response => {
        if (!response.ok) throw new Error('Ошибка сервера');
        return response.text();
    })
    .then(html => {
        const container = document.getElementById('issues-container');
        if (container) {
            container.innerHTML = html;
        }
        // Обновляем маркеры на карте
        updateMapMarkers(filters);
    })
    .catch(error => {
        console.error('Error loading filtered issues:', error);
        alert('Ошибка при загрузке данных. Попробуйте позже.');
    })
    .finally(() => {
        const btn = document.querySelector('#filter-form button[type="submit"]');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = 'Применить';
        }
    });
}

// === ФИЛЬТРАЦИЯ (обработка формы и бейджей) ===
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация карты
    initMap();

    // Обработчик формы фильтрации
    document.getElementById('filter-form')?.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const filters = Object.fromEntries(formData.entries());
        loadIssuesWithFilters(filters);
    });

    // Обработчик сброса фильтров
    document.getElementById('reset-filters')?.addEventListener('click', function() {
        ['category-filter', 'status-filter', 'search-filter', 'sort-filter'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = el.id === 'sort-filter' ? '-created_at' : '';
        });
        document.querySelectorAll('.filter-badge').forEach(el => el.remove());

        const formData = new FormData(document.getElementById('filter-form'));
        loadIssuesWithFilters(Object.fromEntries(formData.entries()));
    });

    // Обработчик клика по бейджу фильтра
    document.querySelectorAll('.filter-badge').forEach(badge => {
        badge.addEventListener('click', function() {
            const filterType = this.dataset.filter;
            const filterElement = document.getElementById(filterType + '-filter');
            if (filterElement) filterElement.value = '';
            this.remove();
            const formData = new FormData(document.getElementById('filter-form'));
            loadIssuesWithFilters(Object.fromEntries(formData.entries()));
        });
    });

    // Обработчик ввода в поле поиска (с задержкой)
    document.getElementById('search-filter')?.addEventListener('input', function(e) {
        clearTimeout(searchTimeout);
        if (e.target.value.length > 2 || e.target.value.length === 0) {
            searchTimeout = setTimeout(() => {
                const formData = new FormData(document.getElementById('filter-form'));
                loadIssuesWithFilters(Object.fromEntries(formData.entries()));
            }, 500);
        }
    });
});

// === АВТОДОПОЛНЕНИЕ ПО АДРЕСУ ===
function clearSearchResults() {
    const div = document.getElementById('map-search-results');
    if (div) {
        div.innerHTML = '';
        div.style.display = 'none';
    }
    selectedIndex = -1; // Сбрасываем индекс при очистке
}

function showSearchResults(results) {
    selectedIndex = -1; // Сбрасываем индекс при отображении новых результатов
    const div = document.getElementById('map-search-results');
    if (!div) return;
    div.innerHTML = '';
    if (!results || results.length === 0) {
        // Показываем сообщение "не найдено"
        div.innerHTML = `
            <div class="map-search-no-results">
                <div class="map-search-no-results-icon">📍</div>
                <div class="map-search-no-results-text">Адреса не найдены<br><small style="font-size: 12px; opacity: 0.7;">Попробуйте другой запрос</small></div>
            </div>
        `;
        div.style.display = 'block';
        return;
    }

    // Заголовок с количеством результатов (как в старом шаблоне)
    const header = document.createElement('div');
    header.className = 'map-search-results-header';
    header.innerHTML = `
        <span>📍 Найдено адресов</span>
        <span class="map-search-results-count">${results.length}</span>
    `;
    div.appendChild(header);

    results.forEach((r, index) => {
        const item = document.createElement('div');
        item.className = 'map-search-result-item';
        if (index === 0) item.classList.add('active'); // Первый элемент активен по умолчанию

        // Извлекаем компоненты адреса (как в старом шаблоне)
        const addr = r.address || {};
        const road = addr.road || '';
        const houseNumber = addr.house_number || '';
        const city = addr.city || addr.town || addr.municipality || '';
        const district = addr.suburb || addr.quarter || addr.neighbourhood || '';
        const postcode = addr.postcode || '';

        // Формируем основной адрес
        let mainAddress = '';
        if (road) {
            mainAddress = road;
            if (houseNumber) mainAddress += `, ${houseNumber}`;
        } else {
            // Если нет названия улицы, берем первую часть display_name
            mainAddress = r.display_name.split(',')[0] || r.display_name;
        }

        // Формируем детали
        const details = [];
        if (district) details.push({ icon: '🏘️', text: district });
        if (city && city !== district) details.push({ icon: '🏙️', text: city });
        if (postcode) details.push({ icon: '📮', text: postcode });

        // Создаем структурированный HTML (как в старом шаблоне)
        item.innerHTML = `
            <div class="map-search-result-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                </svg>
            </div>
            <div class="map-search-result-content">
                <div class="map-search-result-main">${mainAddress}</div>
                ${details.length > 0 ? `
                    <div class="map-search-result-details">
                        ${details.map(d => `
                            <span class="map-search-result-detail">
                                <span class="map-search-result-detail-icon">${d.icon}</span>
                                <span>${d.text}</span>
                            </span>
                        `).join('')}
                    </div>
                ` : ''}
                <div class="map-search-result-address">${r.display_name}</div>
            </div>
        `;

        item.onclick = () => {
            const lat = parseFloat(r.lat);
            const lon = parseFloat(r.lon);
            const addr = r.display_name;
            if (isNaN(lat) || isNaN(lon)) {
                console.error("Invalid coordinates from search result:", r);
                return;
            }
            map.flyTo({ center: [lon, lat], zoom: 16 });
            clearSearchResults();
            if (tempMarker) {
                tempMarker.remove();
                tempMarker = null;
            }
            tempMarker = new maplibregl.Marker({ color: '#3498db' })
                .setLngLat([lon, lat])
                .setPopup(new maplibregl.Popup().setText(addr))
                .addTo(map);
            tempMarker.togglePopup();
            if (userIsCitizen) {
                showReportButton(lat, lon, addr);
            }
            // Обновляем поле поиска с выбранным адресом (как в старом шаблоне)
            const searchInput = document.getElementById('map-address-search');
            if (searchInput) {
                searchInput.value = mainAddress;
            }
        };
        div.appendChild(item);
    });
    div.style.display = 'block';
}

// Обработчики событий для поиска (ввод, клавиши, клики)
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('map-address-search');
    if (searchInput) {
        // Обработка ввода
        searchInput.addEventListener('input', function() {
            clearTimeout(searchDebounce);
            const q = this.value.trim();
            if (q.length < 2) return clearSearchResults();
            searchDebounce = setTimeout(async () => {
                try {
                    const res = await fetch(`/issues/api/search-address/?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    showSearchResults(data.results);
                } catch (e) {
                    console.warn('Search failed:', e);
                    clearSearchResults();
                }
            }, 300);
        });

        // Обработка клавиш (Enter, ArrowDown, ArrowUp, Escape)
        searchInput.addEventListener('keydown', (e) => {
            const div = document.getElementById('map-search-results');
            const items = div?.querySelectorAll('.map-search-result-item');

            if (e.key === 'Enter') {
                e.preventDefault();
                if (selectedIndex >= 0 && items && items[selectedIndex]) {
                    items[selectedIndex].click();
                } else if (items && items.length > 0) {
                    items[0].click(); // Нажимаем на первый, если нет выбранного
                } else if (searchInput.value.trim()) {
                    searchInput.dispatchEvent(new Event('input')); // Ищем, если поле не пустое
                }
                clearSearchResults(); // Скрываем результаты после выбора или поиска
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!items || items.length === 0) return;
                if (selectedIndex >= 0) {
                    items[selectedIndex].classList.remove('active');
                }
                selectedIndex = (selectedIndex + 1) % items.length;
                items[selectedIndex].classList.add('active');
                items[selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!items || items.length === 0) return;
                if (selectedIndex >= 0) {
                    items[selectedIndex].classList.remove('active');
                }
                selectedIndex = selectedIndex <= 0 ? items.length - 1 : selectedIndex - 1;
                items[selectedIndex].classList.add('active');
                items[selectedIndex].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else if (e.key === 'Escape') {
                clearSearchResults();
                selectedIndex = -1;
            }
        });
    }

    // Клик по кнопке поиска
    document.getElementById('map-search-btn')?.addEventListener('click', () => {
        if (searchInput) {
            searchInput.dispatchEvent(new Event('input'));
            // Попробуем активировать первый результат, если результаты есть
            const div = document.getElementById('map-search-results');
            const items = div?.querySelectorAll('.map-search-result-item');
            if (items && items.length > 0) {
                items[0].click();
            }
        }
    });

    // Клик вне контейнера поиска
    document.addEventListener('click', e => {
        const container = document.querySelector('.map-search-container-above-map');
        if (container && !container.contains(e.target)) clearSearchResults();
    });
});

// === КНОПКА «СООБЩИТЬ О ПРОБЛЕМЕ» ===
function showReportButton(lat, lon, address) {
    const oldBtn = document.getElementById('map-report-btn');
    if (oldBtn) oldBtn.remove();

    const btn = Object.assign(document.createElement('button'), {
        id: 'map-report-btn',
        className: 'btn-problem',
        innerHTML: ' Сообщить о проблеме здесь',
        style: 'position:absolute;width:300px;top:20px:20px;z-index:2' 
    });

    btn.onclick = () => {
        const url = new URL('/issues/create/', location.origin); // Используйте ваш URL
        url.searchParams.set('lat', lat.toFixed(6));
        url.searchParams.set('lon', lon.toFixed(6));
        url.searchParams.set('address', address);
        location.href = url.toString();
    };

    document.getElementById('map-container').appendChild(btn);
}

// === МОДАЛЬНОЕ ОКНО (функции для открытия/закрытия и предпросмотра) ===
// Предполагается, что кнопка "Сообщить" будет вызывать открытие модального окна из HTML
// или через другую логику. Функции ниже могут быть вызваны из HTML onclick или другой JS логики.

function openReportModal(lat, lon, address) {
    document.getElementById('id_lat').value = lat;
    document.getElementById('id_lon').value = lon;
    // Здесь можно заполнить адрес в скрытом поле или отобразить в модальном окне, если нужно
    document.getElementById('report-form-modal').style.display = 'block';
    document.getElementById('modal-backdrop').style.display = 'block';
}

function closeReportModal() {
    document.getElementById('report-form-modal').style.display = 'none';
    document.getElementById('modal-backdrop').style.display = 'none';
    if (tempMarker) {
        tempMarker.remove();
        tempMarker = null;
    }
    // Очищаем форму
    const form = document.querySelector('#report-form-modal form');
    if (form) form.reset();
    // Очищаем превью
    document.getElementById('modal-preview').innerHTML = '';
}

// Обработчик изменения файлов для превью
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('modal-images');
    if (!fileInput) return;

    fileInput.addEventListener('change', function() {
        const preview = document.getElementById('modal-preview');
        preview.innerHTML = '';
        if (this.files.length > 5) {
            alert('Максимум 5 фотографий. Будут загружены только первые 5.');
        }
        Array.from(this.files).slice(0, 5).forEach(file => {
            if (file.size > 5 * 1024 * 1024) {
                preview.appendChild(Object.assign(document.createElement('div'), {
                    className: 'text-danger small mt-1',
                    textContent: `⚠️ ${file.name} слишком большой`
                }));
                return;
            }
            if (!file.type.match('image.*')) {
                preview.appendChild(Object.assign(document.createElement('div'), {
                    className: 'text-danger small mt-1',
                    textContent: `⚠️ ${file.name} не изображение`
                }));
                return;
            }
            const reader = new FileReader();
            reader.onload = e => {
                const img = Object.assign(document.createElement('img'), {
                    src: e.target.result,
                    style: 'width:60px;height:60px;object-fit:cover;border-radius:4px;border:1px solid #ddd'
                });
                preview.appendChild(img);
            };
            reader.readAsDataURL(file);
        });
    });
});

// === ГОЛОСОВАНИЕ (перенесено из старого скрипта) ===
// Функция toggleVote оставлена для совместимости с другими частями шаблона, если используется
function toggleVote(issueId, intendedValue, isUpvoted, isDownvoted) {
    let voteValue = intendedValue.toString();
    if ((intendedValue === 1 && isUpvoted) || (intendedValue === -1 && isDownvoted)) voteValue = '0';

    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    formData.append('vote', voteValue);

    const card = document.querySelector(`.card[data-issue-id="${issueId}"]`); // Предполагаемый селектор для карточки
    if (!card) return;

    const buttons = card.querySelectorAll(`button[onclick*="toggleVote(${issueId},"]`);
    buttons.forEach(b => { b.disabled = true; b.innerHTML = '⋯'; });

    fetch(`/issues/${issueId}/vote/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json().then(d => r.ok ? d : Promise.reject(d)))
    .then(data => {
        const badge = card.querySelector('.badge.bg-primary');
        if (badge) badge.innerHTML = `${data.rating} рейтинг`;
        // Обновление рейтинга во всплывающих окнах на карте (если элементы существуют)
        document.querySelectorAll('.maplibregl-popup-content').forEach(p => {
            if (p.innerHTML.includes(`/issues/${issueId}/`)) {
                const small = p.querySelector('small');
                if (small) {
                    small.innerHTML = small.innerHTML.replace(
                        /Рейтинг: <strong>\d+<\/strong>/,
                        `Рейтинг: <strong>${data.rating}</strong>`
                    );
                }
            }
        });
        const up = card.querySelector(`button[onclick*="toggleVote(${issueId}, 1"]`);
        const down = card.querySelector(`button[onclick*="toggleVote(${issueId}, -1"]`);
        if (up && down) {
            up.className = up.className.replace(/\b(btn-success|btn-outline-success)\b/g, data.user_vote === 1 ? 'btn-success' : 'btn-outline-success');
            down.className = down.className.replace(/\b(btn-danger|btn-outline-danger)\b/g, data.user_vote === -1 ? 'btn-danger' : 'btn-outline-danger');
        }
    })
    .catch(err => {
        console.error('Vote error:', err);
        alert(err.error || 'Ошибка голосования.');
    })
    .finally(() => {
        const up = card.querySelector(`button[onclick*="toggleVote(${issueId}, 1"]`);
        const down = card.querySelector(`button[onclick*="toggleVote(${issueId}, -1"]`);
        if (up) up.innerHTML = '👍';
        if (down) down.innerHTML = '👎';
        if (up) up.disabled = false;
        if (down) down.disabled = false;
    });
}
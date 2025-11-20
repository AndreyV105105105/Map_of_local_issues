// Map Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const bounds = [
        [68.75, 60.75],
        [69.30, 61.15]
    ];

    let markers = [];
    let tempMarker = null;

    const map = new maplibregl.Map({
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
        maxBounds: bounds
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 100 }), 'bottom-left');

    // === МАРКЕРЫ И ФИЛЬТРЫ ===
    function updateMapMarkers(filters) {
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

                    const marker = new maplibregl.Marker({ color: '#e74c3c' })
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
            setTimeout(() => {
                markers.forEach(marker => marker.remove());
                markers = [];
                // Загрузка маркеров из шаблона (если ошибка)
                document.querySelectorAll('.issue-marker').forEach(marker => {
                    const lat = parseFloat(marker.dataset.lat);
                    const lng = parseFloat(marker.dataset.lng);
                    const title = marker.dataset.title;
                    const status = marker.dataset.status;
                    const category = marker.dataset.category;
                    const rating = marker.dataset.rating;
                    const url = marker.dataset.url;
                    const photos = marker.dataset.photos;

                    if (!isNaN(lng) && !isNaN(lat)) {
                        const popup = new maplibregl.Popup({
                            closeButton: false,
                            closeOnClick: false,
                            anchor: 'top',
                            offset: [0, -8],
                            maxWidth: '220px'
                        }).setHTML(`
                            <a href="${url}"
                               style="text-decoration: none; color: inherit; font-weight: bold; display: block; margin-bottom: 4px;">
                                ${title}
                            </a>
                            <small>
                                Статус: <strong>${status}</strong><br>
                                Категория: ${category}<br>
                                Рейтинг: <strong>${rating}</strong>
                                ${photos > 0 ? `<br>📸 ${photos} фото` : ''}
                            </small>
                        `);

                        const marker = new maplibregl.Marker({ color: '#e74c3c' })
                            .setLngLat([lng, lat])
                            .addTo(map);

                        const markerEl = marker.getElement();
                        if (markerEl) {
                            markerEl.addEventListener('mouseenter', (e) => {
                                e.stopPropagation();
                                popup.setLngLat(marker.getLngLat()).addTo(map);
                            });
                            markerEl.addEventListener('mouseleave', (e) => {
                                e.stopPropagation();
                                if (popup.isOpen()) popup.remove();
                            });

                            markerEl.addEventListener('click', (e) => {
                                e.stopPropagation();
                                window.location.href = url;
                            });
                        }

                        markers.push(marker);
                    }
                });
            }, 500);
        });
    }

    function loadIssuesWithFilters(filters) {
        const url = new URL(window.location.href);
        Object.entries(filters).forEach(([key, value]) => {
            value ? url.searchParams.set(key, value) : url.searchParams.delete(key);
        });
        history.pushState({}, '', url);

        const btn = document.querySelector('#filter-form button[type="submit"]');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
        }

        fetch(`/issues/map/?${new URLSearchParams(filters)}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => {
            if (!response.ok) throw new Error('Ошибка сервера');
            return response.text();
        })
        .then(html => {
            document.getElementById('issues-container').innerHTML = html;
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

    const filterForm = document.getElementById('filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const filters = Object.fromEntries(formData.entries());
            loadIssuesWithFilters(filters);
        });
    }

    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            ['category-filter', 'status-filter', 'search-filter', 'sort-filter'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = el.id === 'sort-filter' ? '-created_at' : '';
            });
            document.querySelectorAll('.filter-badge').forEach(el => el.remove());
            
            const formData = new FormData(document.getElementById('filter-form'));
            loadIssuesWithFilters(Object.fromEntries(formData.entries()));
        });
    }

    document.querySelectorAll('.filter-badge').forEach(badge => {
        badge.addEventListener('click', function() {
            const f = this.dataset.filter;
            const el = document.getElementById(f + '-filter');
            if (el) el.value = '';
            this.remove();
            const formData = new FormData(document.getElementById('filter-form'));
            loadIssuesWithFilters(Object.fromEntries(formData.entries()));
        });
    });

    const searchFilter = document.getElementById('search-filter');
    if (searchFilter) {
        let searchTimeout;
        searchFilter.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            if (e.target.value.length > 2 || e.target.value.length === 0) {
                searchTimeout = setTimeout(() => {
                    const formData = new FormData(document.getElementById('filter-form'));
                    loadIssuesWithFilters(Object.fromEntries(formData.entries()));
                }, 500);
            }
        });
    }

    // === АВТОДОПОЛНЕНИЕ ПО АДРЕСУ ===
    function clearSearchResults() {
        const div = document.getElementById('map-search-results');
        if (div) { 
            div.innerHTML = ''; 
            div.style.display = 'none'; 
        }
    }

    function showSearchResults(results) {
        const div = document.getElementById('map-search-results');
        if (!div) return;
        div.innerHTML = '';
        if (!results || results.length === 0) return clearSearchResults();

        results.forEach(r => {
            const item = document.createElement('div');
            item.className = 'map-search-result-item';
            const road = r.address?.road || '';
            const city = r.address?.city || r.address?.town || '';
            const sub = [road, city].filter(Boolean).join(', ') || '';
            item.innerHTML = `<div><strong>${r.display_name}</strong></div><small class="text-muted">${sub}</small>`;
            item.onclick = () => {
                const lat = r.lat, lon = r.lon, addr = r.display_name;
                map.flyTo({ center: [lon, lat], zoom: 16 });
                clearSearchResults();
                if (tempMarker) tempMarker.remove();
                tempMarker = new maplibregl.Marker({ color: '#3498db' })
                    .setLngLat([lon, lat])
                    .setPopup(new maplibregl.Popup().setText(addr))
                    .addTo(map);
                tempMarker.togglePopup();
                if (window.userIsCitizen) {
                    showReportButton(lat, lon, addr);
                }
            };
            div.appendChild(item);
        });
        div.style.display = 'block';
    }

    let searchDebounce;
    const searchInput = document.getElementById('map-address-search');
    if (searchInput) {
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

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const div = document.getElementById('map-search-results');
                const first = div?.querySelector('.map-search-result-item');
                if (first) first.click();
                else if (searchInput.value.trim()) searchInput.dispatchEvent(new Event('input'));
            }
        });
    }

    const searchBtn = document.getElementById('map-search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            if (searchInput) searchInput.dispatchEvent(new Event('input'));
        });
    }

    document.addEventListener('click', e => {
        const container = document.querySelector('.map-search-container');
        if (container && !container.contains(e.target)) clearSearchResults();
    });

    // === КНОПКА «СООБЩИТЬ» ===
    function showReportButton(lat, lon, address) {
        const old = document.getElementById('map-report-btn');
        if (old) old.remove();

        const btn = Object.assign(document.createElement('button'), {
            id: 'map-report-btn',
            className: 'btn btn-success btn-sm',
            innerHTML: '📍 Сообщить о проблеме здесь',
            style: 'position:absolute;top:10px;right:10px;z-index:2'
        });

        btn.onclick = () => {
            const url = new URL('/issues/create/', location.origin);
            url.searchParams.set('lat', lat.toFixed(6));
            url.searchParams.set('lon', lon.toFixed(6));
            url.searchParams.set('address', address);
            location.href = url.toString();
        };

        document.getElementById('map').appendChild(btn);
    }

    // === ИНИЦИАЛИЗАЦИЯ ===
    const userIsCitizen = document.querySelector('#map').dataset.userRole === 'citizen';
    window.userIsCitizen = userIsCitizen;

    map.on('load', () => {
        // Маркеры (уже есть выше — не дублируем)
        // Клик по карте → обратное геокодирование + кнопка
        if (userIsCitizen) {
            map.on('click', async function(e) {
                if (e.originalEvent.target.closest('.maplibregl-marker, .maplibregl-popup')) return;
            
                const lng = e.lngLat.lng;
                const lat = e.lngLat.lat;
            
                // Обратное геокодирование → ОБЯЗАТЕЛЬНО!
                let address = `Координаты: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                try {
                    const resp = await fetch(`/issues/api/reverse-geocode/?lat=${lat}&lon=${lng}`);
                    const data = await resp.json();
                    if (data.address) {
                        address = data.address;
                    }
                } catch (err) {
                    console.warn('Reverse geocode failed:', err);
                }

                if (tempMarker) tempMarker.remove();
                tempMarker = new maplibregl.Marker({ color: '#3498db' })
                    .setLngLat([lng, lat])
                    .setPopup(new maplibregl.Popup().setText(address))
                    .addTo(map);
                tempMarker.togglePopup();

                showReportButton(lat, lng, address);
            });
        }
    });

    map.on('error', e => {
        console.error('Map error:', e);
        document.getElementById('map').innerHTML =
            `<div class="alert alert-danger p-3">❌ Ошибка карты: ${e.error?.message || 'неизвестная ошибка'}</div>`;
    });

    // Preview for modal images
    const modalImagesInput = document.getElementById('modal-images');
    if (modalImagesInput) {
        modalImagesInput.addEventListener('change', function() {
            const preview = document.getElementById('modal-preview');
            preview.innerHTML = '';
            if (this.files.length > 5) alert('Максимум 5 фотографий. Будут загружены только первые 5.');
            Array.from(this.files).slice(0, 5).forEach(file => {
                if (file.size > 5 * 1024 * 1024) return preview.appendChild(Object.assign(document.createElement('div'), { className: 'text-danger small mt-1', textContent: `⚠️ ${file.name} слишком большой` }));
                if (!file.type.match('image.*')) return preview.appendChild(Object.assign(document.createElement('div'), { className: 'text-danger small mt-1', textContent: `⚠️ ${file.name} не изображение` }));
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
    }

    // Vote functionality
    window.toggleVote = function(issueId, intendedValue, isUpvoted, isDownvoted) {
        let voteValue = intendedValue.toString();
        if ((intendedValue === 1 && isUpvoted) || (intendedValue === -1 && isDownvoted)) voteValue = '0';

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        formData.append('vote', voteValue);

        const card = document.querySelector(`.card[data-issue-id="${issueId}"]`);
        if (!card) return;

        const buttons = card.querySelectorAll(`button[onclick*="toggleVote(${issueId},"]`);
        buttons.forEach(b => { 
            b.disabled = true; 
            b.innerHTML = '⋯'; 
        });

        fetch(`/issues/${issueId}/vote/`, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.json().then(d => r.ok ? d : Promise.reject(d)))
        .then(data => {
            const badge = card.querySelector('.badge.bg-primary');
            if (badge) badge.innerHTML = `${data.rating} рейтинг`;
            document.querySelectorAll('.maplibregl-popup-content').forEach(p => {
                if (p.innerHTML.includes(`/issues/${issueId}/`)) {
                    const small = p.querySelector('small');
                    if (small) small.innerHTML = small.innerHTML.replace(
                        /Рейтинг: <strong>\d+<\/strong>/,
                        `Рейтинг: <strong>${data.rating}</strong>`
                    );
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
    };
});
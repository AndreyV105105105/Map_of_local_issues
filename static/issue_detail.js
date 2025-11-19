// static/js/login.js

function togglePasswordVisibility(button) {
    const passwordInput = button.previousElementSibling;
    const eyeIcon = button.querySelector('.eye-icon');
    const eyeClosedIcon = button.querySelector('.eye-closed-icon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.style.display = 'none';
        eyeClosedIcon.style.display = 'inline';
    } else {
        passwordInput.type = 'password';
        eyeIcon.style.display = 'inline';
        eyeClosedIcon.style.display = 'none';
    }
}

// Функция для голосования с возможностью отмены (для страницы деталей проблемы)
function toggleVote(button) {
    // Получаем ID проблемы из атрибута data-issue-id
    const issueId = button.getAttribute('data-issue-id');
    // Получаем текущее направление голоса (1 или -1)
    const direction = parseInt(button.getAttribute('data-direction'));
    
    // Проверяем, является ли кнопка активной (уже нажатой)
    const isActive = button.classList.contains('active');
    
    // Если кнопка уже активна - отменяем голос (отправляем 0)
    const newDirection = isActive ? 0 : direction;
    
    // Отключаем кнопки на время запроса
    const allVoteButtons = document.querySelectorAll(`[data-issue-id="${issueId}"][data-direction]`);
    allVoteButtons.forEach(btn => btn.disabled = true);
    
    // Подготовка данных для отправки
    const formData = new FormData();
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    formData.append('csrfmiddlewaretoken', csrfToken);
    formData.append('vote', newDirection.toString());
    
    // Отправляем AJAX-запрос
    fetch(`/issues/${issueId}/vote/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Обновляем значение рейтинга
            const ratingValueEl = document.querySelector(`[data-rating-for="${issueId}"]`);
            if (ratingValueEl) {
                ratingValueEl.textContent = data.rating;
            }
            
            // Обновляем состояния кнопок
            const upvoteBtn = document.querySelector(`[data-issue-id="${issueId}"][data-direction="1"]`);
            const downvoteBtn = document.querySelector(`[data-issue-id="${issueId}"][data-direction="-1"]`);
            
            if (newDirection === 1) {
                // Нажата кнопка "за"
                upvoteBtn.classList.add('active');
                downvoteBtn.classList.remove('active');
            } else if (newDirection === -1) {
                // Нажата кнопка "против"
                downvoteBtn.classList.add('active');
                upvoteBtn.classList.remove('active');
            } else {
                // Отмена голоса (newDirection === 0)
                upvoteBtn.classList.remove('active');
                downvoteBtn.classList.remove('active');
            }
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
    })
    .catch(error => {
        console.error('Ошибка голосования:', error);
        alert('Ошибка при голосовании: ' + error.message);
    })
    .finally(() => {
        // Возвращаем активность кнопок
        allVoteButtons.forEach(btn => btn.disabled = false);
    });
}

// Инициализация обработчиков голосования при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Добавляем обработчики для всех кнопок голосования
    const voteButtons = document.querySelectorAll('[data-issue-id][data-direction]');
    voteButtons.forEach(button => {
        button.addEventListener('click', function() {
            toggleVote(this);
        });
    });
});

// Инициализация карты (если элемент существует)
function initMap() {
    const mapDiv = document.getElementById('mini-map');
    if (!mapDiv) return;

    // Получаем координаты из данных страницы
    const coordsText = document.querySelector('.coordinates').textContent.trim();
    const [lng, lat] = coordsText.split(', ').map(coord => parseFloat(coord));

    try {
        const miniMap = new maplibregl.Map({
            container: 'mini-map',
            style: {
                version: 8,
                sources: {
                    'osm-de': {
                        type: 'raster',
                        tiles: ['https://tile.openstreetmap.de/{z}/{x}/{y}.png'],
                        tileSize: 256,
                        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    }
                },
                layers: [{
                    id: 'osm-de-tiles',
                    type: 'raster',
                    source: 'osm-de',
                    minzoom: 0,
                    maxzoom: 19
                }]
            },
            center: [lng, lat],
            zoom: 14,
            interactive: false,
            attributionControl: true
        });

        // Маркер
        new maplibregl.Marker({ color: '#e74c3c' })
            .setLngLat([lng, lat])
            .addTo(miniMap);

        // Убираем логотип MapLibre
        miniMap.on('load', () => {
            const logo = miniMap.getContainer().querySelector('.maplibregl-ctrl-logo');
            if (logo) logo.style.display = 'none';
        });

        // Обработка ошибок
        miniMap.on('error', (e) => {
            console.warn('Mini-map warning (non-fatal):', e);
        });

    } catch (e) {
        console.error('Mini-map init failed:', e);
        mapDiv.innerHTML = `
            <div class="map-error">
                <p>Карта не загружена</p>
                <a href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}"
                    target="_blank"
                    class="open-map-link">
                    Открыть в OpenStreetMap
                </a>
            </div>
        `;
    }
}

// Инициализация карты при загрузке страницы (если карта нужна)
document.addEventListener('DOMContentLoaded', function() {
    initMap();
});
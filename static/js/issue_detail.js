// Карта
document.addEventListener('DOMContentLoaded', () => {
    const mapDiv = document.getElementById('mini-map');
    if (!mapDiv) return;

    const lng = parseFloat(document.querySelector('.coordinates').textContent.split(',')[0].trim());
    const lat = parseFloat(document.querySelector('.coordinates').textContent.split(',')[1].trim());

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

        // При ошибке — fallback
        miniMap.on('error', (e) => {
            console.warn('Mini-map warning (non-fatal):', e);
        });

    } catch (e) {
        console.error('Mini-map init failed:', e);
        mapDiv.innerHTML = `
            <div class="h-100 d-flex flex-column">
                <div class="flex-grow-1 bg-light d-flex align-items-center justify-content-center">
                    <div class="text-center p-3">
                        <div class="text-muted mb-2">📍</div>
                        <a href="https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=16/${lat}/${lng}"
                          target="_blank"
                          class="btn btn-sm btn-outline-secondary">
                            Открыть в OpenStreetMap
                        </a>
                    </div>
                </div>
                <div class="px-3 py-2 small text-muted border-top bg-light">
                    <code>${lng.toFixed(6)}, ${lat.toFixed(6)}</code>
                </div>
            </div>
        `;
    }
});

// Голосование
function toggleVote(issueId, intendedValue, isUpvoted, isDownvoted) {
    let voteValue = null;
    if (intendedValue === 1 && isUpvoted) {
        voteValue = '0';  // отмена
    } else if (intendedValue === -1 && isDownvoted) {
        voteValue = '0';  // отмена
    } else {
        voteValue = intendedValue.toString();
    }

    const formData = new FormData();
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
    formData.append('csrfmiddlewaretoken', csrf);
    formData.append('vote', voteValue);

    const upBtn = document.querySelector(`.upvote-btn[data-issue-id="${issueId}"]`);
    const downBtn = document.querySelector(`.downvote-btn[data-issue-id="${issueId}"]`);
    if (upBtn && downBtn) {
        upBtn.disabled = true;
        downBtn.disabled = true;
    }

    fetch(`/issues/${issueId}/vote/`, {
        method: 'POST',
        body: formData,
        redirect: 'follow',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json().then(data => r.ok ? data : Promise.reject(data)))
    .then(data => {
        // Обновляем рейтинг
        const ratingElement = document.querySelector('.rating-value');
        if (ratingElement) {
            ratingElement.textContent = data.rating;
        }

        // Обновляем стиль кнопок
        if (upBtn) {
            upBtn.classList.toggle('active', data.user_vote === 1);
        }
        if (downBtn) {
            downBtn.classList.toggle('active', data.user_vote === -1);
        }
    })
    .catch(err => {
        console.error('Vote error:', err);
        alert(err.error || 'Ошибка голосования.');
    })
    .finally(() => {
        if (upBtn) upBtn.disabled = false;
        if (downBtn) downBtn.disabled = false;
    });
}

// Photo Modal - Упрощенная реализация
let currentPhotoIndex = 0;
let totalPhotos = 0;
let photoUrls = [];

function openPhotoModal(photoUrl, index, total) {
    const modal = document.getElementById('photoModal');
    const modalImage = document.getElementById('modalImage');
    const modalCounter = document.getElementById('modalCounter');
    
    // Собираем все URL фотографий
    photoUrls = [];
    const photoItems = document.querySelectorAll('.photo-item');
    photoItems.forEach(item => {
        const img = item.querySelector('img');
        if (img) photoUrls.push(img.src);
    });
    
    currentPhotoIndex = index - 1;
    totalPhotos = total;
    
    modalImage.src = photoUrl;
    modalCounter.textContent = `${index} / ${total}`;
    
    // Прямое изменение стиля для отображения
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function navigatePhoto(direction) {
    if (direction === 'next') {
        currentPhotoIndex = (currentPhotoIndex + 1) % totalPhotos;
    } else if (direction === 'prev') {
        currentPhotoIndex = (currentPhotoIndex - 1 + totalPhotos) % totalPhotos;
    }
    
    const modalImage = document.getElementById('modalImage');
    const modalCounter = document.getElementById('modalCounter');
    
    if (modalImage && photoUrls[currentPhotoIndex]) {
        modalImage.src = photoUrls[currentPhotoIndex];
        modalCounter.textContent = `${currentPhotoIndex + 1} / ${totalPhotos}`;
    }
}

// Инициализация фото-модального окна
document.addEventListener('DOMContentLoaded', function() {
    // Добавляем обработчики кликов на фото
    const photoItems = document.querySelectorAll('.photo-item');
    photoItems.forEach((item, index) => {
        item.addEventListener('click', function(e) {
            // Проверяем, что клик был на изображении
            if (e.target.tagName === 'IMG') {
                const img = e.target;
                const photoCounter = this.querySelector('.photo-caption span').textContent;
                const photoNumber = parseInt(photoCounter.split('/')[0]);
                const total = parseInt(photoCounter.split('/')[1]);
                openPhotoModal(img.src, photoNumber, total);
            }
        });
    });

    // Обработчик для основного фото
    const mainPhotoLink = document.querySelector('.main-photo-container a');
    if (mainPhotoLink) {
        mainPhotoLink.addEventListener('click', function(e) {
            e.preventDefault();
            const img = this.querySelector('img');
            if (img) {
                openPhotoModal(img.src, 1, document.querySelectorAll('.photo-item').length);
            }
        });
    }

    // Закрытие модального окна по клику вне изображения
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
        photoModal.addEventListener('click', function(e) {
            // Закрываем только если клик был на фоне, а не на контенте
            if (e.target === photoModal) {
                closePhotoModal();
            }
        });
    }

    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });

    // Навигация по стрелкам
    document.addEventListener('keydown', function(e) {
        const modal = document.getElementById('photoModal');
        if (modal && modal.style.display === 'flex') {
            if (e.key === 'ArrowRight') {
                navigatePhoto('next');
            } else if (e.key === 'ArrowLeft') {
                navigatePhoto('prev');
            }
        }
    });
});
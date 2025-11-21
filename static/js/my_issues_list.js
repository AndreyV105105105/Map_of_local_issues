
document.addEventListener('DOMContentLoaded', function() {

    // Photo Modal - Исправленная реализация
    let currentPhotoIndex = 0;
    let photoUrls = []; // Глобальный массив для URL фотографий текущего модального окна

    // Функция для открытия модального окна
    function openPhotoModal(startingIndex, urlsArray) {
        const modal = document.getElementById('photoModal');
        const modalImage = document.getElementById('modalImage');
        const modalCounter = document.getElementById('modalCounter');

        // Проверяем, есть ли что отображать
        if (!urlsArray || urlsArray.length === 0) {
            console.error("No photo URLs provided to openPhotoModal.");
            return;
        }

        photoUrls = urlsArray; // Сохраняем массив URL в глобальной переменной

        // Проверяем, что индекс в пределах
        if (startingIndex < 0 || startingIndex >= photoUrls.length) {
            console.error("Invalid starting index for photo modal. Defaulting to 0.");
            currentPhotoIndex = 0;
        } else {
            currentPhotoIndex = startingIndex;
        }

        // Устанавливаем начальное изображение и счетчик
        modalImage.src = photoUrls[currentPhotoIndex];
        modalCounter.textContent = `${currentPhotoIndex + 1} / ${photoUrls.length}`;

        // Показываем модальное окно
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    // Функция для закрытия модального окна
    function closePhotoModal() {
        const modal = document.getElementById('photoModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
            photoUrls = []; // Очищаем массив при закрытии
        }
    }

    // Функция для переключения фото
    function navigatePhoto(direction) {
        if (photoUrls.length === 0) return; // Нечего листать

        if (direction === 'next') {
            currentPhotoIndex = (currentPhotoIndex + 1) % photoUrls.length;
        } else if (direction === 'prev') {
            currentPhotoIndex = (currentPhotoIndex - 1 + photoUrls.length) % photoUrls.length;
        }

        const modalImage = document.getElementById('modalImage');
        const modalCounter = document.getElementById('modalCounter');

        if (modalImage && photoUrls[currentPhotoIndex]) {
            modalImage.src = photoUrls[currentPhotoIndex];
            modalCounter.textContent = `${currentPhotoIndex + 1} / ${photoUrls.length}`;
        }
    }

    // Инициализация фото-модального окна
    const photoThumbnails = document.querySelectorAll('.photo-thumbnail');
    photoThumbnails.forEach(thumbnail => {
        thumbnail.addEventListener('click', function(e) {
            if (e.target.tagName === 'IMG') {
                const img = e.target;
                const photoCard = this.closest('.issue-card');
                if (photoCard) {
                    // Собираем URL всех фото в этой карточке *здесь*, перед открытием
                    const allPhotosInCard = photoCard.querySelectorAll('.photo-thumbnail img');
                    const urlsArray = Array.from(allPhotosInCard).map(photoImg => photoImg.src);
                    const clickedPhotoIndex = Array.from(allPhotosInCard).indexOf(img);

                    // Вызываем openPhotoModal с индексом и массивом URL
                    openPhotoModal(clickedPhotoIndex, urlsArray);
                }
            }
        });
    });

    // Закрытие по клику на оверлей (фон)
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
        photoModal.addEventListener('click', function(e) {
            if (e.target === photoModal) { // Проверяем, что клик был на фоне
                closePhotoModal();
            }
        });
    }

    // Закрытие по клику на крестик (специально для onclick)
    window.closePhotoModal = closePhotoModal; // Делаем функцию глобальной для onclick
    window.navigatePhoto = navigatePhoto; // Делаем функцию глобальной для onclick

    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });

    // Навигация по стрелкам (влево/вправо)
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
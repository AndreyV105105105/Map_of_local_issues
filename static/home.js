// static/js/home.js

document.addEventListener('DOMContentLoaded', function() {
    initGallery();
});

function initGallery() {
    const gallery = document.getElementById('resultsGallery');
    if (!gallery) return;

    const items = gallery.querySelectorAll('.gallery-item');
    if (items.length === 0) return;

    // Вычисляем ширину одного элемента с учетом gap
    const galleryStyle = window.getComputedStyle(gallery);
    const gap = parseFloat(galleryStyle.gap) || 0;
    const itemWidth = items[0].offsetWidth + gap;

    // Клонируем элементы для бесконечной прокрутки
    function cloneItemsForInfiniteScroll() {
        // Клонируем все элементы и добавляем в конец
        items.forEach(item => {
            const clone = item.cloneNode(true);
            clone.setAttribute('data-cloned', 'true');
            gallery.appendChild(clone);
        });
    }

    // Обработчик прокрутки для бесконечного эффекта
    function handleGalleryScroll() {
        const scrollLeft = gallery.scrollLeft;
        const scrollWidth = gallery.scrollWidth;
        const clientWidth = gallery.clientWidth;
        const originalItemsWidth = items.length * itemWidth;
        
        // Когда прокрутили до середины клонированных элементов в конце
        // Мгновенно и незаметно переходим к началу оригинальных элементов
        if (scrollLeft >= originalItemsWidth) {
            // Мгновенно переходим к началу без анимации
            gallery.style.scrollBehavior = 'auto';
            gallery.scrollLeft = scrollLeft - originalItemsWidth;
            // Возвращаем плавную прокрутку
            setTimeout(() => {
                gallery.style.scrollBehavior = 'smooth';
            }, 0);
        }
        
        // Если прокрутили назад к началу оригинальных элементов
        // Мгновенно переходим к концу клонированных элементов
        if (scrollLeft <= 0) {
            gallery.style.scrollBehavior = 'auto';
            gallery.scrollLeft = originalItemsWidth + scrollLeft;
            setTimeout(() => {
                gallery.style.scrollBehavior = 'smooth';
            }, 0);
        }
    }

    // Функция для прокрутки на один элемент вперед
    function scrollNext() {
        const currentScroll = gallery.scrollLeft;
        gallery.scrollTo({
            left: currentScroll + itemWidth,
            behavior: 'smooth'
        });
    }

    // Функция для прокрутки на один элемент назад
    function scrollPrev() {
        const currentScroll = gallery.scrollLeft;
        gallery.scrollTo({
            left: currentScroll - itemWidth,
            behavior: 'smooth'
        });
    }

    // Обработчики для свайпа на мобильных устройствах
    function initTouchHandlers() {
        let startX = 0;
        let currentX = 0;
        let isScrolling = false;

        gallery.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            isScrolling = true;
        });

        gallery.addEventListener('touchmove', (e) => {
            if (!isScrolling) return;
            currentX = e.touches[0].clientX;
        });

        gallery.addEventListener('touchend', () => {
            if (!isScrolling) return;
            
            const diff = startX - currentX;
            const swipeThreshold = 50;

            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    scrollNext();
                } else {
                    scrollPrev();
                }
            }
            
            isScrolling = false;
        });
    }

    // Инициализация галереи
    function init() {
        // Клонируем элементы для бесконечной прокрутки
        cloneItemsForInfiniteScroll();

        // Устанавливаем начальную позицию прокрутки (начало оригинальных элементов)
        gallery.scrollLeft = 0;

        // Добавляем обработчик прокрутки
        gallery.addEventListener('scroll', handleGalleryScroll);

        // Обработчики для кнопок навигации (если они есть)
        const prevBtn = document.querySelector('.gallery-prev');
        const nextBtn = document.querySelector('.gallery-next');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', scrollPrev);
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', scrollNext);
        }

        // Инициализируем обработчики касания
        initTouchHandlers();

        // Устанавливаем плавную прокрутку по умолчанию
        gallery.style.scrollBehavior = 'smooth';
    }

    // Запускаем инициализацию
    init();
}
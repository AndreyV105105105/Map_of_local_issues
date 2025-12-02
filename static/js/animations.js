/**
 * Глобальные анимации для улучшения UX
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Анимация появления элементов при загрузке страницы
    const animatedElements = document.querySelectorAll('.issue-card, .comment-item, .stat-item, .form-group');
    
    // Используем Intersection Observer для анимации при прокрутке
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        observer.observe(el);
    });
    
    // Анимация для счетчиков статистики
    const statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(stat => {
        const target = parseInt(stat.textContent) || 0;
        if (target > 0) {
            animateCounter(stat, 0, target, 1000);
        }
    });
    
    // Анимация для рейтинга при изменении
    const ratingElements = document.querySelectorAll('.rating-value');
    ratingElements.forEach(rating => {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(() => {
                rating.classList.add('changed');
                setTimeout(() => {
                    rating.classList.remove('changed');
                }, 500);
            });
        });
        observer.observe(rating, { childList: true, characterData: true });
    });
    
    // Плавная прокрутка к якорям
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // Анимация при отправке формы
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.style.transform = 'scale(0.95)';
                submitBtn.style.opacity = '0.7';
            }
        });
    });
    
    // Анимация для модальных окон
    const modals = document.querySelectorAll('.photo-modal, .modal');
    modals.forEach(modal => {
        if (modal.style.display === 'flex' || modal.classList.contains('show')) {
            modal.style.display = 'flex';
            setTimeout(() => {
                modal.classList.add('show');
            }, 10);
        }
    });
    
    // Анимация для алертов
    const alerts = document.querySelectorAll('.custom-alert');
    alerts.forEach(alert => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        setTimeout(() => {
            alert.style.transition = 'all 0.5s ease-out';
            alert.style.opacity = '1';
            alert.style.transform = 'translateX(0)';
        }, 100);
    });
    
    // Анимация при наведении на карточки
    const cards = document.querySelectorAll('.issue-card, .profile-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });
    
    // Анимация для кнопок голосования
    const voteButtons = document.querySelectorAll('.vote-btn');
    voteButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.9)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    // Анимация для фотографий при клике
    const photos = document.querySelectorAll('.photo-item, .photo-thumbnail');
    photos.forEach(photo => {
        photo.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
        });
    });
    
    // Анимация загрузки для динамического контента
    window.showLoading = function(element) {
        if (element) {
            element.innerHTML = '<div class="loading-spinner"></div>';
        }
    };
    
    window.hideLoading = function(element) {
        if (element && element.querySelector('.loading-spinner')) {
            element.querySelector('.loading-spinner').remove();
        }
    };
    
});

/**
 * Анимация счетчика чисел
 */
function animateCounter(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.floor(easeOutQuart * (end - start) + start);
        element.textContent = current;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.textContent = end;
        }
    };
    window.requestAnimationFrame(step);
}

/**
 * Плавное появление элемента
 */
function fadeInElement(element, duration = 300) {
    element.style.opacity = '0';
    element.style.display = '';
    const start = performance.now();
    
    function animate(currentTime) {
        const elapsed = currentTime - start;
        const progress = Math.min(elapsed / duration, 1);
        element.style.opacity = progress;
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }
    
    requestAnimationFrame(animate);
}

/**
 * Плавное исчезновение элемента
 */
function fadeOutElement(element, duration = 300) {
    const start = performance.now();
    const startOpacity = parseFloat(getComputedStyle(element).opacity) || 1;
    
    function animate(currentTime) {
        const elapsed = currentTime - start;
        const progress = Math.min(elapsed / duration, 1);
        element.style.opacity = startOpacity * (1 - progress);
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        } else {
            element.style.display = 'none';
        }
    }
    
    requestAnimationFrame(animate);
}

/**
 * Показать toast-уведомление с анимацией
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 24px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        z-index: 10000;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


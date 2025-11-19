// Password Reset Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const emailInput = document.querySelector('input[type="email"]');
    const submitBtn = document.querySelector('button[type="submit"]');
    
    if (emailInput) {
        // Добавить валидацию email
        emailInput.addEventListener('input', function() {
            const email = this.value;
            const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
            
            if (email && !isValid) {
                this.style.borderColor = '#e74c3c';
            } else {
                this.style.borderColor = '#e1e5e9';
            }
        });
        
        // Focus и blur события для подсветки
        emailInput.addEventListener('focus', function() {
            this.style.borderColor = 'var(--primary-color)';
            this.style.boxShadow = '0 0 0 3px rgba(231, 90, 124, 0.1)';
            this.style.background = 'white';
        });
        
        emailInput.addEventListener('blur', function() {
            const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value);
            if (!isValid && this.value) {
                this.style.borderColor = '#e74c3c';
            } else {
                this.style.borderColor = '#e1e5e9';
                this.style.boxShadow = 'none';
                this.style.background = '#fafafa';
            }
        });
    }
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const email = emailInput.value.trim();
            
            if (!email) {
                e.preventDefault();
                alert('Пожалуйста, введите адрес электронной почты');
                return;
            }
            
            const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
            if (!isValid) {
                e.preventDefault();
                alert('Пожалуйста, введите действительный адрес электронной почты');
                return;
            }
            
            // Показать индикатор загрузки
            submitBtn.disabled = true;
            submitBtn.textContent = 'Отправка...';
        });
    }
    
    // Сброс состояния кнопки при ошибке формы
    if (document.querySelector('.global-error')) {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Отправить инструкции';
        }
    }
});
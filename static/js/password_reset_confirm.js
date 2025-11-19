// Password Reset Confirm Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const password1Input = document.querySelector('input[name="new_password1"]');
    const password2Input = document.querySelector('input[name="new_password2"]');
    const submitBtn = document.querySelector('button[type="submit"]');
    
    if (password1Input && password2Input) {
        // Валидация совпадения паролей
        password2Input.addEventListener('input', function() {
            if (password1Input.value && password2Input.value && password1Input.value !== password2Input.value) {
                this.style.borderColor = '#e74c3c';
            } else {
                this.style.borderColor = '#e1e5e9';
            }
        });
        
        // Focus и blur события для подсветки
        [password1Input, password2Input].forEach(input => {
            input.addEventListener('focus', function() {
                this.style.borderColor = 'var(--primary-color)';
                this.style.boxShadow = '0 0 0 3px rgba(231, 90, 124, 0.1)';
                this.style.background = 'white';
            });
            
            input.addEventListener('blur', function() {
                this.style.borderColor = '#e1e5e9';
                this.style.boxShadow = 'none';
                this.style.background = '#fafafa';
            });
        });
    }
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const password1 = password1Input.value.trim();
            const password2 = password2Input.value.trim();
            
            if (!password1 || !password2) {
                e.preventDefault();
                alert('Пожалуйста, заполните все поля');
                return;
            }
            
            if (password1 !== password2) {
                e.preventDefault();
                alert('Пароли не совпадают');
                return;
            }
            
        });
    }
    
    if (document.querySelector('.error-message')) {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Сохранить новый пароль';
        }
    }
});
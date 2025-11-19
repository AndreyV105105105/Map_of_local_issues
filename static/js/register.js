// static/js/register.js
function togglePasswordVisibility(button) {
    // Находим поле ввода пароля (соседний элемент в DOM)
    const passwordInput = button.previousElementSibling; // Поле <input type="password">
    
    // Находим изображения глаза
    const eyeIcon = button.querySelector('.eye-icon');
    const eyeClosedIcon = button.querySelector('.eye-closed-icon');
    
    if (passwordInput.type === 'password') {
        // Показываем пароль
        passwordInput.type = 'text';
        eyeIcon.style.display = 'none';
        eyeClosedIcon.style.display = 'inline';
    } else {
        // Скрываем пароль
        passwordInput.type = 'password';
        eyeIcon.style.display = 'inline';
        eyeClosedIcon.style.display = 'none';
    }
}

// Добавляем валидацию при отправке формы
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.register-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password1 = document.querySelector('input[name="password1"]');
            const password2 = document.querySelector('input[name="password2"]');
            
            // Проверка подтверждения пароля
            if (password1 && password2 && password1.value !== password2.value) {
                e.preventDefault();
                alert('Пароли не совпадают');
                return false;
            }
        });
    }
});
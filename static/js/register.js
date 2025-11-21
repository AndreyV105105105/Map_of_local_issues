
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


document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.register-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password1 = document.querySelector('input[name="password1"]');
            const password2 = document.querySelector('input[name="password2"]');
            
            
            if (password1 && password2 && password1.value !== password2.value) {
                e.preventDefault();
                alert('Пароли не совпадают');
                return false;
            }
        });
    }
});
function togglePasswordVisibility(button) {
    const passwordInput = button.previousElementSibling;
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        
        button.querySelector('.eye-icon').style.display = 'none';
        button.querySelector('.eye-closed-icon').style.display = 'inline';
    } else {
        passwordInput.type = 'password';
        
        button.querySelector('.eye-icon').style.display = 'inline';
        button.querySelector('.eye-closed-icon').style.display = 'none';
    }
}
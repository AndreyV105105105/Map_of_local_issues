document.addEventListener('DOMContentLoaded', function() {
    
    const closeButtons = document.querySelectorAll('.custom-btn-close');
    
    
    closeButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            
            const alertElement = this.closest('.custom-alert');
            
            
            if (alertElement) {
                alertElement.style.display = 'none';
            }
        });
    });
});
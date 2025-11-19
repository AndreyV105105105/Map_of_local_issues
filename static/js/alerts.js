document.addEventListener('DOMContentLoaded', function() {
    // Находим все кнопки закрытия с классом .custom-btn-close
    const closeButtons = document.querySelectorAll('.custom-btn-close');
    
    // Добавляем обработчик события для каждой кнопки
    closeButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            // Находим ближайший родительский элемент с классом .custom-alert
            const alertElement = this.closest('.custom-alert');
            
            // Если элемент найден, скрываем его
            if (alertElement) {
                alertElement.style.display = 'none';
            }
        });
    });
});
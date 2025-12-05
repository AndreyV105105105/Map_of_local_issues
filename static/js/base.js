
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const headerMenu = document.querySelector('.header__menu');

    if (mobileMenuBtn && headerMenu) {
        mobileMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            mobileMenuBtn.classList.toggle('active');
            headerMenu.classList.toggle('active');
        });

        // Закрытие меню при клике вне его области
        document.addEventListener('click', function(event) {
            const isClickInsideMenu = headerMenu.contains(event.target);
            const isClickOnBtn = mobileMenuBtn.contains(event.target);

            if (!isClickInsideMenu && !isClickOnBtn && headerMenu.classList.contains('active')) {
                mobileMenuBtn.classList.remove('active');
                headerMenu.classList.remove('active');
            }
        });
    }
});


document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const headerMenu = document.querySelector('.header__menu');
    const body = document.body;

    if (mobileMenuBtn && headerMenu) {
        mobileMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            this.classList.toggle('active');
            headerMenu.classList.toggle('active');
            body.classList.toggle('menu-open');
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!headerMenu.contains(e.target) && !mobileMenuBtn.contains(e.target) && headerMenu.classList.contains('active')) {
                mobileMenuBtn.classList.remove('active');
                headerMenu.classList.remove('active');
                body.classList.remove('menu-open');
            }
        });

        // Close menu when clicking a link
        const navLinks = headerMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                mobileMenuBtn.classList.remove('active');
                headerMenu.classList.remove('active');
                body.classList.remove('menu-open');
            });
        });
    }
});

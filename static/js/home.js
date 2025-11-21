

document.addEventListener('DOMContentLoaded', function() {
    initGallery();
});

function initGallery() {
    const gallery = document.getElementById('resultsGallery');
    if (!gallery) return;

    const items = gallery.querySelectorAll('.gallery-item');
    if (items.length === 0) return;

    
    const galleryStyle = window.getComputedStyle(gallery);
    const gap = parseFloat(galleryStyle.gap) || 0;
    const itemWidth = items[0].offsetWidth + gap;

    
    function cloneItemsForInfiniteScroll() {
        
        items.forEach(item => {
            const clone = item.cloneNode(true);
            clone.setAttribute('data-cloned', 'true');
            gallery.appendChild(clone);
        });
    }

    
    function handleGalleryScroll() {
        const scrollLeft = gallery.scrollLeft;
        const scrollWidth = gallery.scrollWidth;
        const clientWidth = gallery.clientWidth;
        const originalItemsWidth = items.length * itemWidth;
        
        
        
        if (scrollLeft >= originalItemsWidth) {
            
            gallery.style.scrollBehavior = 'auto';
            gallery.scrollLeft = scrollLeft - originalItemsWidth;
            
            setTimeout(() => {
                gallery.style.scrollBehavior = 'smooth';
            }, 0);
        }
        
        
        
        if (scrollLeft <= 0) {
            gallery.style.scrollBehavior = 'auto';
            gallery.scrollLeft = originalItemsWidth + scrollLeft;
            setTimeout(() => {
                gallery.style.scrollBehavior = 'smooth';
            }, 0);
        }
    }

    
    function scrollNext() {
        const currentScroll = gallery.scrollLeft;
        gallery.scrollTo({
            left: currentScroll + itemWidth,
            behavior: 'smooth'
        });
    }

    
    function scrollPrev() {
        const currentScroll = gallery.scrollLeft;
        gallery.scrollTo({
            left: currentScroll - itemWidth,
            behavior: 'smooth'
        });
    }

    
    function initTouchHandlers() {
        let startX = 0;
        let currentX = 0;
        let isScrolling = false;

        gallery.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            isScrolling = true;
        });

        gallery.addEventListener('touchmove', (e) => {
            if (!isScrolling) return;
            currentX = e.touches[0].clientX;
        });

        gallery.addEventListener('touchend', () => {
            if (!isScrolling) return;
            
            const diff = startX - currentX;
            const swipeThreshold = 50;

            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    scrollNext();
                } else {
                    scrollPrev();
                }
            }
            
            isScrolling = false;
        });
    }

    
    function init() {
        
        cloneItemsForInfiniteScroll();

        
        gallery.scrollLeft = 0;

        
        gallery.addEventListener('scroll', handleGalleryScroll);

        
        initTouchHandlers();

        
        gallery.style.scrollBehavior = 'smooth';
    }

    
    init();
}
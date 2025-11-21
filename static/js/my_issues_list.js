
document.addEventListener('DOMContentLoaded', function() {

    
    let currentPhotoIndex = 0;
    let photoUrls = []; 

    
    function openPhotoModal(startingIndex, urlsArray) {
        const modal = document.getElementById('photoModal');
        const modalImage = document.getElementById('modalImage');
        const modalCounter = document.getElementById('modalCounter');

        
        if (!urlsArray || urlsArray.length === 0) {
            console.error("No photo URLs provided to openPhotoModal.");
            return;
        }

        photoUrls = urlsArray; 

        
        if (startingIndex < 0 || startingIndex >= photoUrls.length) {
            console.error("Invalid starting index for photo modal. Defaulting to 0.");
            currentPhotoIndex = 0;
        } else {
            currentPhotoIndex = startingIndex;
        }

        
        modalImage.src = photoUrls[currentPhotoIndex];
        modalCounter.textContent = `${currentPhotoIndex + 1} / ${photoUrls.length}`;

        
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    
    function closePhotoModal() {
        const modal = document.getElementById('photoModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
            photoUrls = []; 
        }
    }

    
    function navigatePhoto(direction) {
        if (photoUrls.length === 0) return; 

        if (direction === 'next') {
            currentPhotoIndex = (currentPhotoIndex + 1) % photoUrls.length;
        } else if (direction === 'prev') {
            currentPhotoIndex = (currentPhotoIndex - 1 + photoUrls.length) % photoUrls.length;
        }

        const modalImage = document.getElementById('modalImage');
        const modalCounter = document.getElementById('modalCounter');

        if (modalImage && photoUrls[currentPhotoIndex]) {
            modalImage.src = photoUrls[currentPhotoIndex];
            modalCounter.textContent = `${currentPhotoIndex + 1} / ${photoUrls.length}`;
        }
    }

    
    const photoThumbnails = document.querySelectorAll('.photo-thumbnail');
    photoThumbnails.forEach(thumbnail => {
        thumbnail.addEventListener('click', function(e) {
            if (e.target.tagName === 'IMG') {
                const img = e.target;
                const photoCard = this.closest('.issue-card');
                if (photoCard) {
                    
                    const allPhotosInCard = photoCard.querySelectorAll('.photo-thumbnail img');
                    const urlsArray = Array.from(allPhotosInCard).map(photoImg => photoImg.src);
                    const clickedPhotoIndex = Array.from(allPhotosInCard).indexOf(img);

                    
                    openPhotoModal(clickedPhotoIndex, urlsArray);
                }
            }
        });
    });

    
    const photoModal = document.getElementById('photoModal');
    if (photoModal) {
        photoModal.addEventListener('click', function(e) {
            if (e.target === photoModal) { 
                closePhotoModal();
            }
        });
    }

    
    window.closePhotoModal = closePhotoModal; 
    window.navigatePhoto = navigatePhoto; 

    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });

    
    document.addEventListener('keydown', function(e) {
        const modal = document.getElementById('photoModal');
        if (modal && modal.style.display === 'flex') {
            if (e.key === 'ArrowRight') {
                navigatePhoto('next');
            } else if (e.key === 'ArrowLeft') {
                navigatePhoto('prev');
            }
        }
    });
});
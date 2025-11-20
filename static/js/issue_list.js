// Issues List JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initIssuesList();
});

function initIssuesList() {
    initVotingSystem();
    initStatusUpdates();
    initDeleteConfirmations();
    initFilters();
    initPhotoModal();
}

// Голосование (исправленная версия)
function initVotingSystem() {
    const voteButtons = document.querySelectorAll('.vote-btn');
    
    voteButtons.forEach(button => {
        button.addEventListener('click', handleVote);
    });
}

function handleVote(event) {
    const button = event.currentTarget;
    const issueId = button.dataset.issueId;
    const voteType = parseInt(button.dataset.voteType);
    
    // Находим карточку и элементы
    const issueCard = button.closest('.issue-card');
    const upvoteBtn = issueCard.querySelector('.upvote');
    const downvoteBtn = issueCard.querySelector('.downvote');
    
    const isUpvoted = upvoteBtn.classList.contains('active');
    const isDownvoted = downvoteBtn.classList.contains('active');
    
    // Вызываем toggleVote
    toggleVote(issueId, voteType, isUpvoted, isDownvoted);
}

function toggleVote(issueId, intendedValue, isUpvoted, isDownvoted) {
    let voteValue = null;
    if (intendedValue === 1 && isUpvoted) {
        voteValue = '0';  // отмена
    } else if (intendedValue === -1 && isDownvoted) {
        voteValue = '0';  // отмена
    } else {
        voteValue = intendedValue.toString();
    }

    const formData = new FormData();
    const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
    formData.append('csrfmiddlewaretoken', csrf);
    formData.append('vote', voteValue);

    // Находим элементы в конкретной карточке (ИСПРАВЛЕНО!)
    const issueCard = document.querySelector(`.issue-card[data-issue-id="${issueId}"]`);
    const upBtn = issueCard.querySelector('.upvote');
    const downBtn = issueCard.querySelector('.downvote');
    const ratingElement = issueCard.querySelector('.vote-rating'); // ИСПРАВЛЕНО: было .rating-value
    
    // Блокируем кнопки
    if (upBtn && downBtn) {
        upBtn.disabled = true;
        downBtn.disabled = true;
    }

    fetch(`/issues/${issueId}/vote/`, {
        method: 'POST',
        body: formData,
        headers: { 
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Обновляем рейтинг (ИСПРАВЛЕНО!)
        if (ratingElement) {
            ratingElement.textContent = data.rating || data.new_rating;
        }

        // Обновляем стиль кнопок (ИСПРАВЛЕНО!)
        if (upBtn) {
            upBtn.classList.toggle('active', data.user_vote === 1 || data.user_has_upvoted);
        }
        if (downBtn) {
            downBtn.classList.toggle('active', data.user_vote === -1 || data.user_has_downvoted);
        }
        
        showNotification('Голос учтен!', 'success');
    })
    .catch(error => {
        console.error('Vote error:', error);
        showNotification('Ошибка голосования', 'error');
    })
    .finally(() => {
        if (upBtn) upBtn.disabled = false;
        if (downBtn) downBtn.disabled = false;
    });
}

// Остальные функции остаются без изменений
function initStatusUpdates() {
    const statusForms = document.querySelectorAll('.status-form');
    
    statusForms.forEach(form => {
        form.addEventListener('submit', handleStatusUpdate);
    });
}

function handleStatusUpdate(event) {
    event.preventDefault();
    
    const form = event.currentTarget;
    const submitButton = form.querySelector('.status-update-btn');
    const originalText = submitButton.textContent;
    
    submitButton.textContent = 'Обновление...';
    submitButton.disabled = true;
    
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateStatusUI(form, data.new_status);
            showNotification('Статус обновлен!', 'success');
        } else {
            showNotification(data.error || 'Ошибка обновления', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Ошибка соединения', 'error');
    })
    .finally(() => {
        submitButton.textContent = originalText;
        submitButton.disabled = false;
    });
}

function updateStatusUI(form, newStatus) {
    const issueCard = form.closest('.issue-card');
    const statusElement = issueCard.querySelector('.issue-status');
    
    statusElement.textContent = newStatus.display || newStatus;
    statusElement.className = 'issue-status';
    statusElement.classList.add(`status-${newStatus.value || newStatus.toLowerCase().replace(' ', '_')}`);
}

function initDeleteConfirmations() {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', handleDeleteConfirmation);
    });
}

function handleDeleteConfirmation(event) {
    const button = event.currentTarget;
    const issueTitle = button.dataset.issueTitle;
    
    if (!confirm(`❗ Удалить обращение «${issueTitle}»? Действие нельзя отменить.`)) {
        event.preventDefault();
    }
}

function initFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', handleFilter);
    });
}

function handleFilter(event) {
    const button = event.currentTarget;
    const filterValue = button.textContent.trim();
    
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    button.classList.add('active');
    
    const issueCards = document.querySelectorAll('.issue-card');
    let visibleCount = 0;
    
    issueCards.forEach(card => {
        const status = card.dataset.status;
        let shouldShow = false;
        
        switch(filterValue) {
            case 'Все':
                shouldShow = true;
                break;
            case 'Новые':
                shouldShow = status === 'new';
                break;
            case 'В работе':
                shouldShow = status === 'in_progress';
                break;
            case 'Решено':
                shouldShow = status === 'completed';
                break;
            default:
                shouldShow = true;
        }
        
        if (shouldShow) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    const issuesCount = document.querySelector('.issues-count');
    if (issuesCount) {
        issuesCount.textContent = `(${visibleCount})`;
    }
    
    showNotification(`Показаны: ${filterValue}`, 'info');
}

// Photo Modal System
let currentPhotoIndex = 0;
let currentPhotoUrls = [];

function initPhotoModal() {
    // Этот код будет работать когда вы добавите фото-превью в HTML
    const photoThumbnails = document.querySelectorAll('.photo-thumbnail');
    
    photoThumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', function() {
            const issueCard = this.closest('.issue-card');
            openPhotoModal(issueCard, index);
        });
    });
}

function openPhotoModal(issueCard, startIndex) {
    const photoElements = issueCard.querySelectorAll('.photo-thumbnail img');
    currentPhotoUrls = Array.from(photoElements).map(img => img.src);
    currentPhotoIndex = startIndex;
    
    const modal = document.getElementById('photoModal');
    const modalImage = modal.querySelector('#modalImage');
    const modalCounter = modal.querySelector('#modalCounter');
    
    if (currentPhotoUrls.length > 0) {
        modalImage.src = currentPhotoUrls[currentPhotoIndex];
        modalCounter.textContent = `${currentPhotoIndex + 1} / ${currentPhotoUrls.length}`;
        
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

function navigatePhoto(direction) {
    if (direction === 'next') {
        currentPhotoIndex = (currentPhotoIndex + 1) % currentPhotoUrls.length;
    } else if (direction === 'prev') {
        currentPhotoIndex = (currentPhotoIndex - 1 + currentPhotoUrls.length) % currentPhotoUrls.length;
    }
    
    const modal = document.getElementById('photoModal');
    const modalImage = modal.querySelector('#modalImage');
    const modalCounter = modal.querySelector('#modalCounter');
    
    if (modalImage && currentPhotoUrls[currentPhotoIndex]) {
        modalImage.src = currentPhotoUrls[currentPhotoIndex];
        modalCounter.textContent = `${currentPhotoIndex + 1} / ${currentPhotoUrls.length}`;
    }
}

// Utility Functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#e75a7c',
        warning: '#f59e0b'
    };
    
    notification.style.background = colors[type] || colors.info;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}
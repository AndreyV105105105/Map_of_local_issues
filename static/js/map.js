
function toggleVote(issueId, intendedValue, isUpvoted, isDownvoted) {
    let voteValue = intendedValue.toString();
    if ((intendedValue === 1 && isUpvoted) || (intendedValue === -1 && isDownvoted)) voteValue = '0';

    const formData = new FormData();
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
    formData.append('vote', voteValue);

    const card = document.querySelector(`.card[data-issue-id="${issueId}"]`); // 
    if (!card) return;

    const buttons = card.querySelectorAll(`button[onclick*="toggleVote(${issueId},"]`);
    buttons.forEach(b => { b.disabled = true; b.innerHTML = '⋯'; });

    fetch(`/issues/${issueId}/vote/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json().then(d => r.ok ? d : Promise.reject(d)))
    .then(data => {
        const badge = card.querySelector('.badge.bg-primary');
        if (badge) badge.innerHTML = `${data.rating} рейтинг`;

        document.querySelectorAll('.maplibregl-popup-content').forEach(p => {
            if (p.innerHTML.includes(`/issues/${issueId}/`)) {
                const small = p.querySelector('small');
                if (small) {
                    small.innerHTML = small.innerHTML.replace(
                        /Рейтинг: <strong>\d+<\/strong>/,
                        `Рейтинг: <strong>${data.rating}</strong>`
                    );
                }
            }
        });
        const up = card.querySelector(`button[onclick*="toggleVote(${issueId}, 1"]`);
        const down = card.querySelector(`button[onclick*="toggleVote(${issueId}, -1"]`);
        if (up && down) {
            up.className = up.className.replace(/\b(btn-success|btn-outline-success)\b/g, data.user_vote === 1 ? 'btn-success' : 'btn-outline-success');
            down.className = down.className.replace(/\b(btn-danger|btn-outline-danger)\b/g, data.user_vote === -1 ? 'btn-danger' : 'btn-outline-danger');
        }
    })
    .catch(err => {
        console.error('Vote error:', err);
        alert(err.error || 'Ошибка голосования.');
    })
    .finally(() => {
        const up = card.querySelector(`button[onclick*="toggleVote(${issueId}, 1"]`);
        const down = card.querySelector(`button[onclick*="toggleVote(${issueId}, -1"]`);
        if (up) up.innerHTML = '👍';
        if (down) down.innerHTML = '👎';
        if (up) up.disabled = false;
        if (down) down.disabled = false;
    });
}





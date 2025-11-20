// Create Issue Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Preview фото
    const imagesInput = document.getElementById('images');
    const preview = document.getElementById('preview');
    
    if (imagesInput && preview) {
        imagesInput.addEventListener('change', function() {
            preview.innerHTML = '';
            for (let file of this.files) {
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.style.cssText = 'width:100px;height:100px;object-fit:cover;margin:5px;border-radius:4px';
                preview.appendChild(img);
            }
        });
    }

    // === АВТОДОПОЛНЕНИЕ ===
    let searchDebounce;
    const addressSearch = document.getElementById('address-search');
    const addressInput = document.getElementById('address');
    const latInput = document.getElementById('lat');
    const lonInput = document.getElementById('lon');

    if (addressSearch) {
        addressSearch.addEventListener('input', function() {
            clearTimeout(searchDebounce);
            const q = this.value.trim();
            if (q.length < 2) return;

            searchDebounce = setTimeout(async () => {
                try {
                    const res = await fetch(`/issues/api/search-address/?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0) {
                        const r = data.results[0];
                        latInput.value = r.lat.toFixed(6);
                        lonInput.value = r.lon.toFixed(6);
                        addressInput.value = r.display_name;
                        addressSearch.value = r.display_name; // подставляем полный адрес
                    }
                } catch (e) {
                    console.warn('Autocomplete failed:', e);
                }
            }, 300);
        });

        // Enter → взять первый результат
        addressSearch.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addressSearch.dispatchEvent(new Event('input'));
            }
        });
    }

    // === ОБРАТНОЕ ГЕОКОДИРОВАНИЕ ПРИ РУЧНОМ ВВОДЕ ===
    let reverseDebounce;
    [latInput, lonInput].forEach(el => {
        el?.addEventListener('input', () => {
            clearTimeout(reverseDebounce);
            reverseDebounce = setTimeout(async () => {
                const lat = parseFloat(latInput.value);
                const lon = parseFloat(lonInput.value);
                if (isNaN(lat) || isNaN(lon)) return;
                try {
                    const res = await fetch(`/issues/api/reverse-geocode/?lat=${lat}&lon=${lon}`);
                    const data = await res.json();
                    if (data.address) addressInput.value = data.address;
                } catch (e) {
                    console.warn('Reverse geocode failed:', e);
                }
            }, 800);
        });
    });

    // === ИНИЦИАЛИЗАЦИЯ: ЕСЛИ ПЕРЕДАНЫ ПАРАМЕТРЫ — ПОДСТАВИТЬ ===
    const urlParams = new URLSearchParams(window.location.search);
    const lat = urlParams.get('lat');
    const lon = urlParams.get('lon');
    const address = urlParams.get('address');

    if (lat && lon) {
        latInput.value = parseFloat(lat).toFixed(6);
        lonInput.value = parseFloat(lon).toFixed(6);
        if (address) {
            addressInput.value = address;
            addressSearch.value = address;
        } else {
            // Обратное геокодирование при загрузке
            setTimeout(async () => {
                try {
                    const res = await fetch(`/issues/api/reverse-geocode/?lat=${lat}&lon=${lon}`);
                    const data = await res.json();
                    if (data.address) {
                        addressInput.value = data.address;
                        addressSearch.value = data.address;
                    }
                } catch (e) {
                    console.warn('Reverse geocode on load failed:', e);
                }
            }, 100);
        }
    }
});
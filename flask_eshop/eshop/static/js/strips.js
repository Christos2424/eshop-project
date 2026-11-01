// Product strips built from this browser's storage: saved items (the Saved items page)
// and recently viewed products (the home page)
document.addEventListener('DOMContentLoaded', function() {
    // Same markup as the stars() template macro: full, half and empty stars
    function starsHtml(rating) {
        const halves = Math.round((rating || 0) * 2);
        let icons = '';
        for (let i = 1; i <= 5; i++) {
            const icon = halves >= i * 2 ? 'fas fa-star' : halves === i * 2 - 1 ? 'fas fa-star-half-alt' : 'far fa-star';
            icons += `<i class="${icon}"></i>`;
        }
        const label = escapeHtml(t('Rated {rating} out of 5', { rating: rating || 0 }));
        return `<span class="stars" role="img" aria-label="${label}">${icons}</span>`;
    }

    function ratingHtml(product) {
        if (product.review_count == null) return '';
        const count = product.review_count;
        const title = escapeHtml(tn('{n} review', '{n} reviews', count));
        return `
            <div class="card-rating${count ? '' : ' is-empty'}">
                ${starsHtml(product.rating)}
                <span class="card-rating-count" title="${title}">${count ? product.rating + ' ' : ''}(${count})</span>
            </div>`;
    }

    function miniCard(product, index) {
        return `
            <div class="mini-card" style="animation-delay: ${index * 40}ms">
                <div class="mini-card-media">${imageHtml(product.image, product.name, '', product.art)}</div>
                <button type="button" class="wishlist-btn" data-wishlist-toggle data-product-id="${product.id}"
                        aria-label="${escapeHtml(t('Save {name} for later', { name: product.name }))}" aria-pressed="false">
                    <i class="far fa-heart"></i>
                </button>
                <div class="mini-card-body">
                    <a href="${escapeHtml(product.url)}" class="mini-card-name">${escapeHtml(product.name)}</a>
                    ${ratingHtml(product)}
                    <div class="mini-card-price">${formatPrice(product.price)}</div>
                </div>
            </div>`;
    }

    async function renderStrip(sectionId, ids) {
        const section = document.getElementById(sectionId);
        if (!section) return;
        if (!ids.length) {
            section.hidden = true;
            return;
        }

        try {
            const data = await requestJSON(`${window.APP_URLS.products_api}?ids=${ids.join(',')}`);
            section.querySelector('[data-strip-track]').innerHTML = data.products.map(miniCard).join('');
            section.hidden = data.products.length === 0;
            syncWishlistButtons(section);
        } catch (error) {
            console.error('Error loading products:', error);
            section.hidden = true;
        }
    }

    // The saved items page shows a message instead of an empty list
    async function renderSaved() {
        await renderStrip('savedStrip', getWishlist());
        const empty = document.getElementById('savedEmpty');
        if (empty) empty.hidden = !document.getElementById('savedStrip').hidden;
    }

    renderSaved();
    renderStrip('recentStrip', storage.get(RECENTLY_VIEWED_KEY, []));

    window.addEventListener('wishlist:change', renderSaved);

    document.querySelector('[data-clear-recent]')?.addEventListener('click', function() {
        storage.set(RECENTLY_VIEWED_KEY, []);
        renderStrip('recentStrip', []);
    });
});

// Product Detail Page JavaScript: tabs, quantity stepper, image zoom and recently viewed
document.addEventListener('DOMContentLoaded', function() {
    const page = document.querySelector('.product-page');
    if (!page) return;

    initTabs();
    initQuantityStepper();
    initImageZoom();
    initImageViewer();
    initReviewForms();
    rememberRecentlyViewed(Number(page.dataset.productId));
});

// Post, edit and delete reviews without reloading the page: the reviews tab, its count
// and the rating under the title are swapped in from the page the server sends back
function initReviewForms() {
    const pane = document.getElementById('reviews');
    if (!pane) return;

    pane.addEventListener('submit', async function(e) {
        const form = e.target.closest('.review-form, .review-delete');
        if (!form) return;
        e.preventDefault();

        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        try {
            const { doc, messages } = await submitFormInBackground(form);
            // On an error keep the form as it is, so nothing the user typed is lost
            if (toastMessages(messages)) {
                ['#reviews', '#tab-reviews .tab-count', '.product-rating-link'].forEach(selector => {
                    const fresh = doc.querySelector(selector);
                    const current = document.querySelector(selector);
                    if (fresh && current) current.innerHTML = fresh.innerHTML;
                });
                replayAnimation(pane, 'fade-in');
            }
        } catch (error) {
            console.error('Error saving review:', error);
            showToast(t('An unexpected error occurred. Please try again.'), 'error');
        } finally {
            button.disabled = false;
        }
    });
}

// Tabs, with arrow-key navigation between them
function initTabs() {
    const tabs = Array.from(document.querySelectorAll('.tab-btn'));

    function activate(tab, focus = false) {
        tabs.forEach(t => {
            const selected = t === tab;
            t.classList.toggle('active', selected);
            t.setAttribute('aria-selected', selected);
            t.tabIndex = selected ? 0 : -1;
            const pane = document.getElementById(t.getAttribute('aria-controls'));
            pane.hidden = !selected;
            pane.classList.toggle('active', selected);
        });
        if (focus) tab.focus();
    }

    // Links to #reviews (the rating under the title, and redirects after posting a review) open that tab
    function openFromHash() {
        const tab = tabs.find(t => '#' + t.getAttribute('aria-controls') === location.hash);
        if (!tab) return;
        activate(tab);
        document.querySelector('.product-tabs').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    document.querySelectorAll('[data-open-reviews]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            history.replaceState(null, '', '#reviews');
            openFromHash();
        });
    });
    window.addEventListener('hashchange', openFromHash);
    openFromHash();

    tabs.forEach((tab, i) => {
        tab.addEventListener('click', () => activate(tab));
        tab.addEventListener('keydown', function(e) {
            if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
            e.preventDefault();
            const step = e.key === 'ArrowRight' ? 1 : -1;
            activate(tabs[(i + step + tabs.length) % tabs.length], true);
        });
    });
}

// Quantity +/- buttons, kept within the stock; the add button shows the line total
function initQuantityStepper() {
    const form = document.querySelector('.purchase-box');
    if (!form) return;

    const input = form.querySelector('.qty-input');
    const decrease = form.querySelector('[data-step="-1"]');
    const increase = form.querySelector('[data-step="1"]');
    const total = form.querySelector('[data-line-total]');
    const hint = form.querySelector('[data-stepper-hint]');
    const price = parseFloat(form.dataset.price);
    const max = parseInt(input.max, 10);

    function setQuantity(value) {
        const quantity = Math.min(Math.max(parseInt(value, 10) || 1, 1), max);
        input.value = quantity;
        decrease.disabled = quantity <= 1;
        increase.disabled = quantity >= max;
        hint.textContent = quantity >= max && max > 1 ? t("That's all we have: {n} in stock.", { n: max }) : '';
        updateTotal(quantity);
    }

    function updateTotal(quantity) {
        const text = formatPrice(price * quantity);
        if (total.textContent !== text) {
            total.textContent = text;
            replayAnimation(total, 'changed');
        }
    }

    form.querySelectorAll('[data-step]').forEach(button => {
        button.addEventListener('click', function() {
            setQuantity(parseInt(input.value, 10) + parseInt(button.dataset.step, 10));
        });
    });

    // Update the total while typing, clamp the value when the user is done
    input.addEventListener('input', function() {
        const quantity = parseInt(input.value, 10);
        if (quantity >= 1 && quantity <= max) updateTotal(quantity);
    });
    input.addEventListener('change', () => setQuantity(input.value));

    setQuantity(input.value);
}

// Zoom into the image where the mouse points (mouse/trackpad only)
function initImageZoom() {
    const frame = document.getElementById('galleryFrame');
    if (!frame || !frame.classList.contains('has-image')) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    frame.addEventListener('mouseenter', () => frame.classList.add('zooming'));
    frame.addEventListener('mouseleave', () => frame.classList.remove('zooming'));
    frame.addEventListener('mousemove', function(e) {
        const image = frame.querySelector('.main-product-image');
        if (!image) return;
        const rect = frame.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width * 100;
        const y = (e.clientY - rect.top) / rect.height * 100;
        image.style.transformOrigin = `${x}% ${y}%`;
    });
}

// Touch screens: tap the image for a full-screen viewer with pinch, drag and double-tap zoom
function initImageViewer() {
    const frame = document.getElementById('galleryFrame');
    const source = frame && frame.querySelector('.main-product-image');
    if (!source || source.tagName !== 'IMG') return;
    // Mouse users get the hover zoom instead
    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    frame.addEventListener('click', () => openImageViewer(source));
}

function openImageViewer(source) {
    const MAX_SCALE = 5;
    const viewer = document.createElement('div');
    viewer.className = 'image-viewer';
    viewer.setAttribute('role', 'dialog');
    viewer.setAttribute('aria-modal', 'true');
    viewer.setAttribute('aria-label', source.alt);
    viewer.innerHTML = `
        <img alt="${escapeHtml(source.alt)}" src="${escapeHtml(source.currentSrc || source.src)}">
        <button type="button" class="image-viewer-close" aria-label="${escapeHtml(t('Close'))}"><i class="fas fa-times"></i></button>
        <span class="image-viewer-tip">${escapeHtml(t('Pinch or double-tap to zoom'))}</span>`;
    document.body.appendChild(viewer);
    lockScroll(true);

    const img = viewer.querySelector('img');
    // The image sits centred; scale and (x, y) are applied from its top-left corner
    let scale = 1, x = 0, y = 0;
    const pointers = new Map();
    let pinch = null;      // { distance, center } of the previous pinch step
    let lastTap = 0;
    let moved = false;

    function apply(animate = false) {
        img.classList.toggle('is-animating', animate);
        img.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    }

    // Keep the picture on screen: when zoomed in its edges can't be dragged past the
    // screen's edges, and when it is smaller than the screen it stays centred
    function clamp() {
        const box = viewer.getBoundingClientRect();
        const axis = (size, view, base) => {
            const scaled = size * scale;
            if (scaled <= view) return [(view - scaled) / 2 - base, (view - scaled) / 2 - base];
            return [view - scaled - base, -base];
        };
        const [minX, maxX] = axis(img.offsetWidth, box.width, (box.width - img.offsetWidth) / 2);
        const [minY, maxY] = axis(img.offsetHeight, box.height, (box.height - img.offsetHeight) / 2);
        x = Math.min(Math.max(x, minX), maxX);
        y = Math.min(Math.max(y, minY), maxY);
    }

    // Zoom by a factor around a screen point, so that point stays under the fingers
    function zoomAt(factor, clientX, clientY) {
        const box = viewer.getBoundingClientRect();
        const next = Math.min(Math.max(scale * factor, 1), MAX_SCALE);
        const ratio = next / scale;
        const px = clientX - box.left - (box.width - img.offsetWidth) / 2;
        const py = clientY - box.top - (box.height - img.offsetHeight) / 2;
        x = px - (px - x) * ratio;
        y = py - (py - y) * ratio;
        scale = next;
        clamp();
    }

    function reset() {
        scale = 1; x = 0; y = 0;
    }

    const pinchState = () => {
        const [a, b] = [...pointers.values()];
        return { distance: Math.hypot(a.x - b.x, a.y - b.y), center: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } };
    };

    viewer.addEventListener('pointerdown', function(e) {
        if (e.target.closest('.image-viewer-close')) return;
        viewer.setPointerCapture(e.pointerId);
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        moved = false;
        pinch = pointers.size === 2 ? pinchState() : null;
    });

    viewer.addEventListener('pointermove', function(e) {
        const previous = pointers.get(e.pointerId);
        if (!previous) return;
        pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

        if (pointers.size === 2 && pinch) {
            const now = pinchState();
            // Both fingers moving pans, spreading them zooms
            x += now.center.x - pinch.center.x;
            y += now.center.y - pinch.center.y;
            zoomAt(now.distance / pinch.distance, now.center.x, now.center.y);
            pinch = now;
            moved = true;
        } else if (pointers.size === 1 && scale > 1) {
            x += e.clientX - previous.x;
            y += e.clientY - previous.y;
            clamp();
            moved = true;
        } else if (Math.hypot(e.clientX - previous.x, e.clientY - previous.y) > 3) {
            moved = true;
        }
        apply();
    });

    function release(e) {
        const wasSingleTap = e.type === 'pointerup' && pointers.size === 1 && !moved;
        pointers.delete(e.pointerId);
        pinch = null;

        if (wasSingleTap) {
            const now = Date.now();
            if (now - lastTap < 300) {
                // Double-tap zooms in where tapped, or back out
                if (scale > 1) reset();
                else zoomAt(2.5, e.clientX, e.clientY);
                apply(true);
                lastTap = 0;
            } else {
                lastTap = now;
            }
        } else if (scale < 1.02) {
            reset();
            apply(true);
        }
    }
    viewer.addEventListener('pointerup', release);
    viewer.addEventListener('pointercancel', release);

    // Mouse wheel / trackpad pinch, for tablets with a mouse
    viewer.addEventListener('wheel', function(e) {
        e.preventDefault();
        zoomAt(e.deltaY < 0 ? 1.2 : 1 / 1.2, e.clientX, e.clientY);
        apply();
    }, { passive: false });

    function close() {
        document.removeEventListener('keydown', onKey);
        lockScroll(false);
        viewer.classList.add('is-leaving');
        setTimeout(() => viewer.remove(), 200);
    }
    function onKey(e) {
        if (e.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKey);
    viewer.querySelector('.image-viewer-close').addEventListener('click', close);

    // The tip fades out after a moment
    setTimeout(() => viewer.querySelector('.image-viewer-tip')?.style.setProperty('opacity', '0'), 2500);
}

// Remembered in this browser for the "Recently viewed" row on the home page
function rememberRecentlyViewed(productId) {
    if (!productId) return;
    const recent = storage.get(RECENTLY_VIEWED_KEY, []).filter(id => id !== productId);
    recent.unshift(productId);
    storage.set(RECENTLY_VIEWED_KEY, recent.slice(0, 12));
}

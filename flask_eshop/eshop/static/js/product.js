// Product Detail Page JavaScript: tabs, quantity stepper, image zoom and recently viewed
document.addEventListener('DOMContentLoaded', function() {
    const page = document.querySelector('.product-page');
    if (!page) return;

    initTabs();
    initQuantityStepper();
    initImageZoom();
    rememberRecentlyViewed(Number(page.dataset.productId));
});

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

// Remembered in this browser for the "Recently viewed" row on the home page
function rememberRecentlyViewed(productId) {
    if (!productId) return;
    const recent = storage.get(RECENTLY_VIEWED_KEY, []).filter(id => id !== productId);
    recent.unshift(productId);
    storage.set(RECENTLY_VIEWED_KEY, recent.slice(0, 12));
}

// base.js - JavaScript shared by every eShop page:
// header menus, live search, toasts, modal, cart drawer, add to cart and wishlist

const WISHLIST_KEY = 'eshop:wishlist';
const RECENTLY_VIEWED_KEY = 'eshop:recent';

// CSRF token for AJAX requests (set in base.html <meta name="csrf-token">)
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
}

document.addEventListener('DOMContentLoaded', function() {
    initScrollHeader();
    CategoriesSidebar.init();
    initDropdowns();
    initConfirmButtons();
    initClickableRows();
    initSearchSuggestions();
    initFlashMessages();
    initImageFallback();
    initScrollLinks();
    initAddToCart();
    CartDrawer.init();
    initWishlist();
    initEscapeKey();
});

// ---------- Translations ----------

// t('Only {n} left', { n: 3 }): the text in the current language (window.I18N comes from
// /i18n/<lang>.js, loaded by base.html; English needs no catalog). Params are not escaped.
function t(text, params = {}) {
    const translated = (window.I18N && window.I18N[text]) || text;
    return translated.replace(/\{(\w+)\}/g, (match, key) => (key in params ? params[key] : match));
}

// tn('{n} item', '{n} items', count): singular or plural form
function tn(singular, plural, n, params = {}) {
    return t(n === 1 ? singular : plural, { n, ...params });
}

// ---------- Utilities ----------

function escapeHtml(value) {
    const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(value ?? '').replace(/[&<>"']/g, ch => entities[ch]);
}

function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(price);
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Restart a CSS animation class on an element (e.g. a badge "bump")
function replayAnimation(element, className) {
    element.classList.remove(className);
    void element.offsetWidth;
    element.classList.add(className);
}

// localStorage that never throws (private browsing, blocked storage)
const storage = {
    get(key, fallback) {
        try {
            const value = localStorage.getItem(key);
            return value === null ? fallback : JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            // Storage unavailable; the feature just won't persist
        }
    }
};

// Fetch JSON from our server. X-Requested-With tells Flask it's an AJAX request.
async function requestJSON(url, options = {}) {
    const response = await fetch(url, {
        credentials: 'same-origin',
        ...options,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken(),
            'Accept': 'application/json',
            ...(options.headers || {})
        }
    });
    const contentType = response.headers.get('Content-Type') || '';
    if (!contentType.includes('application/json')) {
        throw new Error(`Unexpected response (${response.status})`);
    }
    return response.json();
}

function postForm(url, data) {
    let body = data;
    if (!(data instanceof FormData)) {
        body = new FormData();
        Object.entries(data).forEach(([key, value]) => body.append(key, value));
    }
    if (!body.has('csrf_token')) {
        body.append('csrf_token', getCsrfToken());
    }
    return requestJSON(url, { method: 'POST', body });
}

// Product image, or an icon for its category when there is no image (art: { icon, hue } from the server)
function imageHtml(src, alt, className = '', art = null) {
    if (!src) {
        const icon = art ? art.icon : 'fa-box-open';
        const hue = art ? art.hue : 245;
        return `<div class="img-placeholder ${className}" role="img" aria-label="${escapeHtml(alt)}" style="--hue: ${Number(hue)}"><i class="fas ${escapeHtml(icon)}"></i></div>`;
    }
    return `<img src="${escapeHtml(src)}" alt="${escapeHtml(alt)}" class="${className}" loading="lazy" data-fallback="icon">`;
}

// Thin progress bar at the top of the page while AJAX content loads
let loadingCount = 0;
function setLoading(active) {
    const bar = document.getElementById('loadingBar');
    if (!bar) return;
    const wasLoading = loadingCount > 0;
    loadingCount = Math.max(0, loadingCount + (active ? 1 : -1));

    if (loadingCount > 0 && !wasLoading) {
        bar.classList.remove('active', 'done');
        void bar.offsetWidth; // restart the bar from zero
        bar.classList.add('active');
    } else if (loadingCount === 0 && wasLoading) {
        bar.classList.replace('active', 'done');
    }
}

// Sidebar, drawer and modal each lock page scrolling while open
let scrollLocks = 0;
function lockScroll(lock) {
    scrollLocks = Math.max(0, scrollLocks + (lock ? 1 : -1));
    document.body.style.overflow = scrollLocks ? 'hidden' : '';
}

// ---------- Header ----------

// Hide the header when scrolling down, bring it back when scrolling up
function initScrollHeader() {
    const header = document.getElementById('mainHeader');
    if (!header) return;

    const searchInput = document.getElementById('headerSearchInput');
    let lastScrollY = window.scrollY;
    let ticking = false;

    function updateHeader() {
        const currentScrollY = window.scrollY;
        const menuOpen = header.querySelector('.active') || document.activeElement === searchInput;

        header.classList.toggle('header-scrolled', currentScrollY > 10);
        if (currentScrollY > 200 && currentScrollY > lastScrollY && !menuOpen) {
            header.classList.add('header-hidden');
        } else if (currentScrollY < lastScrollY || currentScrollY <= 200) {
            header.classList.remove('header-hidden');
        }

        lastScrollY = currentScrollY;
        ticking = false;
    }

    window.addEventListener('scroll', function() {
        if (!ticking) {
            requestAnimationFrame(updateHeader);
            ticking = true;
        }
    }, { passive: true });

    header.addEventListener('focusin', () => header.classList.remove('header-hidden'));
}

// Categories Sidebar
const CategoriesSidebar = {
    init() {
        this.el = document.getElementById('categoriesSidebar');
        this.overlay = document.getElementById('sidebarOverlay');
        this.toggle = document.getElementById('categoriesToggle');
        if (!this.el) return;

        this.toggle?.addEventListener('click', () => this.open());
        document.getElementById('closeCategories')?.addEventListener('click', () => this.close());
        this.overlay?.addEventListener('click', () => this.close());

        document.addEventListener('click', e => {
            if (e.target.closest('[data-open-categories]')) this.open();
        });

        // Category links close the sidebar (on the shop page they load without a reload)
        this.el.addEventListener('click', e => {
            if (e.target.closest('a')) this.close();
        });
    },

    isOpen() {
        return Boolean(this.el?.classList.contains('open'));
    },

    open() {
        if (!this.el || this.isOpen()) return;
        this.el.classList.add('open');
        this.el.setAttribute('aria-hidden', 'false');
        this.overlay?.classList.add('active');
        this.toggle?.setAttribute('aria-expanded', 'true');
        document.getElementById('mainHeader')?.classList.remove('header-hidden');
        lockScroll(true);
        (this.el.querySelector('.category-sidebar-item.active') || this.el.querySelector('a'))?.focus();
    },

    close() {
        if (!this.isOpen()) return;
        this.el.classList.remove('open');
        this.el.setAttribute('aria-hidden', 'true');
        this.overlay?.classList.remove('active');
        this.toggle?.setAttribute('aria-expanded', 'false');
        lockScroll(false);
    }
};

// User and language dropdowns - click to open
function initDropdowns() {
    const dropdowns = [
        [document.querySelector('.user-dropdown'), document.getElementById('userMenuToggle')],
        [document.querySelector('.language-selector'), document.querySelector('.language-btn')]
    ].filter(([root, toggle]) => root && toggle);

    dropdowns.forEach(([root, toggle]) => {
        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const open = !root.classList.contains('active');
            closeDropdowns();
            root.classList.toggle('active', open);
            toggle.setAttribute('aria-expanded', open);
        });

        root.addEventListener('click', function(e) {
            if (e.target.closest('a')) closeDropdowns();
        });
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-dropdown, .language-selector')) closeDropdowns();
    });
}

function closeDropdowns() {
    document.querySelectorAll('.user-dropdown.active, .language-selector.active').forEach(dropdown => {
        dropdown.classList.remove('active');
        dropdown.querySelector('[aria-expanded]')?.setAttribute('aria-expanded', 'false');
    });
}

// Buttons and links with data-confirm="Question?" ask before going ahead
function initConfirmButtons() {
    document.addEventListener('click', function(e) {
        const button = e.target.closest('[data-confirm]');
        if (button && !window.confirm(button.dataset.confirm)) {
            e.preventDefault();
            e.stopPropagation();
        }
    }, true);
}

// One Escape handler so only the top-most layer closes
function initEscapeKey() {
    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        if (closeModal()) return;
        if (CartDrawer.isOpen()) return CartDrawer.close();
        if (CategoriesSidebar.isOpen()) return CategoriesSidebar.close();
        closeDropdowns();
    });
}

// ---------- Live search suggestions ----------

function initSearchSuggestions() {
    const form = document.getElementById('headerSearchForm');
    const input = document.getElementById('headerSearchInput');
    const panel = document.getElementById('searchSuggestions');
    if (!form || !input || !panel) return;

    let controller = null;
    let activeIndex = -1;

    const options = () => Array.from(panel.querySelectorAll('[data-suggestion]'));

    function show() {
        panel.hidden = false;
        input.setAttribute('aria-expanded', 'true');
    }

    function hide() {
        panel.hidden = true;
        input.setAttribute('aria-expanded', 'false');
        setActive(-1);
    }

    function setActive(index) {
        const items = options();
        activeIndex = index;
        items.forEach((item, i) => item.classList.toggle('active', i === index));
        if (items[index]) {
            input.setAttribute('aria-activedescendant', items[index].id);
            items[index].scrollIntoView({ block: 'nearest' });
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }

    // Wrap the matching part of the name in <mark>
    function highlight(text, query) {
        const index = text.toLowerCase().indexOf(query.toLowerCase());
        if (index === -1) return escapeHtml(text);
        return escapeHtml(text.slice(0, index)) +
            `<mark>${escapeHtml(text.slice(index, index + query.length))}</mark>` +
            escapeHtml(text.slice(index + query.length));
    }

    function render(data) {
        if (!data.results.length) {
            panel.innerHTML = `<div class="suggestion-empty">${escapeHtml(t('No products match “{query}”', { query: data.query }))}</div>`;
        } else {
            panel.innerHTML = `
                <ul class="suggestion-list">
                    ${data.results.map((product, i) => `
                    <li>
                        <a href="${escapeHtml(product.url)}" class="suggestion" id="suggestion-${i}" role="option" data-suggestion>
                            <span class="suggestion-thumb">${imageHtml(product.image, product.name, '', product.art)}</span>
                            <span class="suggestion-text">
                                <span class="suggestion-name">${highlight(product.name, data.query)}</span>
                                <span class="suggestion-meta">${escapeHtml(product.category)}${product.stock === 0 ? ` · ${escapeHtml(t('Out of stock'))}` : ''}</span>
                            </span>
                            <span class="suggestion-price">${formatPrice(product.price)}</span>
                        </a>
                    </li>`).join('')}
                </ul>
                <a href="${escapeHtml(data.url)}" class="suggestion-footer" id="suggestion-all" role="option" data-suggestion data-shop-link>
                    <span>${escapeHtml(tn('See all {n} result for “{query}”', 'See all {n} results for “{query}”', data.total, { query: data.query }))}</span>
                    <i class="fas fa-arrow-right"></i>
                </a>`;
        }
        activeIndex = -1;
        show();
    }

    const fetchSuggestions = debounce(async function(query) {
        controller?.abort();
        controller = new AbortController();
        try {
            const url = `${window.APP_URLS.search_api}?q=${encodeURIComponent(query)}`;
            const data = await requestJSON(url, { signal: controller.signal });
            // Ignore answers for a query the user has already changed
            if (input.value.trim() === query) render(data);
        } catch (error) {
            if (error.name !== 'AbortError') hide();
        }
    }, 180);

    input.addEventListener('input', function() {
        const query = input.value.trim();
        if (query.length < 2) {
            controller?.abort();
            hide();
            return;
        }
        if (panel.hidden) {
            panel.innerHTML = '<div class="suggestion-loading"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
            show();
        }
        fetchSuggestions(query);
    });

    input.addEventListener('focus', function() {
        if (input.value.trim().length >= 2 && options().length) show();
    });

    input.addEventListener('keydown', function(e) {
        const items = options();
        if (panel.hidden || !items.length) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActive((activeIndex + 1) % items.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActive(activeIndex <= 0 ? items.length - 1 : activeIndex - 1);
        } else if (e.key === 'Escape') {
            e.stopPropagation();
            hide();
        }
    });

    // Enter on a highlighted suggestion opens it instead of searching
    form.addEventListener('submit', function(e) {
        const active = options()[activeIndex];
        if (!panel.hidden && active) {
            e.preventDefault();
            active.click();
        }
        hide();
    });

    panel.addEventListener('click', function(e) {
        if (e.target.closest('a')) hide();
    });

    document.addEventListener('click', function(e) {
        if (!form.contains(e.target)) hide();
    });
}

// ---------- Clickable Table Rows (admin) ----------

function initClickableRows() {
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function(e) {
            if (e.target.closest('button, a, input, select, form')) {
                return;
            }

            const href = this.getAttribute('data-href');
            if (href) {
                window.location.href = href;
            }
        });
    });
}

// ---------- Flash Messages ----------

function initFlashMessages() {
    document.querySelectorAll('.flash').forEach(flash => {
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'flash-close';
        closeBtn.setAttribute('aria-label', t('Dismiss'));
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.addEventListener('click', () => fadeOut(flash));
        flash.appendChild(closeBtn);

        // Good news goes away by itself; errors and warnings stay until dismissed
        if (flash.classList.contains('flash-success') || flash.classList.contains('flash-info')) {
            setTimeout(() => fadeOut(flash), 6000);
        }
    });
}

function fadeOut(element) {
    if (!element.isConnected || element.classList.contains('is-leaving')) return;
    element.classList.add('is-leaving');
    setTimeout(() => element.remove(), 260);
}

// ---------- Images ----------

// Broken product images become the placeholder icon (or placeholder.svg elsewhere)
function initImageFallback() {
    document.addEventListener('error', function(e) {
        const img = e.target;
        if (img.tagName !== 'IMG' || img.dataset.failed) return;
        img.dataset.failed = 'true';

        if (img.dataset.fallback === 'icon') {
            img.outerHTML = imageHtml(null, img.alt, img.className);
        } else {
            img.src = window.APP_URLS.placeholder_image;
            img.alt = 'Image not available';
        }
    }, true);
}

// Smooth-scroll buttons (without adding #hash entries to the history)
function initScrollLinks() {
    document.addEventListener('click', function(e) {
        const link = e.target.closest('[data-scroll-to]');
        const target = link && document.getElementById(link.dataset.scrollTo);
        if (target) {
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
}

// ---------- Toast Notifications ----------

const TOAST_ICONS = {
    success: 'fa-check',
    error: 'fa-exclamation',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info'
};

// action: optional { label, onClick } button shown in the toast
function showToast(message, type = 'info', duration = 4000, action = null) {
    const stack = document.getElementById('toastStack');
    if (!stack || !message) return;
    if (type === 'danger') type = 'error';

    // Keep at most 3 toasts on screen
    while (stack.children.length >= 3) {
        stack.firstElementChild.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    toast.innerHTML = `
        <span class="toast-icon"><i class="fas ${TOAST_ICONS[type] || TOAST_ICONS.info}"></i></span>
        <span class="toast-message">${escapeHtml(message)}</span>
        ${action ? `<button type="button" class="toast-action">${escapeHtml(action.label)}</button>` : ''}
        <button type="button" class="toast-close" aria-label="${escapeHtml(t('Dismiss'))}"><i class="fas fa-times"></i></button>`;

    const dismiss = () => fadeOut(toast);
    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    if (action) {
        toast.querySelector('.toast-action').addEventListener('click', () => {
            dismiss();
            action.onClick();
        });
    }
    stack.appendChild(toast);

    // Pause while hovered so there is time to click the action
    let timer = setTimeout(dismiss, duration);
    toast.addEventListener('mouseenter', () => clearTimeout(timer));
    toast.addEventListener('mouseleave', () => {
        timer = setTimeout(dismiss, 1500);
    });
}

// ---------- Modal ----------

let modalReturnFocus = null;

// Opens a modal and returns its body element so the caller can fill it in
function openModal({ title, body = '' }) {
    closeModal();
    modalReturnFocus = document.activeElement;

    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.id = 'appModal';
    backdrop.innerHTML = `
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="appModalTitle">
            <div class="modal-header">
                <h2 id="appModalTitle">${escapeHtml(title)}</h2>
                <button type="button" class="icon-btn" data-close-modal aria-label="${escapeHtml(t('Close'))}"><i class="fas fa-times"></i></button>
            </div>
            <div class="modal-body">${body}</div>
        </div>`;

    backdrop.addEventListener('click', function(e) {
        if (e.target === backdrop || e.target.closest('[data-close-modal]')) closeModal();
    });

    document.body.appendChild(backdrop);
    lockScroll(true);
    backdrop.querySelector('[data-close-modal]').focus();
    return backdrop.querySelector('.modal-body');
}

// Returns true if a modal was open
function closeModal() {
    const backdrop = document.getElementById('appModal');
    if (!backdrop) return false;
    backdrop.removeAttribute('id');
    fadeOut(backdrop);
    lockScroll(false);
    modalReturnFocus?.focus();
    return true;
}

// ---------- Form validation messages ----------

// Show (or clear, with an empty message) an error under a .form-group field
function setFieldError(field, message) {
    const group = field.closest('.form-group');
    if (!group) return;

    let error = group.querySelector('.field-error');
    group.classList.toggle('has-error', Boolean(message));
    field.setAttribute('aria-invalid', Boolean(message));

    if (message) {
        if (!error) {
            error = document.createElement('small');
            error.className = 'field-error';
            error.id = `${field.id}-error`;
            group.appendChild(error);
            field.setAttribute('aria-describedby', error.id);
        }
        error.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${escapeHtml(message)}`;
    } else if (error) {
        error.remove();
        field.removeAttribute('aria-describedby');
    }
}

// ---------- Cart ----------

function updateCartCount(count) {
    document.querySelectorAll('.cart-count').forEach(badge => {
        const changed = badge.textContent.trim() !== String(count);
        badge.textContent = count;
        badge.hidden = count <= 0;
        if (changed && count > 0) replayAnimation(badge, 'bump');
    });

    document.querySelectorAll('[data-cart-count-text]').forEach(el => {
        el.textContent = tn('{n} item', '{n} items', count);
    });

    // Dispatch event for other components
    window.dispatchEvent(new CustomEvent('cartUpdated', { detail: { count } }));
}

function updateCartItem(productId, quantity) {
    return postForm(window.APP_URLS.update_cart, { product_id: productId, quantity });
}

function removeCartItem(productId) {
    return postForm(window.APP_URLS.remove_from_cart, { product_id: productId });
}

// Fill in [data-cart-field] totals and the free shipping bar inside root
function renderCartSummary(root, cart) {
    root.querySelectorAll('[data-cart-field]').forEach(el => {
        const value = cart[el.dataset.cartField];
        const text = el.dataset.cartField === 'shipping' && value === 0 ? t('Free') : formatPrice(value);
        if (el.textContent.trim() !== text) {
            el.textContent = text;
            replayAnimation(el, 'changed');
        }
    });

    root.querySelectorAll('[data-shipping-progress]').forEach(progress => {
        const free = cart.free_shipping_remaining <= 0;
        const percent = Math.min(cart.subtotal / cart.free_shipping_threshold * 100, 100);
        progress.classList.toggle('is-free', free);
        progress.querySelector('[data-shipping-text]').innerHTML = free
            ? `<i class="fas fa-check-circle"></i> ${t("You've unlocked <strong>free shipping</strong>!")}`
            : t("You're <strong>{amount}</strong> away from free shipping", { amount: formatPrice(cart.free_shipping_remaining) });
        progress.querySelector('[data-shipping-fill]').style.width = `${percent}%`;
    });
}

// Every .add-to-cart-form (including product cards loaded later) is sent with AJAX
function initAddToCart() {
    document.addEventListener('submit', async function(e) {
        const form = e.target.closest('.add-to-cart-form');
        if (!form || !form.getAttribute('action')) return;
        e.preventDefault();

        const button = form.querySelector('button[type="submit"]');
        if (!button || button.disabled) return;

        const icon = button.querySelector('i');
        const iconClass = icon ? icon.className : '';
        const productId = form.querySelector('[name="product_id"]').value;
        button.disabled = true;
        if (icon) icon.className = 'fas fa-spinner fa-spin';

        try {
            const data = await postForm(form.action, new FormData(form));
            if (!data.success) {
                showToast(data.message, 'warning');
                return;
            }

            updateCartCount(data.cart.count);
            if (form.hasAttribute('data-open-drawer')) {
                CartDrawer.open({ cart: data.cart, highlight: productId });
            } else {
                flyToCart(form.closest('.product-card')?.querySelector('.card-image'));
                showToast(data.message, 'success', 4000, {
                    label: t('View cart'),
                    onClick: () => CartDrawer.open({ highlight: productId })
                });
            }

            // Briefly show a check mark on the button
            if (icon) icon.className = 'fas fa-check';
            button.classList.add('is-added');
            await new Promise(resolve => setTimeout(resolve, 1200));
            button.classList.remove('is-added');
        } catch (error) {
            console.error('Error adding to cart:', error);
            showToast(t('Could not add the item to your cart. Please try again.'), 'error');
        } finally {
            if (icon) icon.className = iconClass;
            button.disabled = false;
        }
    });
}

// Animate a copy of the product image into the header cart icon
function flyToCart(source) {
    const header = document.getElementById('mainHeader');
    const target = document.querySelector('#cartToggle .cart-icon');
    if (!source || !target || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    // The header may be hidden while scrolled; it slides back in
    const headerWasHidden = header?.classList.contains('header-hidden');
    header?.classList.remove('header-hidden');

    const from = source.getBoundingClientRect();
    const to = target.getBoundingClientRect();
    const toTop = to.top + (headerWasHidden ? header.offsetHeight : 0);
    if (!from.width) return;

    const clone = source.cloneNode(true);
    clone.classList.add('fly-to-cart');
    Object.assign(clone.style, {
        left: `${from.left}px`,
        top: `${from.top}px`,
        width: `${from.width}px`,
        height: `${from.height}px`
    });
    document.body.appendChild(clone);

    const dx = to.left + to.width / 2 - (from.left + from.width / 2);
    const dy = toTop + to.height / 2 - (from.top + from.height / 2);
    requestAnimationFrame(() => {
        clone.style.transform = `translate(${dx}px, ${dy}px) scale(0.08)`;
        clone.style.opacity = '0.4';
    });
    clone.addEventListener('transitionend', () => clone.remove(), { once: true });
    setTimeout(() => clone.remove(), 1000);
}

// Slide-in cart, opened from the header cart icon and after adding on a product page
const CartDrawer = {
    init() {
        this.el = document.getElementById('cartDrawer');
        if (!this.el) return;
        this.body = document.getElementById('cartDrawerBody');
        this.footer = document.getElementById('cartDrawerFooter');
        this.overlay = document.getElementById('cartDrawerOverlay');

        document.getElementById('cartToggle')?.addEventListener('click', e => {
            // On the cart page the link just goes to the page
            if (document.getElementById('cartPage') || e.metaKey || e.ctrlKey || e.shiftKey) return;
            e.preventDefault();
            this.open();
        });

        this.overlay?.addEventListener('click', () => this.close());
        this.el.addEventListener('click', e => {
            if (e.target.closest('[data-close-drawer]')) {
                this.close();
                return;
            }
            const button = e.target.closest('[data-drawer-action]');
            if (button) this.handleAction(button);
        });
    },

    isOpen() {
        return Boolean(this.el?.classList.contains('open'));
    },

    async open({ cart = null, highlight = null } = {}) {
        if (!this.el) return;
        const wasOpen = this.isOpen();
        if (!wasOpen) {
            this.returnFocus = document.activeElement;
            this.el.classList.add('open');
            this.el.setAttribute('aria-hidden', 'false');
            this.overlay?.classList.add('active');
            lockScroll(true);
            this.el.focus();
        }

        if (cart) {
            this.render(cart, { highlight, animate: !wasOpen });
            return;
        }

        this.showSkeleton();
        try {
            this.render(await requestJSON(window.APP_URLS.cart_data), { highlight, animate: true });
        } catch (error) {
            console.error('Error loading cart:', error);
            this.footer.hidden = true;
            this.body.innerHTML = `
                <div class="drawer-empty">
                    <p>${escapeHtml(t("We couldn't load your cart."))}</p>
                    <a href="${window.APP_URLS.view_cart}" class="btn btn-outline">${escapeHtml(t('Open cart page'))}</a>
                </div>`;
        }
    },

    close() {
        if (!this.isOpen()) return;
        this.el.classList.remove('open');
        this.el.setAttribute('aria-hidden', 'true');
        this.overlay?.classList.remove('active');
        lockScroll(false);
        this.returnFocus?.focus();
    },

    showSkeleton() {
        this.footer.hidden = true;
        this.body.innerHTML = `
            <div class="drawer-skeleton">
                <div class="skeleton"></div>
                <div class="skeleton-lines"><div class="skeleton" style="width: 70%"></div><div class="skeleton" style="width: 40%"></div></div>
            </div>`.repeat(3);
    },

    render(cart, { highlight = null, animate = false } = {}) {
        updateCartCount(cart.count);
        this.footer.hidden = cart.items.length === 0;

        if (!cart.items.length) {
            this.body.innerHTML = `
                <div class="drawer-empty">
                    <div class="empty-icon"><i class="fas fa-shopping-bag"></i></div>
                    <h3>${escapeHtml(t('Your cart is empty'))}</h3>
                    <p>${escapeHtml(t("Looks like you haven't added anything yet."))}</p>
                    <button type="button" class="btn btn-primary" data-close-drawer>${escapeHtml(t('Continue shopping'))}</button>
                </div>`;
            return;
        }

        this.body.innerHTML = cart.items.map((item, i) => {
            const classes = ['drawer-item'];
            if (String(item.id) === String(highlight)) classes.push('is-new');
            else if (animate) classes.push('enter');
            return `
            <div class="${classes.join(' ')}" data-product-id="${item.id}" style="animation-delay: ${animate ? i * 50 : 0}ms">
                <a href="${escapeHtml(item.url)}" class="drawer-item-media">${imageHtml(item.image, item.name, '', item.art)}</a>
                <div class="drawer-item-info">
                    <a href="${escapeHtml(item.url)}" class="drawer-item-name">${escapeHtml(item.name)}</a>
                    <span class="drawer-item-price">${escapeHtml(t('{price} each', { price: formatPrice(item.price) }))}</span>
                    <div class="drawer-qty">
                        <button type="button" class="qty-btn" data-drawer-action="decrease" aria-label="${escapeHtml(t('Decrease quantity'))}" ${item.quantity <= 1 ? 'disabled' : ''}>
                            <i class="fas fa-minus"></i>
                        </button>
                        <span class="qty-value">${item.quantity}</span>
                        <button type="button" class="qty-btn" data-drawer-action="increase" aria-label="${escapeHtml(t('Increase quantity'))}" ${item.quantity >= item.stock ? 'disabled' : ''}>
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </div>
                <div class="drawer-item-side">
                    <span class="drawer-item-total">${formatPrice(item.line_total)}</span>
                    <button type="button" class="drawer-remove" data-drawer-action="remove">${escapeHtml(t('Remove'))}</button>
                </div>
            </div>`;
        }).join('');

        renderCartSummary(this.footer, cart);
        this.body.querySelector('.is-new')?.scrollIntoView({ block: 'nearest' });
    },

    async handleAction(button) {
        const row = button.closest('.drawer-item');
        const productId = row.dataset.productId;
        const quantity = parseInt(row.querySelector('.qty-value').textContent, 10);
        const action = button.dataset.drawerAction;

        row.classList.add('is-updating');
        try {
            const data = action === 'remove'
                ? await removeCartItem(productId)
                : await updateCartItem(productId, quantity + (action === 'increase' ? 1 : -1));
            if (!data.success) showToast(data.message, 'warning');
            this.render(data.cart);
        } catch (error) {
            console.error('Error updating cart:', error);
            row.classList.remove('is-updating');
            showToast(t('Could not update your cart. Please try again.'), 'error');
        }
    }
};

// ---------- Wishlist (saved in this browser) ----------

function getWishlist() {
    return storage.get(WISHLIST_KEY, []);
}

// Fill the heart of every save button whose product is in the wishlist
function syncWishlistButtons(root = document) {
    const saved = new Set(getWishlist().map(String));
    root.querySelectorAll('[data-wishlist-toggle]').forEach(button => {
        const isSaved = saved.has(button.dataset.productId);
        button.setAttribute('aria-pressed', isSaved);
        const icon = button.querySelector('i');
        if (icon) icon.className = `${isSaved ? 'fas' : 'far'} fa-heart`;
        const label = button.querySelector('span');
        if (label) label.textContent = isSaved ? t('Saved') : t('Save for later');
    });
}

function initWishlist() {
    syncWishlistButtons();

    document.addEventListener('click', function(e) {
        const button = e.target.closest('[data-wishlist-toggle]');
        if (!button) return;
        e.preventDefault();

        const productId = Number(button.dataset.productId);
        const wishlist = getWishlist();
        const index = wishlist.indexOf(productId);
        const adding = index === -1;
        if (adding) {
            wishlist.unshift(productId);
        } else {
            wishlist.splice(index, 1);
        }
        storage.set(WISHLIST_KEY, wishlist.slice(0, 50));

        syncWishlistButtons();
        replayAnimation(button, 'pop');
        if (adding) {
            showToast(t('Saved for later'), 'success', 3000, document.getElementById('savedStrip') ? null : {
                label: t('View saved'),
                onClick: () => { window.location.href = `${window.APP_URLS.home}#savedStrip`; }
            });
        } else {
            showToast(t('Removed from saved items'), 'info', 2500);
        }
        window.dispatchEvent(new CustomEvent('wishlist:change', { detail: { wishlist } }));
    });
}

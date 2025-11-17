// base.js - Main JavaScript functionality for eShop

// Scroll-based header variables
let lastScrollY = window.scrollY;
let ticking = false;
let isHeaderHidden = false;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initScrollHeader();
    initCategoriesSidebar();
    initUserDropdown();
    initLanguageSelector();
    initClickableRows();
    initCartFunctionality();
    initSearchEnhancements();
    initFlashMessages();
    initMobileMenu();
    initImageLoading();
});

// Scroll-based Header Functionality
function initScrollHeader() {
    const header = document.querySelector('.main-header');
    if (!header) return;

    const scrollThreshold = 100;
    const scrollDebounceDelay = 100;

    function updateHeader() {
        const currentScrollY = window.scrollY;
        
        if (currentScrollY > scrollThreshold) {
            if (currentScrollY > lastScrollY && !isHeaderHidden) {
                header.classList.add('header-hidden');
                header.classList.add('header-scrolled');
                isHeaderHidden = true;
            } else if (currentScrollY < lastScrollY && isHeaderHidden) {
                header.classList.remove('header-hidden');
                header.classList.add('header-scrolled');
                isHeaderHidden = false;
            }
        } else {
            header.classList.remove('header-hidden');
            header.classList.remove('header-scrolled');
            isHeaderHidden = false;
        }
        
        lastScrollY = currentScrollY;
        ticking = false;
    }

    function onScroll() {
        if (!ticking) {
            requestAnimationFrame(updateHeader);
            ticking = true;
        }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('wheel', onScroll, { passive: true });

    document.addEventListener('mousemove', function(e) {
        if (e.clientY < 100 && isHeaderHidden) {
            header.classList.remove('header-hidden');
            isHeaderHidden = false;
        }
    });

    const categoriesSidebar = document.getElementById('categoriesSidebar');
    if (categoriesSidebar) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    if (categoriesSidebar.classList.contains('open')) {
                        header.classList.remove('header-hidden');
                        isHeaderHidden = false;
                    }
                }
            });
        });
        
        observer.observe(categoriesSidebar, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    const interactiveElements = document.querySelectorAll('.header-search-input, .categories-search-btn, .user-menu-btn, .language-btn, .cart-link');
    interactiveElements.forEach(element => {
        element.addEventListener('focus', function() {
            if (isHeaderHidden) {
                header.classList.remove('header-hidden');
                isHeaderHidden = false;
            }
        });
    });
}

// Categories Sidebar Functionality
function initCategoriesSidebar() {
    const categoriesToggle = document.getElementById('categoriesToggle');
    const categoriesSidebar = document.getElementById('categoriesSidebar');
    const closeCategories = document.getElementById('closeCategories');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const categoriesList = document.getElementById('categoriesList');
    
    if (!categoriesToggle || !categoriesSidebar) return;
    
    populateCategoriesSidebar();
    
    categoriesToggle.addEventListener('click', function() {
        categoriesSidebar.classList.add('open');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        document.querySelector('.main-header').classList.remove('header-hidden');
        isHeaderHidden = false;
    });
    
    if (closeCategories) {
        closeCategories.addEventListener('click', closeCategoriesSidebar);
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeCategoriesSidebar);
    }
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && categoriesSidebar.classList.contains('open')) {
            closeCategoriesSidebar();
        }
    });
    
    function closeCategoriesSidebar() {
        categoriesSidebar.classList.remove('open');
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('active');
        }
        document.body.style.overflow = '';
    }
    
    function populateCategoriesSidebar() {
        const categoriesData = document.getElementById('categories-data');
        
        if (categoriesData && categoriesList) {
            try {
                const categories = JSON.parse(categoriesData.textContent);
                
                categoriesList.innerHTML = '';
                
                // Add "All Categories" item
                const allCategoriesItem = document.createElement('button');
                allCategoriesItem.className = 'category-sidebar-item active';
                allCategoriesItem.textContent = 'All Categories';
                allCategoriesItem.addEventListener('click', function() {
                    closeCategoriesSidebar();
                    window.location.href = window.APP_URLS.home;
                });
                categoriesList.appendChild(allCategoriesItem);
                
                // Populate categories
                categories.forEach(category => {
                    const categoryItem = document.createElement('button');
                    categoryItem.className = 'category-sidebar-item';
                    categoryItem.textContent = category;
                    categoryItem.addEventListener('click', function() {
                        closeCategoriesSidebar();
                        // Use proper URL encoding for the category
                        const categoryParam = encodeURIComponent(category);
                        window.location.href = `${window.APP_URLS.home}?category=${categoryParam}`;
                    });
                    categoriesList.appendChild(categoryItem);
                });
                
                console.log(`Loaded ${categories.length} categories into sidebar`);
            } catch (e) {
                console.error('Error loading categories:', e);
                categoriesList.innerHTML = '<div class="error-state">Error loading categories</div>';
            }
        } else {
            categoriesList.innerHTML = '<div class="loading-state">Loading categories...</div>';
        }
    }
}

// User Dropdown - Click to open
function initUserDropdown() {
    const userMenuToggle = document.getElementById('userMenuToggle');
    const userDropdown = document.getElementById('userDropdown');
    const userDropdownContainer = document.querySelector('.user-dropdown');
    
    if (userMenuToggle && userDropdown && userDropdownContainer) {
        userMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            userDropdownContainer.classList.toggle('active');
        });
        
        document.addEventListener('click', function(e) {
            if (!userDropdownContainer.contains(e.target)) {
                userDropdownContainer.classList.remove('active');
            }
        });
        
        userDropdown.addEventListener('click', function(e) {
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                userDropdownContainer.classList.remove('active');
            }
        });
    }
}

// Language Selector
function initLanguageSelector() {
    const languageSelector = document.querySelector('.language-selector');
    const languageBtn = document.querySelector('.language-btn');
    const languageOptions = document.querySelectorAll('.language-option');
    
    if (languageBtn && languageSelector) {
        languageBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            languageSelector.classList.toggle('active');
        });
        
        document.addEventListener('click', function(e) {
            if (!languageSelector.contains(e.target)) {
                languageSelector.classList.remove('active');
            }
        });
        
        languageOptions.forEach(option => {
            option.addEventListener('click', function() {
                const lang = this.getAttribute('data-lang');
                changeLanguage(lang);
                languageSelector.classList.remove('active');
            });
        });
    }
}

function changeLanguage(lang) {
    console.log('Changing language to:', lang);
    showToast(`Changing language to ${getLanguageName(lang)}...`, 'info');
    
    setTimeout(() => {
        showToast(`Language changed to ${getLanguageName(lang)}`, 'success');
        const languageBtnText = document.querySelector('.language-btn span');
        if (languageBtnText) {
            languageBtnText.textContent = lang.toUpperCase();
        }
        
        document.documentElement.lang = lang;
    }, 1000);
}

function getLanguageName(lang) {
    const languages = {
        'en': 'English',
        'el': 'Ελληνικά',
        'de': 'Deutsch'
    };
    return languages[lang] || lang.toUpperCase();
}

// Clickable Table Rows
function initClickableRows() {
    document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', function(e) {
            if (isInteractiveElement(e.target)) {
                return;
            }
            
            const href = this.getAttribute('data-href');
            if (href) {
                window.location.href = href;
            }
        });
        
        row.style.cursor = 'pointer';
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f8fafc';
        });
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    function isInteractiveElement(element) {
        return element.tagName === 'BUTTON' || 
               element.tagName === 'A' || 
               element.tagName === 'INPUT' ||
               element.tagName === 'SELECT' ||
               element.tagName === 'FORM' ||
               element.closest('button') || 
               element.closest('a') ||
               element.closest('input') ||
               element.closest('select') ||
               element.closest('form');
    }
}

// Cart Functionality
function initCartFunctionality() {
    updateCartCountDisplay();
    
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
        form.addEventListener('submit', handleAddToCart);
    });
    
    document.querySelectorAll('.quantity-btn').forEach(btn => {
        btn.addEventListener('click', handleQuantityChange);
    });
    
    initCartQuantityControls();
}

function handleAddToCart(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const productId = formData.get('product_id');
    const quantity = formData.get('quantity') || 1;
    
    if (form.querySelector('button:disabled')) {
        showToast('This product is out of stock', 'warning');
        return;
    }
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    const originalDisabled = submitBtn.disabled;
    
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
    submitBtn.disabled = true;
    
    // Use the form's action attribute or fall back to APP_URLS
    const url = form.action || window.APP_URLS.add_to_cart;
    
    fetch(url, {
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
        if (data.success) {
            updateCartCount(data.cart_count);
            showToast(data.message, 'success');
            updateProductStockDisplay(productId, quantity);
            
            if (window.location.pathname.includes('/cart')) {
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            showToast(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error adding to cart:', error);
        showToast('Error adding item to cart. Please try again.', 'error');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = originalDisabled;
    });
}

function handleQuantityChange(e) {
    const btn = e.currentTarget;
    const form = btn.closest('form');
    
    if (form) {
        form.submit();
    }
}

function initCartQuantityControls() {
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const form = this.closest('form');
            if (form && this.value > 0) {
                form.submit();
            }
        });
    });
}

function updateCartCount(count) {
    const cartCountElement = document.querySelector('.cart-count');
    
    if (cartCountElement) {
        if (count > 0) {
            cartCountElement.textContent = count;
            cartCountElement.style.display = 'flex';
        } else {
            cartCountElement.style.display = 'none';
        }
    }
    
    const mobileCartCount = document.querySelector('.mobile-cart-count');
    if (mobileCartCount) {
        mobileCartCount.textContent = count;
    }
    
    window.dispatchEvent(new CustomEvent('cartUpdated', { detail: { count } }));
}

function updateCartCountDisplay() {
    const cartCountElement = document.querySelector('.cart-count');
    if (cartCountElement) {
        const count = parseInt(cartCountElement.textContent) || 0;
        if (count > 0) {
            cartCountElement.style.display = 'flex';
        } else {
            cartCountElement.style.display = 'none';
        }
    }
}

function updateProductStockDisplay(productId, quantity) {
    const stockElement = document.querySelector(`[data-product-id="${productId}"] .stock-quantity`);
    if (stockElement) {
        const currentStock = parseInt(stockElement.textContent);
        const newStock = currentStock - quantity;
        stockElement.textContent = newStock;
        
        if (newStock === 0) {
            stockElement.classList.add('out-of-stock');
            stockElement.classList.remove('low-stock');
            const addToCartBtn = document.querySelector(`[data-product-id="${productId}"] .add-to-cart-form button`);
            if (addToCartBtn) {
                addToCartBtn.disabled = true;
                addToCartBtn.innerHTML = '<i class="fas fa-times"></i> Out of Stock';
            }
        } else if (newStock < 10) {
            stockElement.classList.add('low-stock');
            stockElement.classList.remove('out-of-stock');
        } else {
            stockElement.classList.remove('low-stock', 'out-of-stock');
        }
    }
}

// Search Enhancements
function initSearchEnhancements() {
    const searchInput = document.querySelector('.header-search-input');
    const searchForm = document.querySelector('.header-search-form');
    
    if (searchInput && searchForm) {
        searchInput.addEventListener('input', debounce(handleSearchInput, 300));
        
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                searchForm.submit();
            }
        });
    }
    
    initAdminFilters();
}

function handleSearchInput(e) {
    const query = e.target.value.trim();
    
    if (query.length > 2) {
        console.log('Search query:', query);
    }
}

function initAdminFilters() {
    const stockFilter = document.getElementById('stockFilter');
    if (stockFilter) {
        stockFilter.addEventListener('change', function() {
            filterProductsTable(this.value);
        });
    }
    
    const productSort = document.getElementById('productSortBy');
    if (productSort) {
        productSort.addEventListener('change', function() {
            sortProductsTable(this.value);
        });
    }
    
    const orderStatusFilter = document.getElementById('orderStatusFilter');
    if (orderStatusFilter) {
        orderStatusFilter.addEventListener('change', function() {
            filterOrdersTable(this.value);
        });
    }
    
    const orderSort = document.getElementById('orderSortBy');
    if (orderSort) {
        orderSort.addEventListener('change', function() {
            sortOrdersTable(this.value);
        });
    }
}

function filterProductsTable(stockFilter) {
    const rows = document.querySelectorAll('#productsTableBody .data-row');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const stockQuantity = parseInt(row.querySelector('.stock-quantity').textContent);
        let showRow = true;
        
        switch (stockFilter) {
            case 'in_stock':
                showRow = stockQuantity > 0;
                break;
            case 'low_stock':
                showRow = stockQuantity > 0 && stockQuantity < 10;
                break;
            case 'out_of_stock':
                showRow = stockQuantity === 0;
                break;
            case 'all':
            default:
                showRow = true;
        }
        
        row.style.display = showRow ? '' : 'none';
        if (showRow) visibleCount++;
    });
    
    updateVisibleCount(visibleCount, rows.length);
}

function sortProductsTable(sortBy) {
    const tbody = document.getElementById('productsTableBody');
    const rows = Array.from(tbody.querySelectorAll('.data-row'));
    
    rows.sort((a, b) => {
        switch (sortBy) {
            case 'id_asc':
                return getProductId(a) - getProductId(b);
            case 'id_desc':
                return getProductId(b) - getProductId(a);
            case 'name_asc':
                return getProductName(a).localeCompare(getProductName(b));
            case 'name_desc':
                return getProductName(b).localeCompare(getProductName(a));
            case 'price_asc':
                return getProductPrice(a) - getProductPrice(b);
            case 'price_desc':
                return getProductPrice(b) - getProductPrice(a);
            default:
                return 0;
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

function getProductId(row) {
    return parseInt(row.getAttribute('data-id'));
}

function getProductName(row) {
    return row.getAttribute('data-name') || '';
}

function getProductPrice(row) {
    return parseFloat(row.getAttribute('data-price')) || 0;
}

function filterOrdersTable(statusFilter) {
    const rows = document.querySelectorAll('#ordersTableBody .data-row');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const status = row.getAttribute('data-status');
        const showRow = statusFilter === 'all' || status === statusFilter;
        row.style.display = showRow ? '' : 'none';
        if (showRow) visibleCount++;
    });
    
    updateVisibleCount(visibleCount, rows.length, 'orders');
}

function sortOrdersTable(sortBy) {
    const tbody = document.getElementById('ordersTableBody');
    const rows = Array.from(tbody.querySelectorAll('.data-row'));
    
    rows.sort((a, b) => {
        const aId = parseInt(a.getAttribute('data-id'));
        const bId = parseInt(b.getAttribute('data-id'));
        
        switch (sortBy) {
            case 'id_asc':
                return aId - bId;
            case 'id_desc':
                return bId - aId;
            default:
                return 0;
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

function updateVisibleCount(visible, total, type = 'products') {
    console.log(`${type}: ${visible} of ${total} visible`);
}

// Flash Messages
function initFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');
    
    flashMessages.forEach(flash => {
        if (flash.classList.contains('flash-success')) {
            setTimeout(() => {
                fadeOut(flash);
            }, 5000);
        }
        
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.className = 'flash-close';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            margin-left: auto;
            padding: 0;
            opacity: 0.7;
            transition: opacity 0.2s ease;
        `;
        closeBtn.addEventListener('click', () => fadeOut(flash));
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.opacity = '1';
        });
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.opacity = '0.7';
        });
        
        flash.appendChild(closeBtn);
    });
}

function fadeOut(element) {
    element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    element.style.opacity = '0';
    element.style.transform = 'translateY(-10px)';
    setTimeout(() => {
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }, 300);
}

// Mobile Menu
function initMobileMenu() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const mainNav = document.querySelector('.main-nav');
    
    if (mobileMenuBtn && mainNav) {
        mobileMenuBtn.addEventListener('click', function() {
            mainNav.classList.toggle('mobile-open');
            this.classList.toggle('active');
            document.body.style.overflow = mainNav.classList.contains('mobile-open') ? 'hidden' : '';
        });
    }
    
    document.addEventListener('click', function(e) {
        if (mainNav && mainNav.classList.contains('mobile-open') && 
            !mainNav.contains(e.target) && 
            !e.target.closest('.mobile-menu-btn')) {
            mainNav.classList.remove('mobile-open');
            if (mobileMenuBtn) {
                mobileMenuBtn.classList.remove('active');
            }
            document.body.style.overflow = '';
        }
    });
    
    const mobileLinks = document.querySelectorAll('.main-nav a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (mainNav.classList.contains('mobile-open')) {
                mainNav.classList.remove('mobile-open');
                if (mobileMenuBtn) {
                    mobileMenuBtn.classList.remove('active');
                }
                document.body.style.overflow = '';
            }
        });
    });
}

// Image Loading and Error Handling
function initImageLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.getAttribute('data-src');
                img.removeAttribute('data-src');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
    
    document.addEventListener('error', function(e) {
        if (e.target.tagName === 'IMG') {
            e.target.src = '/static/images/placeholder.png';
            e.target.alt = 'Image not available';
            e.target.style.opacity = '0.7';
        }
    }, true);
}

// Toast Notifications
function showToast(message, type = 'info', duration = 5000) {
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    });
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        max-width: 350px;
        animation: slideInRight 0.3s ease;
        border-left: 4px solid ${getToastColor(type)};
    `;
    
    const icon = document.createElement('i');
    switch (type) {
        case 'success':
            icon.className = 'fas fa-check-circle';
            icon.style.color = '#059669';
            break;
        case 'error':
            icon.className = 'fas fa-exclamation-circle';
            icon.style.color = '#dc2626';
            break;
        case 'warning':
            icon.className = 'fas fa-exclamation-triangle';
            icon.style.color = '#d97706';
            break;
        default:
            icon.className = 'fas fa-info-circle';
            icon.style.color = '#3b82f6';
    }
    
    const messageEl = document.createElement('span');
    messageEl.textContent = message;
    messageEl.style.flex = '1';
    messageEl.style.fontSize = '0.9rem';
    messageEl.style.lineHeight = '1.4';
    
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: #6b7280;
        cursor: pointer;
        padding: 0.25rem;
        border-radius: 4px;
        transition: background-color 0.2s ease;
    `;
    closeBtn.addEventListener('click', () => fadeOut(toast));
    closeBtn.addEventListener('mouseenter', () => {
        closeBtn.style.backgroundColor = '#f3f4f6';
    });
    closeBtn.addEventListener('mouseleave', () => {
        closeBtn.style.backgroundColor = 'transparent';
    });
    
    toast.appendChild(icon);
    toast.appendChild(messageEl);
    toast.appendChild(closeBtn);
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) {
            fadeOut(toast);
        }
    }, duration);
}

function getToastColor(type) {
    const colors = {
        'success': '#059669',
        'error': '#dc2626',
        'warning': '#d97706',
        'info': '#3b82f6'
    };
    return colors[type] || '#3b82f6';
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(price);
}

function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success', 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

// Error boundary for the entire application
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    e.preventDefault();
});

// Add CSS for animations and additional styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideInDown {
        from {
            transform: translateY(-100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .flash-close:hover {
        opacity: 1 !important;
    }
    
    .mobile-menu-btn {
        display: none;
    }
    
    .loading-state, .error-state {
        padding: 2rem;
        text-align: center;
        color: #6b7280;
    }
    
    .error-state {
        color: #dc2626;
    }
    
    @media (max-width: 768px) {
        .mobile-menu-btn {
            display: block;
        }
        
        .toast {
            right: 10px;
            left: 10px;
            max-width: none;
        }
    }
    
    button, a, input, select {
        transition: all 0.2s ease;
    }
    
    button:focus-visible, 
    a:focus-visible, 
    input:focus-visible, 
    select:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
    }
`;
document.head.appendChild(style);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showToast,
        updateCartCount,
        formatPrice,
        formatDate,
        debounce,
        throttle
    };
}

// Initialize any third-party integrations
function initAnalytics() {
    console.log('Analytics initialized');
}

setTimeout(() => {
    initAnalytics();
}, 1000);

console.log('eShop JavaScript loaded successfully!');
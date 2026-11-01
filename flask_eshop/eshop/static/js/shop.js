// Shop Page JavaScript: filter, sort, search and paginate products without reloading
// the page, and show saved / recently viewed products from this browser
document.addEventListener('DOMContentLoaded', function() {
    const results = document.getElementById('shopResults');
    const filtersForm = document.getElementById('shopFilters');
    if (!results || !filtersForm) return;

    // Filter values that are the default, left out of URLs (matches FILTER_DEFAULTS in main.py)
    const DEFAULTS = { stock: 'all', sort: 'newest' };
    let controller = null;
    let currentSearch = window.location.search;

    function shopUrl(params) {
        const clean = new URLSearchParams();
        params.forEach((value, key) => {
            value = String(value).trim();
            if (value && DEFAULTS[key] !== value) clean.set(key, value);
        });
        const query = clean.toString();
        return window.APP_URLS.home + (query ? `?${query}` : '');
    }

    // Fetch the results block for a URL and swap it in
    async function loadResults(url, { push = true } = {}) {
        controller?.abort();
        const request = controller = new AbortController();
        results.classList.add('is-loading');
        setLoading(true);

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                // Don't let this partial page replace the full page in the browser cache
                cache: 'no-store',
                signal: request.signal
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            results.innerHTML = await response.text();

            const parsed = new URL(url, window.location.origin);
            currentSearch = parsed.search;
            if (push) history.pushState({ shop: true }, '', parsed.pathname + parsed.search);
            syncControls(parsed.searchParams);
            syncWishlistButtons(results);
            scrollToResults();
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Error loading products:', error);
            showToast(t('Could not load products. Please try again.'), 'error');
        } finally {
            setLoading(false);
            if (request === controller) results.classList.remove('is-loading');
        }
    }

    // Bring the results into view if the user has scrolled past them
    function scrollToResults() {
        const top = document.getElementById('resultsTop');
        if (top && top.getBoundingClientRect().top < 0) {
            top.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Make the filter controls, chips and search box match the URL
    function syncControls(params) {
        const fields = filtersForm.elements;
        fields.q.value = params.get('q') || '';
        fields.category.value = params.get('category') || '';
        fields.stock.value = params.get('stock') || 'all';
        fields.sort.value = params.get('sort') || 'newest';
        ['min_price', 'max_price'].forEach(name => {
            if (document.activeElement !== fields[name]) fields[name].value = params.get(name) || '';
        });

        const category = params.get('category') || '';
        document.querySelectorAll('[data-shop-link][data-category]').forEach(link => {
            link.classList.toggle('active', link.dataset.category === category);
        });

        const searchInput = document.getElementById('headerSearchInput');
        if (searchInput && document.activeElement !== searchInput) {
            searchInput.value = params.get('q') || '';
        }
    }

    function applyFilters() {
        loadResults(shopUrl(new FormData(filtersForm)));
    }

    // Selects apply right away, price boxes once the user stops typing
    filtersForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
    });
    filtersForm.addEventListener('change', function(e) {
        if (e.target.tagName === 'SELECT') applyFilters();
    });
    const applyPriceFilter = debounce(applyFilters, 600);
    filtersForm.addEventListener('input', function(e) {
        if (e.target.type === 'number') applyPriceFilter();
    });

    // Category chips, sidebar categories, filter pills, pagination and "see all results"
    document.addEventListener('click', function(e) {
        const link = e.target.closest('a[data-shop-link]');
        if (!link || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();

        if (link.hasAttribute('data-category')) {
            // Picking a category keeps the other filters
            const params = new URLSearchParams(window.location.search);
            params.delete('page');
            params.set('category', link.dataset.category);
            loadResults(shopUrl(params));
        } else {
            loadResults(link.href);
        }
    });

    // Header search: a new search keeps only the sort order
    const searchForm = document.getElementById('headerSearchForm');
    searchForm?.addEventListener('submit', function(e) {
        if (e.defaultPrevented) return;
        e.preventDefault();
        const params = new URLSearchParams();
        params.set('q', searchForm.elements.q.value);
        params.set('sort', filtersForm.elements.sort.value);
        loadResults(shopUrl(params));
        searchForm.elements.q.blur();
    });

    // Back / forward buttons
    window.addEventListener('popstate', function() {
        // Ignore history entries that only changed the #hash
        if (window.location.search === currentSearch) return;
        loadResults(window.location.href, { push: false });
    });
});

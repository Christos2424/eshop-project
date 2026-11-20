// Admin Products Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Products Filtering and Sorting
    const productsTableBody = document.getElementById('productsTableBody');
    if (productsTableBody) {
        let productRows = Array.from(productsTableBody.querySelectorAll('.data-row'));

        let activeProductFilters = {
            stock: 'all',
            sort: 'id_asc'
        };

        // Products event listeners - automatic filtering
        document.getElementById('stockFilter')?.addEventListener('change', applyProductFilters);
        document.getElementById('productSortBy')?.addEventListener('change', applyProductFilters);

        function applyProductFilters() {
            // Get current filter values
            activeProductFilters.stock = document.getElementById('stockFilter').value;
            activeProductFilters.sort = document.getElementById('productSortBy').value;

            let filteredRows = [...productRows];

            // Apply stock filter
            if (activeProductFilters.stock !== 'all') {
                filteredRows = filteredRows.filter(row => {
                    const stock = parseInt(row.dataset.stock);
                    if (activeProductFilters.stock === 'in_stock') return stock > 0;
                    if (activeProductFilters.stock === 'low_stock') return stock > 0 && stock < 10;
                    if (activeProductFilters.stock === 'out_of_stock') return stock === 0;
                    return true;
                });
            }

            // Apply sorting
            filteredRows.sort((a, b) => {
                switch (activeProductFilters.sort) {
                    case 'id_asc':
                        return parseInt(a.dataset.id) - parseInt(b.dataset.id);
                    case 'id_desc':
                        return parseInt(b.dataset.id) - parseInt(a.dataset.id);
                    case 'name_asc':
                        return a.dataset.name.localeCompare(b.dataset.name);
                    case 'name_desc':
                        return b.dataset.name.localeCompare(a.dataset.name);
                    case 'price_asc':
                        return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
                    case 'price_desc':
                        return parseFloat(b.dataset.price) - parseFloat(a.dataset.price);
                    default:
                        return parseInt(a.dataset.id) - parseInt(b.dataset.id);
                }
            });

            // Update table
            updateProductsTable(filteredRows);
        }

        function updateProductsTable(rows) {
            productsTableBody.innerHTML = '';
            if (rows.length === 0) {
                productsTableBody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="7">
                            <div class="empty-state">
                                <i class="fas fa-search"></i>
                                <h3>${escapeHtml(t('No Products Match Your Filters'))}</h3>
                                <p>${escapeHtml(t('Try adjusting your filter criteria'))}</p>
                            </div>
                        </td>
                    </tr>
                `;
            } else {
                rows.forEach(row => productsTableBody.appendChild(row));
            }
        }

        // Delete without reloading: the row slides out and the counters update
        // (data-confirm in base.js has already asked before the form submits)
        productsTableBody.addEventListener('submit', async function(e) {
            const form = e.target.closest('.action-form');
            const row = form && form.closest('.data-row');
            if (!row) return;
            e.preventDefault();

            row.classList.add('is-updating');
            try {
                const { messages } = await submitFormInBackground(form);
                if (!toastMessages(messages)) return;

                productRows = productRows.filter(r => r !== row);
                updateStats();
                row.classList.add('is-removing');
                setTimeout(() => {
                    row.remove();
                    if (!productRows.length) applyProductFilters();
                }, 300);
            } catch (error) {
                console.error('Error deleting product:', error);
                showToast(t('An unexpected error occurred. Please try again.'), 'error');
            } finally {
                row.classList.remove('is-updating');
            }
        });

        function updateStats() {
            const stock = productRows.map(r => parseInt(r.dataset.stock, 10));
            const counts = {
                total: stock.length,
                in_stock: stock.filter(n => n > 0).length,
                out_of_stock: stock.filter(n => n === 0).length,
                low_stock: stock.filter(n => n > 0 && n < 10).length
            };
            document.querySelectorAll('[data-stat]').forEach(stat => {
                const value = String(counts[stat.dataset.stat]);
                if (stat.textContent !== value) {
                    stat.textContent = value;
                    replayAnimation(stat, 'changed');
                }
            });
        }

        // Initialize filters on page load
        applyProductFilters();
    }
});

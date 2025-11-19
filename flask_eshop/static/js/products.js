// Product Detail Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Quantity Controls
    function decreaseQuantity() {
        const input = document.getElementById('quantity');
        if (parseInt(input.value) > 1) {
            input.value = parseInt(input.value) - 1;
        }
    }

    function increaseQuantity() {
        const input = document.getElementById('quantity');
        const max = parseInt(input.max);
        if (parseInt(input.value) < max) {
            input.value = parseInt(input.value) + 1;
        }
    }

    // Tab Functionality
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    if (tabBtns.length > 0) {
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const tabId = this.dataset.tab;
                
                // Remove active class from all buttons and panes
                tabBtns.forEach(b => b.classList.remove('active'));
                tabPanes.forEach(p => p.classList.remove('active'));
                
                // Add active class to current button and pane
                this.classList.add('active');
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    // Add to Cart Animation for product detail page
    const addToCartForm = document.querySelector('.add-to-cart-form');
    if (addToCartForm) {
        addToCartForm.addEventListener('submit', function(e) {
            const button = this.querySelector('.btn-add-to-cart');
            const originalText = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
            button.disabled = true;
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 1000);
        });
    }

    // Admin Products Page Filtering and Sorting
    const productsTableBody = document.getElementById('productsTableBody');
    if (productsTableBody) {
        const productRows = Array.from(productsTableBody.querySelectorAll('.data-row'));
        
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
                                <h3>No Products Match Your Filters</h3>
                                <p>Try adjusting your filter criteria</p>
                            </div>
                        </td>
                    </tr>
                `;
            } else {
                rows.forEach(row => productsTableBody.appendChild(row));
            }
        }

        // Initialize filters on page load
        applyProductFilters();
    }
});

// Expose functions for global use (for inline event handlers in product.html)
window.decreaseQuantity = function() {
    const input = document.getElementById('quantity');
    if (parseInt(input.value) > 1) {
        input.value = parseInt(input.value) - 1;
    }
};

window.increaseQuantity = function() {
    const input = document.getElementById('quantity');
    const max = parseInt(input.max);
    if (parseInt(input.value) < max) {
        input.value = parseInt(input.value) + 1;
    }
};
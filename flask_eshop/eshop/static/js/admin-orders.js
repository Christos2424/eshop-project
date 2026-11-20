// Admin Orders Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const allRows = Array.from(document.querySelectorAll('#ordersTableBody .data-row'));

    // Orders Filtering and Sorting
    const ordersTableBody = document.getElementById('ordersTableBody');
    if (ordersTableBody) {
        const orderRows = Array.from(ordersTableBody.querySelectorAll('.data-row'));
        
        let activeOrderFilters = {
            status: 'all',
            sort: 'id_asc'
        };

        // Orders event listeners - automatic filtering
        document.getElementById('orderStatusFilter')?.addEventListener('change', applyOrderFilters);
        document.getElementById('orderSortBy')?.addEventListener('change', applyOrderFilters);

        function applyOrderFilters() {
            // Get current filter values
            activeOrderFilters.status = document.getElementById('orderStatusFilter').value;
            activeOrderFilters.sort = document.getElementById('orderSortBy').value;
            
            let filteredRows = [...orderRows];
            
            // Apply status filter
            if (activeOrderFilters.status !== 'all') {
                filteredRows = filteredRows.filter(row => {
                    return row.dataset.status === activeOrderFilters.status;
                });
            }
            
            // Apply sorting
            filteredRows.sort((a, b) => {
                const aId = parseInt(a.dataset.id);
                const bId = parseInt(b.dataset.id);
                
                switch (activeOrderFilters.sort) {
                    case 'id_asc':
                        return aId - bId;
                    case 'id_desc':
                        return bId - aId;
                    default:
                        return aId - bId;
                }
            });
            
            // Update table
            updateOrdersTable(filteredRows);
        }

        function updateOrdersTable(rows) {
            ordersTableBody.innerHTML = '';
            if (rows.length === 0) {
                ordersTableBody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="7">
                            <div class="empty-state">
                                <i class="fas fa-search"></i>
                                <h3>${escapeHtml(t('No Orders Match Your Filters'))}</h3>
                                <p>${escapeHtml(t('Try adjusting your filter criteria'))}</p>
                            </div>
                        </td>
                    </tr>
                `;
            } else {
                rows.forEach(row => ordersTableBody.appendChild(row));
            }
        }

        // Initialize filters on page load
        if (document.getElementById('orderStatusFilter')) {
            applyOrderFilters();
        }
    }

    // Status buttons: update the order, then the row and the counters in place (no reload)
    document.addEventListener('click', async function(e) {
        const button = e.target.closest('[data-set-status]');
        const row = button && button.closest('.data-row');
        if (!row) return;

        const orderId = row.dataset.id;
        const status = button.dataset.setStatus;
        const statusText = statusLabel(status);
        if (!confirm(t('Are you sure you want to update order #{id} to "{status}"?', { id: orderId, status: statusText }))) return;

        row.classList.add('is-updating');
        try {
            const response = await fetch(`/admin/update_order/${orderId}`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ status })
            });
            const data = await response.json();
            if (!data.success) {
                showToast(data.error || t('Error updating order status'), 'error');
                return;
            }
            setRowStatus(row, status);
            showToast(t('Order #{id} status updated to {status}', { id: orderId, status: statusText }), 'success');
        } catch (error) {
            console.error('Error updating order status:', error);
            showToast(t('Error updating order status'), 'error');
        } finally {
            row.classList.remove('is-updating');
        }
    });

    function statusLabel(status) {
        return t(status.charAt(0).toUpperCase() + status.slice(1));
    }

    function setRowStatus(row, status) {
        row.dataset.status = status;
        const pill = row.querySelector('.order-status');
        pill.className = `order-status status-${status}`;
        pill.textContent = statusLabel(status);
        replayAnimation(pill, 'changed');

        row.querySelectorAll('[data-show-for]').forEach(action => {
            action.hidden = !action.dataset.showFor.split(' ').includes(status);
        });

        // Count every order, including rows the filter has taken out of the table
        document.querySelectorAll('[data-stat]').forEach(stat => {
            stat.textContent = allRows.filter(r => r.dataset.status === stat.dataset.stat).length;
        });

        // Hide the row if it no longer matches the status filter
        const filter = document.getElementById('orderStatusFilter');
        if (filter && filter.value !== 'all' && filter.value !== status) {
            filter.dispatchEvent(new Event('change'));
        }
    }
});
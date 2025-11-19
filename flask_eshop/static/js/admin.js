// Admin Orders Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
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
                                <h3>No Orders Match Your Filters</h3>
                                <p>Try adjusting your filter criteria</p>
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

    // Order management functions
    window.viewOrderDetails = function(orderId) {
        alert('Viewing details for order #' + orderId);
        // In a real implementation, this would open a modal or redirect to order details
        // window.location.href = `/order/${orderId}`;
    };

    window.updateOrderStatus = function(orderId, status) {
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        if (confirm(`Are you sure you want to update order #${orderId} to "${statusText}"?`)) {
            // In a real implementation, this would make an AJAX call to update the order status
            fetch(`/admin/update_order/${orderId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: status })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`Order #${orderId} status updated to ${status}`);
                    location.reload();
                } else {
                    alert('Error updating order status');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating order status');
            });
        }
    };
});
// Order pages (customer and admin): order details modal and status filter

// Also called from onclick handlers in admin/orders.html
window.viewOrderDetails = async function(orderId) {
    const body = openModal({
        title: t('Order #{id}', { id: orderId }),
        body: '<div class="skeleton" style="height: 72px; margin-bottom: 12px"></div><div class="skeleton" style="height: 72px"></div>'
    });

    try {
        const data = await requestJSON(window.APP_URLS.order_items.replace('/0/', `/${orderId}/`));
        if (!data.success) throw new Error(data.error);
        body.innerHTML = renderOrderDetails(data);
    } catch (error) {
        console.error('Error loading order:', error);
        body.innerHTML = `<p class="modal-error">${escapeHtml(t("We couldn't load this order. Please try again."))}</p>`;
    }
};

function renderOrderDetails({ order, items }) {
    const status = t(order.status.charAt(0).toUpperCase() + order.status.slice(1));
    const itemCount = items.reduce((sum, item) => sum + item.quantity, 0);
    // Order totals include shipping and tax; older orders stored only the items' total
    const itemsTotal = items.reduce((sum, item) => sum + item.line_total, 0);
    const extras = order.total - itemsTotal;
    const breakdown = extras > 0.005 ? `
        <div class="order-detail-line"><span>${escapeHtml(t('Subtotal'))}</span><span>${formatPrice(itemsTotal)}</span></div>
        <div class="order-detail-line"><span>${escapeHtml(t('Shipping & tax'))}</span><span>${formatPrice(extras)}</span></div>` : '';
    return `
        <div class="order-detail-meta">
            <span class="status-pill status-${escapeHtml(order.status)}">${escapeHtml(status)}</span>
            <span><i class="far fa-calendar"></i> ${escapeHtml(order.created_at.slice(0, 16))}</span>
            <span>${escapeHtml(tn('{n} item', '{n} items', itemCount))}</span>
        </div>
        <ul class="order-detail-items">
            ${items.map(item => `
            <li class="order-detail-item">
                <a href="${escapeHtml(item.url)}" class="order-detail-media">${imageHtml(item.image, item.name, '', item.art)}</a>
                <div class="order-detail-info">
                    <a href="${escapeHtml(item.url)}" class="order-detail-name">${escapeHtml(item.name)}</a>
                    <span>${item.quantity} × ${formatPrice(item.price)}</span>
                </div>
                <strong>${formatPrice(item.line_total)}</strong>
            </li>`).join('')}
        </ul>
        ${breakdown}
        <div class="order-detail-total">
            <span>${escapeHtml(t('Order total'))}</span>
            <strong>${formatPrice(order.total)}</strong>
        </div>`;
}

document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('click', function(e) {
        const button = e.target.closest('[data-order-details]');
        if (button) window.viewOrderDetails(button.dataset.orderDetails);
    });

    // Status chips on the customer's orders page
    const chips = document.querySelectorAll('[data-status-filter]');
    const cards = document.querySelectorAll('.order-card');
    const emptyMessage = document.getElementById('ordersFilterEmpty');

    chips.forEach(chip => {
        chip.addEventListener('click', function() {
            const status = chip.dataset.statusFilter;
            chips.forEach(c => c.classList.toggle('active', c === chip));

            let visible = 0;
            cards.forEach(card => {
                const show = status === 'all' || card.dataset.status === status;
                card.hidden = !show;
                if (show) visible++;
            });
            if (emptyMessage) emptyMessage.hidden = visible > 0;
        });
    });
});

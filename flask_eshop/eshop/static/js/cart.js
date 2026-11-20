// Cart Page JavaScript: change quantities (minus at 1 removes the item) without reloading the page.
// The forms still work on their own; this sends them with AJAX and updates the totals.
document.addEventListener('DOMContentLoaded', function() {
    const page = document.getElementById('cartPage');
    if (!page) return;

    page.addEventListener('submit', async function(e) {
        const form = e.target;
        const row = form.closest('.cart-item');
        if (!row) return;
        e.preventDefault();

        const productId = row.dataset.productId;
        row.classList.add('is-updating');
        try {
            const current = parseInt(row.querySelector('[data-qty]').textContent, 10);
            const data = await updateCartItem(productId, current + parseInt(form.dataset.step, 10));

            if (!data.success) showToast(data.message, 'warning');
            applyCart(data.cart);
            // The row is gone, so reload the page to bring it back on undo
            if (data.success && !data.cart.items.some(item => String(item.id) === productId)) {
                showRemovedToast(productId, () => window.location.reload());
            }
        } catch (error) {
            console.error('Error updating cart:', error);
            showToast(t('Could not update your cart. Please try again.'), 'error');
        } finally {
            row.classList.remove('is-updating');
        }
    });

    // Update every row and the summary from the cart the server sent back
    function applyCart(cart) {
        updateCartCount(cart.count);
        renderCartSummary(page, cart);

        const items = new Map(cart.items.map(item => [String(item.id), item]));
        page.querySelectorAll('.cart-item').forEach(row => {
            const item = items.get(row.dataset.productId);
            if (!item) {
                removeRow(row);
                return;
            }

            row.querySelector('[data-qty]').textContent = item.quantity;
            const lineTotal = row.querySelector('[data-line-total]');
            if (lineTotal.textContent !== formatPrice(item.line_total)) {
                lineTotal.textContent = formatPrice(item.line_total);
                replayAnimation(lineTotal, 'changed');
            }

            const minus = row.querySelector('[data-step="-1"]');
            const plus = row.querySelector('[data-step="1"]');
            const minusButton = minus.querySelector('button');
            minusButton.setAttribute('aria-label', item.quantity <= 1 ? minusButton.dataset.removeLabel : t('Decrease quantity'));
            plus.querySelector('button').disabled = item.quantity >= item.stock;
            // Keep the no-JS fallback values right too
            minus.querySelector('[name="quantity"]').value = item.quantity - 1;
            plus.querySelector('[name="quantity"]').value = item.quantity + 1;

            row.querySelector('[data-stock-note]').textContent =
                item.quantity >= item.stock ? t('Maximum available quantity')
                : item.stock < 10 ? t('Only {n} left in stock', { n: item.stock }) : '';
        });

        if (!cart.items.length) showEmptyState();
    }

    // Slide the row out and collapse its height
    function removeRow(row) {
        row.style.maxHeight = `${row.offsetHeight}px`;
        void row.offsetHeight;
        row.classList.add('is-removing');
        row.style.maxHeight = '0px';
        setTimeout(() => row.remove(), 450);
    }

    function showEmptyState() {
        setTimeout(() => {
            document.getElementById('cartLayout')?.remove();
            document.getElementById('cartEmpty').hidden = false;
        }, 450);
    }

    // There are no promo codes yet, so every code is rejected
    const promoForm = document.getElementById('promoForm');
    promoForm?.addEventListener('submit', function(e) {
        e.preventDefault();
        const input = promoForm.querySelector('input');
        const code = input.value.trim();
        input.classList.remove('is-invalid');

        if (!code) {
            input.focus();
            showToast(t('Enter a promo code first'), 'info');
            return;
        }
        replayAnimation(input, 'is-invalid');
        showToast(t('"{code}" isn\'t a valid promo code', { code: code.toUpperCase() }), 'warning');
    });
});

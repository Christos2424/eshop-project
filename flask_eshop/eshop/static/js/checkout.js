// Checkout Page JavaScript: check the shipping form before the order is placed
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('checkoutForm');
    if (!form) return;

    initSummaryQuantities();

    // We show our own messages instead of the browser's
    form.noValidate = true;

    const required = message => value => (value ? '' : message);
    const rules = {
        firstName: required(t('Please enter your first name')),
        lastName: required(t('Please enter your last name')),
        email: value => !value ? t('Please enter your email')
            : /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value) ? '' : t('Please enter a valid email address'),
        address: value => value.length >= 5 ? '' : t('Please enter your street address'),
        city: required(t('Please enter your city')),
        zipCode: value => /^[A-Za-z0-9][A-Za-z0-9 -]{1,9}$/.test(value) ? '' : t('Please enter a valid ZIP / postal code'),
        country: required(t('Please choose a country'))
    };

    function validate(field) {
        const message = rules[field.name](field.value.trim());
        setFieldError(field, message);
        field.closest('.form-group').classList.toggle('is-valid', !message);
        return !message;
    }

    Object.keys(rules).forEach(name => {
        const field = form.elements[name];
        field.addEventListener('blur', () => {
            if (field.value.trim()) validate(field);
        });
        // Once a field shows an error, re-check it as the user fixes it
        field.addEventListener('input', () => {
            if (field.closest('.form-group').classList.contains('has-error')) validate(field);
        });
        field.addEventListener('change', () => validate(field));
    });

    form.addEventListener('submit', function(e) {
        const invalid = Object.keys(rules).map(name => form.elements[name]).filter(field => !validate(field));
        if (invalid.length) {
            e.preventDefault();
            invalid[0].focus();
            showToast(t('Please check the highlighted fields'), 'warning');
            return;
        }

        // Prevent double orders while the server works
        const button = form.querySelector('.btn-checkout');
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${escapeHtml(t('Placing your order…'))}`;
    });
});

// Add/remove items from the order summary without leaving checkout
function initSummaryQuantities() {
    const summary = document.querySelector('.checkout-summary');
    if (!summary) return;

    summary.addEventListener('submit', async function(e) {
        const stepForm = e.target.closest('.cart-qty-form');
        const row = stepForm && stepForm.closest('.summary-item');
        if (!row) return;
        e.preventDefault();

        const productId = row.dataset.productId;
        row.classList.add('is-updating');
        try {
            const current = parseInt(row.querySelector('[data-qty]').textContent, 10);
            const data = await updateCartItem(productId, current + parseInt(stepForm.dataset.step, 10));

            if (!data.success) showToast(data.message, 'warning');
            applyCart(data.cart);

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

    function applyCart(cart) {
        const totalField = summary.querySelector('[data-cart-field="total"]');
        const oldTotal = totalField.textContent.trim();

        updateCartCount(cart.count);
        renderCartSummary(summary, cart);

        // Keep the "Place order" button's total in step
        const label = document.querySelector('[data-place-order-label]');
        const newTotal = totalField.textContent.trim();
        if (label && oldTotal !== newTotal) label.textContent = label.textContent.replace(oldTotal, newTotal);

        const items = new Map(cart.items.map(item => [String(item.id), item]));
        summary.querySelectorAll('.summary-item').forEach(row => {
            const item = items.get(row.dataset.productId);
            if (!item) {
                row.classList.add('is-removing');
                setTimeout(() => row.remove(), 300);
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
            minus.querySelector('[name="quantity"]').value = item.quantity - 1;
            plus.querySelector('[name="quantity"]').value = item.quantity + 1;
        });

        // Nothing left to buy: go back to the (empty) cart
        if (!cart.items.length) {
            setTimeout(() => { window.location.href = window.APP_URLS.view_cart; }, 1200);
        }
    }
}

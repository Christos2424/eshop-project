// Checkout Page JavaScript: check the shipping form before the order is placed
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('checkoutForm');
    if (!form) return;

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

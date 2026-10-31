// Login and Register pages: show/hide password, password strength and live checks
document.addEventListener('DOMContentLoaded', function() {
    initPasswordToggles();

    document.querySelectorAll('[data-auth-form]').forEach(form => {
        if (form.hasAttribute('data-validate')) initRegisterValidation(form);

        form.addEventListener('submit', function(e) {
            if (e.defaultPrevented) return;
            const button = form.querySelector('button[type="submit"]');
            button.classList.add('is-loading');
            button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${escapeHtml(t('Please wait…'))}`;
        });
    });
});

function initPasswordToggles() {
    document.querySelectorAll('[data-password-toggle]').forEach(button => {
        const input = document.getElementById(button.dataset.passwordToggle);
        button.addEventListener('click', function() {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.setAttribute('aria-pressed', show);
            button.setAttribute('aria-label', show ? t('Hide password') : t('Show password'));
            button.querySelector('i').className = `fas ${show ? 'fa-eye-slash' : 'fa-eye'}`;
            input.focus();
        });
    });
}

// 1 (weak) to 4 (strong); passwords under 6 characters are rejected by the server
function passwordStrength(password) {
    if (password.length < 6) return { level: 1, label: t('Too short') };
    let level = 1;
    if (password.length >= 10) level++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) level++;
    if (/\d/.test(password) || /[^A-Za-z0-9]/.test(password)) level++;
    return { level, label: [t('Weak'), t('Fair'), t('Good'), t('Strong')][level - 1] };
}

// Same rules as validators.validate_user_data on the server
function initRegisterValidation(form) {
    form.noValidate = true;
    const fields = form.elements;
    const meter = form.querySelector('[data-strength-meter]');
    const usernameHint = fields.username.closest('.form-group').querySelector('.field-hint');

    const rules = {
        username: value => value.length < 3 ? t('Username must be at least 3 characters')
            : /^[\p{L}\p{N}]+$/u.test(value) ? '' : t('Username can only contain letters and numbers'),
        email: value => /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value) ? '' : t('Please enter a valid email address'),
        password: value => value.length >= 6 ? '' : t('Password must be at least 6 characters'),
        confirm_password: value => !value ? t('Please confirm your password')
            : value === fields.password.value ? '' : t('Passwords do not match')
    };

    function validate(field) {
        const value = field.name === 'username' || field.name === 'email' ? field.value.trim() : field.value;
        const message = rules[field.name](value);
        setFieldError(field, message);
        field.closest('.form-group').classList.toggle('is-valid', !message);
        if (field.name === 'username') {
            usernameHint.hidden = Boolean(message);
            usernameHint.classList.toggle('is-ok', !message);
        }
        return !message;
    }

    Object.keys(rules).forEach(name => {
        const field = fields[name];
        field.addEventListener('blur', () => {
            if (field.value) validate(field);
        });
        field.addEventListener('input', () => {
            const group = field.closest('.form-group');
            if (group.classList.contains('has-error') || group.classList.contains('is-valid')) validate(field);
        });
    });

    fields.password.addEventListener('input', function() {
        const password = fields.password.value;
        meter.hidden = !password;
        const { level, label } = passwordStrength(password);
        meter.dataset.level = level;
        meter.querySelector('[data-strength-label]').textContent = label;
        // The confirmation may now match (or stop matching)
        if (fields.confirm_password.value) validate(fields.confirm_password);
    });

    form.addEventListener('submit', function(e) {
        const invalid = Object.keys(rules).map(name => fields[name]).filter(field => !validate(field));
        if (invalid.length) {
            e.preventDefault();
            invalid[0].focus();
        }
    });
}

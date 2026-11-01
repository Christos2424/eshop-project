// Add / Edit Product forms: image preview, file size check, unsaved changes warning
// and a locked save button while the form (and its image) uploads
const MAX_IMAGE_BYTES = 16 * 1024 * 1024;

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.product-form');
    if (!form) return;

    initImagePreview(form);
    initUnsavedWarning(form);
});

function initImagePreview(form) {
    const fileInput = form.querySelector('#image_file');
    const urlInput = form.querySelector('#image_url');
    const removeBox = form.querySelector('[name="remove_image"]');
    const currentImage = form.querySelector('.current-image');
    if (!fileInput || !urlInput) return;

    const preview = document.createElement('div');
    preview.className = 'image-live-preview';
    preview.hidden = true;
    preview.innerHTML = `
        <img alt="">
        <span class="image-live-label"></span>`;
    form.querySelector('.image-upload-options').after(preview);
    const img = preview.querySelector('img');
    const label = preview.querySelector('.image-live-label');
    let objectUrl = null;

    function show(src, text) {
        if (objectUrl && src !== objectUrl) {
            URL.revokeObjectURL(objectUrl);
            objectUrl = null;
        }
        if (!src) {
            preview.hidden = true;
            img.removeAttribute('src');
            return;
        }
        img.src = src;
        label.textContent = text;
        preview.hidden = false;
        replayAnimation(preview, 'fade-in');
    }

    // An uploaded file wins over a URL (the server does the same)
    function refresh() {
        const file = fileInput.files[0];
        if (file) {
            objectUrl = URL.createObjectURL(file);
            show(objectUrl, t('New image: {name}', { name: file.name }));
        } else if (urlInput.value.trim() && urlInput.value.trim() !== urlInput.defaultValue.trim() && urlInput.checkValidity()) {
            show(urlInput.value.trim(), t('New image from URL'));
        } else {
            show(null);
        }
    }

    fileInput.addEventListener('change', function() {
        const file = fileInput.files[0];
        setFieldError(fileInput, '');
        if (file && file.size > MAX_IMAGE_BYTES) {
            setFieldError(fileInput, t('This image is larger than 16MB'));
            fileInput.value = '';
        } else if (file && !file.type.startsWith('image/')) {
            setFieldError(fileInput, t('Please choose an image file'));
            fileInput.value = '';
        }
        refresh();
    });

    urlInput.addEventListener('change', function() {
        setFieldError(urlInput, '');
        refresh();
    });

    // Tell the admin straight away when a URL doesn't point to an image
    img.addEventListener('error', function() {
        if (!img.getAttribute('src') || fileInput.files[0]) return;
        show(null);
        setFieldError(urlInput, t('No image could be loaded from this URL'));
    });

    removeBox?.addEventListener('change', function() {
        currentImage?.classList.toggle('is-removed', removeBox.checked);
    });
}

function initUnsavedWarning(form) {
    const snapshot = () => JSON.stringify(Array.from(new FormData(form).entries(),
        ([key, value]) => [key, value instanceof File ? value.name : value]));
    const initial = snapshot();
    let submitting = false;

    window.addEventListener('beforeunload', function(e) {
        if (!submitting && snapshot() !== initial) {
            e.preventDefault();
            e.returnValue = '';
        }
    });

    form.addEventListener('submit', function(e) {
        if (submitting) {
            e.preventDefault();
            return;
        }
        submitting = true;
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${escapeHtml(t('Saving…'))}`;
    });
}

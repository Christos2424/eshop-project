// Cart Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Function to update cart count when removing items
    window.updateCartCountOnRemove = function(quantityToRemove) {
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            const currentCount = parseInt(cartCountElement.textContent) || 0;
            const newCount = Math.max(0, currentCount - quantityToRemove);
            
            // Update the count immediately for better UX
            cartCountElement.textContent = newCount;
            
            if (newCount > 0) {
                cartCountElement.style.display = 'flex';
            } else {
                cartCountElement.style.display = 'none';
            }
        }
    };

    // Update quantity buttons to update cart count
    const quantityForms = document.querySelectorAll('.quantity-controls form');
    
    quantityForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // The form will handle the actual update, we just update the UI immediately
            setTimeout(() => {
                // Reload the page to get updated cart data
                // In a real app, you'd use AJAX, but for simplicity we'll reload
                window.location.reload();
            }, 100);
        });
    });
});
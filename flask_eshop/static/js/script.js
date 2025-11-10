// Modern interactive features
document.addEventListener('DOMContentLoaded', function() {
    // Add to cart animations
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const button = this.querySelector('button[type="submit"]');
            const originalText = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
            button.disabled = true;
            
            // Get the product ID and quantity to update cart count
            const productId = this.querySelector('input[name="product_id"]').value;
            const quantity = parseInt(this.querySelector('input[name="quantity"]').value) || 1;
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
                
                // Update cart count dynamically
                updateCartCount(quantity);
            }, 1000);
        });
    });
    
    // Function to update cart count dynamically
    function updateCartCount(quantityToAdd = 0) {
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            const currentCount = parseInt(cartCountElement.textContent) || 0;
            const newCount = currentCount + quantityToAdd;
            cartCountElement.textContent = newCount;
            
            // Show/hide cart count based on new count
            if (newCount > 0) {
                cartCountElement.style.display = 'flex';
            } else {
                cartCountElement.style.display = 'none';
            }
        } else if (quantityToAdd > 0) {
            // If cart count doesn't exist but we're adding items, create it
            const cartLink = document.querySelector('.cart-link');
            if (cartLink) {
                const newCartCount = document.createElement('span');
                newCartCount.className = 'cart-count';
                newCartCount.textContent = quantityToAdd;
                newCartCount.style.display = 'flex';
                cartLink.appendChild(newCartCount);
            }
        }
    }
    
    // Update cart count on page load
    updateCartCountOnLoad();
    
    function updateCartCountOnLoad() {
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            const currentCount = parseInt(cartCountElement.textContent) || 0;
            if (currentCount > 0) {
                cartCountElement.style.display = 'flex';
            } else {
                cartCountElement.style.display = 'none';
            }
        }
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Quantity controls for product detail page
    const quantityInputs = document.querySelectorAll('input[name="quantity"]');
    quantityInputs.forEach(input => {
        // Only apply to product detail page, not admin forms
        if (!input.closest('.product-form')) {
            input.addEventListener('change', function() {
                if (this.value < 1) this.value = 1;
                if (this.max && this.value > parseInt(this.max)) this.value = this.max;
            });
        }
    });
});
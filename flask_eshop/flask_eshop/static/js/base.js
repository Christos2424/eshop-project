// Modern interactive features - General functionality
document.addEventListener('DOMContentLoaded', function() {
    // Populate categories in the dropdown on all pages
    function populateCategories() {
        const categoriesList = document.getElementById('categories-list');
        
        if (categoriesList) {
            // Get categories from global variable or data attribute
            let categories = [];
            const categoriesData = document.getElementById('categories-data');
            
            if (categoriesData) {
                try {
                    categories = JSON.parse(categoriesData.textContent || '[]');
                } catch (e) {
                    console.error('Error parsing categories data:', e);
                }
            } else if (window.globalCategories) {
                categories = window.globalCategories;
            }
            
            // Clear existing categories (keep the first item if it's a header)
            const existingItems = categoriesList.querySelectorAll('.category-item');
            existingItems.forEach((item, index) => {
                if (index > 0) { // Keep first item (usually "All Categories" or header)
                    item.remove();
                }
            });
            
            // Add categories to dropdown
            categories.forEach(function(category) {
                const link = document.createElement('a');
                link.href = `/?category=${encodeURIComponent(category)}`;
                link.className = 'category-item';
                link.textContent = category;
                categoriesList.appendChild(link);
            });
        }
    }

    // Initialize categories
    populateCategories();

    // Add to cart with AJAX
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');
    
    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            
            const button = this.querySelector('button[type="submit"]');
            const originalText = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
            button.disabled = true;
            
            // Get form data
            const formData = new FormData(this);
            
            // Send AJAX request
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Identify as AJAX request
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update cart count
                    updateCartCount(data.cart_count);
                    
                    // Show success message
                    showFlashMessage(data.message, 'success');
                    
                    // Optional: Add visual feedback on the button
                    button.innerHTML = '<i class="fas fa-check"></i> Added!';
                    setTimeout(() => {
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }, 1500);
                } else {
                    // Show error message
                    showFlashMessage(data.message, 'danger');
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showFlashMessage('An error occurred. Please try again.', 'danger');
                button.innerHTML = originalText;
                button.disabled = false;
            });
        });
    });
    
    // Function to show flash messages dynamically
    function showFlashMessage(message, category) {
        // Remove any existing dynamic flash messages
        document.querySelectorAll('.flash-dynamic').forEach(flash => flash.remove());
        
        // Create new flash message
        const flashMessage = document.createElement('div');
        flashMessage.className = `flash flash-${category} flash-dynamic`;
        flashMessage.innerHTML = `
            <i class="fas fa-${getFlashIcon(category)}"></i>
            ${message}
        `;
        
        // Add styles for dynamic flash messages
        flashMessage.style.position = 'fixed';
        flashMessage.style.top = '100px';
        flashMessage.style.right = '20px';
        flashMessage.style.zIndex = '9999';
        flashMessage.style.maxWidth = '300px';
        flashMessage.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        
        // Add to page
        document.body.appendChild(flashMessage);
        
        // Remove after 3 seconds
        setTimeout(() => {
            flashMessage.style.opacity = '0';
            flashMessage.style.transition = 'opacity 0.3s ease';
            setTimeout(() => flashMessage.remove(), 300);
        }, 3000);
    }
    
    function getFlashIcon(category) {
        switch(category) {
            case 'success': return 'check-circle';
            case 'danger': return 'exclamation-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }
    
    // Function to update cart count dynamically
    function updateCartCount(newCount) {
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            cartCountElement.textContent = newCount;
            
            if (newCount > 0) {
                cartCountElement.style.display = 'flex';
                
                // Add animation
                cartCountElement.style.transform = 'scale(1.2)';
                setTimeout(() => {
                    cartCountElement.style.transform = 'scale(1)';
                    cartCountElement.style.transition = 'transform 0.3s ease';
                }, 300);
            } else {
                cartCountElement.style.display = 'none';
            }
        } else if (newCount > 0) {
            // If cart count doesn't exist but we're adding items, create it
            const cartLink = document.querySelector('.cart-link');
            if (cartLink) {
                const newCartCount = document.createElement('span');
                newCartCount.className = 'cart-count';
                newCartCount.textContent = newCount;
                newCartCount.style.display = 'flex';
                cartLink.appendChild(newCartCount);
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

    // User dropdown functionality
    const userDropdowns = document.querySelectorAll('.user-dropdown');
    
    userDropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', function(e) {
            // Prevent closing when clicking inside dropdown
            e.stopPropagation();
        });
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        userDropdowns.forEach(dropdown => {
            const menu = dropdown.querySelector('.user-dropdown-menu');
            if (menu) {
                menu.style.opacity = '0';
                menu.style.visibility = 'hidden';
                menu.style.transform = 'translateY(-10px)';
            }
        });
    });
    
    // Mobile menu toggle for categories (if needed)
    const categoriesDropdown = document.querySelector('.categories-dropdown');
    if (categoriesDropdown) {
        categoriesDropdown.addEventListener('click', function(e) {
            if (window.innerWidth <= 480) {
                e.preventDefault();
                const menu = this.querySelector('.categories-menu');
                if (menu) {
                    const isVisible = menu.style.opacity === '1';
                    menu.style.opacity = isVisible ? '0' : '1';
                    menu.style.visibility = isVisible ? 'hidden' : 'visible';
                    menu.style.transform = isVisible ? 'translateY(-10px)' : 'translateY(0)';
                }
            }
        });
    }

    // Make product rows clickable (for admin products page)
    const clickableRows = document.querySelectorAll('.clickable-row');
    
    clickableRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on action buttons
            if (e.target.closest('.action-buttons')) {
                return;
            }
            window.location.href = this.dataset.href;
        });
    });
});
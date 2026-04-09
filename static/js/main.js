// ========== CART MANAGER - WORKING CODE ==========

// Create cartManager object
const cartManager = {
    // Initialize cart
    init: function() {
        console.log('✅ Cart Manager Initialized');
        this.attachEvents();
    },

    // Attach events
    attachEvents: function() {
        console.log('Events attached');
    },

    // Update quantity
    updateQuantity: function(productId, change) {
        console.log('Updating quantity for product:', productId, 'Change:', change);
        
        const currentQtySpan = document.getElementById(`qty-${productId}`);
        if (!currentQtySpan) {
            console.error('Quantity span not found');
            return;
        }
        
        let currentQty = parseInt(currentQtySpan.innerText);
        let newQty = currentQty + change;
        
        if (newQty < 1) {
            this.showToast('Quantity cannot be less than 1', 'warning');
            return;
        }
        
        // Disable buttons during update
        const buttons = document.querySelectorAll(`#cart-row-${productId} .quantity-btn`);
        buttons.forEach(btn => btn.disabled = true);
        
        // Update hidden input
        const hiddenInput = document.getElementById(`update-qty-${productId}`);
        if (hiddenInput) {
            hiddenInput.value = newQty;
        }
        
        // Get form
        const form = document.getElementById(`update-form-${productId}`);
        if (!form) {
            console.error('Update form not found');
            buttons.forEach(btn => btn.disabled = false);
            return;
        }
        
        // Send AJAX request
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Response:', data);
            if (data.success) {
                // Update quantity display
                currentQtySpan.innerText = newQty;
                
                // Update subtotal
                const subtotalElement = document.getElementById(`subtotal-${productId}`);
                if (subtotalElement) {
                    subtotalElement.innerText = `₹${data.new_subtotal}`;
                    subtotalElement.classList.add('update-animation');
                }
                
                // Update cart total
                const totalElement = document.getElementById('cart-total');
                if (totalElement) {
                    totalElement.innerText = `₹${data.new_total}`;
                    totalElement.classList.add('update-animation');
                }
                
                // Enable/disable minus button
                const minusBtn = document.querySelector(`#cart-row-${productId} .minus`);
                if (minusBtn) {
                    minusBtn.disabled = newQty <= 1;
                }
                
                // Update item count
                this.updateItemCount();
                
                // Remove animation classes
                setTimeout(() => {
                    if (subtotalElement) subtotalElement.classList.remove('update-animation');
                    if (totalElement) totalElement.classList.remove('update-animation');
                }, 500);
                
                this.showToast('Cart updated successfully!', 'success');
            } else {
                this.showToast(data.message || 'Error updating cart', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showToast('Error updating cart', 'error');
        })
        .finally(() => {
            // Re-enable buttons
            buttons.forEach(btn => btn.disabled = false);
        });
    },

    // Remove item
    removeItem: function(productId) {
        console.log('Removing product:', productId);
        
        if (!confirm('Are you sure you want to remove this item?')) {
            return;
        }
        
        const row = document.getElementById(`cart-row-${productId}`);
        if (!row) {
            console.error('Cart row not found');
            return;
        }
        
        const form = document.getElementById(`remove-form-${productId}`);
        if (!form) {
            console.error('Remove form not found');
            return;
        }
        
        // Add removing animation
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0.5';
        row.style.transform = 'scale(0.98)';
        
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Response:', data);
            if (data.success) {
                // Animate removal
                row.style.transform = 'translateX(100%)';
                row.style.opacity = '0';
                
                setTimeout(() => {
                    row.remove();
                    
                    // Update total
                    const totalElement = document.getElementById('cart-total');
                    if (totalElement) {
                        totalElement.innerText = `₹${data.new_total}`;
                        totalElement.classList.add('update-animation');
                    }
                    
                    // Update item count
                    this.updateItemCount();
                    
                    // Remove animation
                    setTimeout(() => {
                        if (totalElement) totalElement.classList.remove('update-animation');
                    }, 500);
                    
                    // Check if cart is empty
                    const remainingItems = document.querySelectorAll('.cart-item').length;
                    if (remainingItems === 0) {
                        setTimeout(() => {
                            location.reload();
                        }, 500);
                    }
                    
                    this.showToast('Item removed from cart', 'success');
                }, 300);
            } else {
                row.style.opacity = '1';
                row.style.transform = 'scale(1)';
                this.showToast(data.message || 'Error removing item', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            row.style.opacity = '1';
            row.style.transform = 'scale(1)';
            this.showToast('Error removing item', 'error');
        });
    },

    // Update item count
    updateItemCount: function() {
        const itemCount = document.querySelectorAll('.cart-item').length;
        const countElement = document.getElementById('item-count');
        if (countElement) {
            countElement.innerText = itemCount + ' Items';
            
            // Animate count change
            countElement.style.transform = 'scale(1.2)';
            setTimeout(() => {
                countElement.style.transform = 'scale(1)';
            }, 200);
        }
    },

    // Show toast notification
    showToast: function(message, type = 'info') {
        console.log('Toast:', message, type);
        
        const container = document.getElementById('toast-container');
        if (!container) {
            alert(message); // Fallback to alert if toast container not found
            return;
        }
        
        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Set icon
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';
        if (type === 'warning') icon = 'fa-exclamation-triangle';
        
        toast.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    },

    // Get CSRF token
    getCookie: function(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing cart...');
    cartManager.init();
});

// Add toast styles if not already in CSS
(function addToastStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
        
        .toast {
            background: white;
            color: #333;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideInRight 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 300px;
            border-left: 4px solid;
        }
        
        .toast.success {
            border-left-color: #28a745;
        }
        
        .toast.success i {
            color: #28a745;
        }
        
        .toast.error {
            border-left-color: #dc3545;
        }
        
        .toast.error i {
            color: #dc3545;
        }
        
        .toast.warning {
            border-left-color: #ffc107;
        }
        
        .toast.warning i {
            color: #ffc107;
        }
        
        .toast.info {
            border-left-color: #17a2b8;
        }
        
        .toast.info i {
            color: #17a2b8;
        }
        
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .update-animation {
            animation: priceUpdate 0.5s ease;
        }
        
        @keyframes priceUpdate {
            0% { transform: scale(1); }
            50% { transform: scale(1.2); color: #28a745; }
            100% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
})();

console.log('✅ Cart Manager loaded successfully');
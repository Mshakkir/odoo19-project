document.addEventListener('DOMContentLoaded', function() {

    // Add to cart with stock validation
    const addToCartButtons = document.querySelectorAll('[data-action="cart_update"]');

    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const product = this.closest('[data-product-id]');
            const productId = product.dataset.productId;
            const qty = parseInt(document.querySelector('[name="add_qty"]').value) || 1;
            const availableQty = parseInt(product.querySelector('[data-available-qty]').textContent);

            if (qty > availableQty && availableQty > 0) {
                e.preventDefault();
                alert(`Only ${availableQty} units available!`);
            }
        });
    });

    // Stock status animations
    const stockBadges = document.querySelectorAll('.stock-badge');
    stockBadges.forEach(badge => {
        if (badge.classList.contains('stock-low')) {
            badge.style.animation = 'pulse 2s infinite';
        }
    });
});

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
`;
document.head.appendChild(style);
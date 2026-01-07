/** @odoo-module **/

let autoScrollInterval;
let categoryButtons = [];
let currentIndex = 0;

window.showCategory = function(id, button) {
    // Stop auto-scroll when user clicks
    stopAutoScroll();

    // Update panels
    document.querySelectorAll('.cat-panel').forEach(function(p) {
        p.classList.remove('active');
    });
    const panel = document.getElementById(id);
    if (panel) {
        panel.classList.add('active');
    }

    // Update buttons
    document.querySelectorAll('.cat-btn').forEach(function(b) {
        b.classList.remove('active');
    });
    button.classList.add('active');

    // Update current index
    currentIndex = categoryButtons.indexOf(button);

    // Center the clicked button
    const container = document.querySelector('.category-tabs');
    if (container) {
        const buttonRect = button.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const scrollLeft = button.offsetLeft - (containerRect.width / 2) + (buttonRect.width / 2);
        container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
    }

    // Restart auto-scroll after 5 seconds
    setTimeout(startAutoScroll, 5000);
};

window.scrollCategories = function(direction) {
    const container = document.querySelector('.category-tabs');
    if (container) {
        const scrollAmount = 200;
        container.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' });
    }

    // Stop and restart auto-scroll
    stopAutoScroll();
    setTimeout(startAutoScroll, 5000);
};

function autoAdvanceCategory() {
    if (categoryButtons.length === 0) {
        return;
    }

    currentIndex = (currentIndex + 1) % categoryButtons.length;
    const nextButton = categoryButtons[currentIndex];

    if (nextButton) {
        // Update panels
        document.querySelectorAll('.cat-panel').forEach(function(p) {
            p.classList.remove('active');
        });
        const panelId = nextButton.getAttribute('onclick').match(/'([^']+)'/)[1];
        const panel = document.getElementById(panelId);
        if (panel) {
            panel.classList.add('active');
        }

        // Update buttons
        document.querySelectorAll('.cat-btn').forEach(function(b) {
            b.classList.remove('active');
        });
        nextButton.classList.add('active');

        // Scroll to center the button
        const container = document.querySelector('.category-tabs');
        if (container) {
            const buttonRect = nextButton.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const scrollLeft = nextButton.offsetLeft - (containerRect.width / 2) + (buttonRect.width / 2);
            container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
        }
    }
}

function startAutoScroll() {
    stopAutoScroll();
    autoScrollInterval = setInterval(autoAdvanceCategory, 4000);
}

function stopAutoScroll() {
    if (autoScrollInterval) {
        clearInterval(autoScrollInterval);
        autoScrollInterval = null;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    categoryButtons = Array.from(document.querySelectorAll('.cat-btn'));

    // Start auto-scroll after page loads
    setTimeout(startAutoScroll, 2000);

    // Pause auto-scroll when user hovers over the section
    const sliderWrapper = document.querySelector('.category-slider-wrapper');
    if (sliderWrapper) {
        sliderWrapper.addEventListener('mouseenter', stopAutoScroll);
        sliderWrapper.addEventListener('mouseleave', function() {
            setTimeout(startAutoScroll, 2000);
        });
    }
});
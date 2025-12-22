/* Custom Header JavaScript */

(function() {
    'use strict';

    // Wait for DOM to be fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        hideSignInButton();
        addStickyHeaderEffect();
    });

    /**
     * Hide Sign In button using multiple methods
     */
    function hideSignInButton() {
        // Method 1: Hide by href containing login
        const signInSelectors = [
            'a[href*="/web/login"]',
            'a[href*="/web/signin"]',
            'a[href*="sign-in"]',
            'a[href="/web/login"]',
            '.o_portal_sign_in',
            '.o_sign_in_link',
            '.o_login_btn'
        ];

        signInSelectors.forEach(function(selector) {
            const elements = document.querySelectorAll(selector);
            elements.forEach(function(element) {
                element.style.display = 'none';
                element.style.visibility = 'hidden';
                element.style.opacity = '0';
                // Also hide parent li if exists
                const parentLi = element.closest('li');
                if (parentLi) {
                    parentLi.style.display = 'none';
                }
            });
        });

        // Method 2: Hide by text content
        const headerLinks = document.querySelectorAll('header a, .navbar a, .o_main_navbar a');
        headerLinks.forEach(function(link) {
            const text = link.textContent.trim().toLowerCase();
            if (text === 'sign in' || text === 'login' || text === 'log in') {
                link.style.display = 'none';
                const parentLi = link.closest('li');
                if (parentLi) {
                    parentLi.style.display = 'none';
                }
            }
        });

        console.log('Sign-in buttons hidden successfully');
    }

    /**
     * Add sticky header effect on scroll
     */
    function addStickyHeaderEffect() {
        const header = document.querySelector('header, .o_main_navbar');

        if (!header) return;

        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop;

            if (currentScroll > 100) {
                header.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
            } else {
                header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
            }
        });

        console.log('Sticky header effect activated');
    }

    // Run hide function again after a delay to catch dynamically loaded content
    setTimeout(hideSignInButton, 1000);
    setTimeout(hideSignInButton, 2000);

})();
/** @odoo-module **/

import { Component } from "@odoo/owl";

/* Custom Header JavaScript */

(function() {
    'use strict';

    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCustomTheme);
    } else {
        initCustomTheme();
    }

    function initCustomTheme() {
        console.log('Custom Theme Module: Initializing...');

        hideSignInButton();
        addStickyHeaderEffect();

        // Run hide function again after delays to catch dynamic content
        setTimeout(hideSignInButton, 1000);
        setTimeout(hideSignInButton, 2000);
        setTimeout(hideSignInButton, 3000);

        console.log('Custom Theme Module: Loaded successfully');
    }

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
                element.style.position = 'absolute';
                element.style.left = '-9999px';

                // Also hide parent li if exists
                const parentLi = element.closest('li');
                if (parentLi) {
                    parentLi.style.display = 'none';
                }

                // Also hide parent nav-item
                const parentNavItem = element.closest('.nav-item');
                if (parentNavItem) {
                    parentNavItem.style.display = 'none';
                }
            });
        });

        // Method 2: Hide by text content
        const headerLinks = document.querySelectorAll('header a, .navbar a, .o_main_navbar a, nav a');
        headerLinks.forEach(function(link) {
            const text = link.textContent.trim().toLowerCase();
            if (text === 'sign in' || text === 'login' || text === 'log in' || text === 'signin') {
                link.style.display = 'none';
                link.style.visibility = 'hidden';

                const parentLi = link.closest('li');
                if (parentLi) {
                    parentLi.style.display = 'none';
                }

                const parentNavItem = link.closest('.nav-item');
                if (parentNavItem) {
                    parentNavItem.style.display = 'none';
                }
            }
        });

        console.log('Custom Theme: Sign-in buttons hidden');
    }

    /**
     * Add sticky header effect on scroll
     */
    function addStickyHeaderEffect() {
        const header = document.querySelector('header, .o_main_navbar');

        if (!header) {
            console.log('Custom Theme: Header element not found');
            return;
        }

        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset || document.documentElement.scrollTop;

            if (currentScroll > 100) {
                header.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
            } else {
                header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
            }
        });

        console.log('Custom Theme: Sticky header effect activated');
    }

    // MutationObserver to watch for dynamically added content
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                hideSignInButton();
            }
        });
    });

    // Start observing the header for changes
    const headerElement = document.querySelector('header, .o_main_navbar');
    if (headerElement) {
        observer.observe(headerElement, {
            childList: true,
            subtree: true
        });
    }

})();
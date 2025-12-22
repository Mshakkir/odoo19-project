
```javascript
/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.CustomHeaderWidget = publicWidget.Widget.extend({
    selector: 'header, .o_main_navbar',

    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this._hideSignInButton();
        this._addStickyHeader();
        console.log('Custom Header Widget Loaded');
    },

    /**
     * Hide Sign In button with multiple methods
     */
    _hideSignInButton: function () {
        // Method 1: Hide by href attribute
        const signInLinks = document.querySelectorAll(
            'a[href*="/web/login"], a[href*="sign-in"], a[href*="signin"]'
        );
        signInLinks.forEach(link => {
            link.style.display = 'none';
            link.style.visibility = 'hidden';
        });

        // Method 2: Hide by text content
        const allLinks = document.querySelectorAll('header a, .o_main_navbar a');
        allLinks.forEach(link => {
            if (link.textContent.trim().toLowerCase().includes('sign in') ||
                link.textContent.trim().toLowerCase().includes('login')) {
                link.style.display = 'none';
                link.style.visibility = 'hidden';
            }
        });

        // Method 3: Hide Odoo specific classes
        const odooSignIn = document.querySelectorAll('.o_portal_sign_in, .o_sign_in_link');
        odooSignIn.forEach(element => {
            element.style.display = 'none';
        });
    },

    /**
     * Add sticky header effect on scroll
     */
    _addStickyHeader: function () {
        let lastScroll = 0;

        window.addEventListener('scroll', () => {
            const header = document.querySelector('header, .o_main_navbar');
            const currentScroll = window.pageYOffset;

            if (header) {
                if (currentScroll > 100) {
                    header.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.2)';
                } else {
                    header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
                }
            }

            lastScroll = currentScroll;
        });
    }
});

export default publicWidget.registry.CustomHeaderWidget;
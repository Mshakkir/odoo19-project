/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.HidePriceRange = publicWidget.Widget.extend({
    selector: '.o_wsale_products_searchbar_form',

    start() {
        // Hide price range filter
        this.$el.find('[data-bs-target="#o_wsale_offcanvas_price_filter"]').parent().hide();
        this.$('#o_wsale_offcanvas_price_filter').hide();

        // Alternative: Hide by text
        this.$el.find('.accordion-button').each(function() {
            if ($(this).text().toLowerCase().includes('price')) {
                $(this).closest('.accordion-item').hide();
            }
        });

        return this._super(...arguments);
    },
});
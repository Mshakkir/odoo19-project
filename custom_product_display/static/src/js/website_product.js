odoo.define('custom_product_display.website_product', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    publicWidget.registry.CustomProductDisplay = publicWidget.Widget.extend({
        selector: '#products_with_inventory',
        events: {
            'click a[href*="/shop/cart?add="]': '_onAddToCart',
            'click .btn-outline-primary': '_onViewDetails',
        },

        start: function () {
            this._super.apply(this, arguments);
            console.log('Custom Product Display initialized');
        },

        _onViewDetails: function (ev) {
            // Default behavior is fine
            return true;
        },

        _onAddToCart: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            var self = this;
            var $link = $(ev.currentTarget);
            var productId = $link.data('product-id') ||
                           $link.attr('href').match(/add=(\d+)/)[1];

            // Store original content
            var originalHtml = $link.html();

            // Show loading state
            $link.prop('disabled', true)
                 .removeClass('btn-success')
                 .addClass('btn-secondary')
                 .html('<i class="fa fa-spinner fa-spin me-1"></i>Adding...');

            // Make AJAX call to add to cart
            ajax.jsonRpc('/shop/cart/update_json', 'call', {
                'product_id': parseInt(productId),
                'add_qty': 1
            }).then(function (data) {
                // Update cart icon
                if (data.cart_quantity) {
                    $('.my_cart_quantity, .fa-shopping-cart .my_cart_quantity').each(function() {
                        $(this).text(data.cart_quantity);
                    });

                    // Trigger cart update event
                    $(document).trigger('update_cart', data);
                }

                // Show success state
                $link.html('<i class="fa fa-check me-1"></i>Added!');

                // Restore after 2 seconds
                setTimeout(function() {
                    $link.prop('disabled', false)
                         .removeClass('btn-secondary')
                         .addClass('btn-success')
                         .html(originalHtml);
                }, 2000);

            }).catch(function (error) {
                console.error('Error adding to cart:', error);

                // Show error state
                $link.html('<i class="fa fa-times me-1"></i>Error');

                // Restore after 2 seconds
                setTimeout(function() {
                    $link.prop('disabled', false)
                         .removeClass('btn-secondary')
                         .addClass('btn-success')
                         .html(originalHtml);
                }, 2000);
            });

            return false;
        }
    });

    return publicWidget.registry.CustomProductDisplay;
});
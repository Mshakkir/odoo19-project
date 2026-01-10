// File: static/src/js/checkout_country_filter.js
odoo.define('web_delivery_countries.checkout', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.WebsiteCheckoutCountryFilter = publicWidget.Widget.extend({
        selector: 'form[name="checkout"]',
        events: {
            'change select[name="country_id"]': '_onCountryChange',
        },

        start: function () {
            this._filterCountries();
            return this._super.apply(this, arguments);
        },

        _filterCountries: function () {
            var self = this;
            var countrySelect = this.$el.find('select[name="country_id"]');

            if (!countrySelect.length) {
                return;
            }

            // Fetch allowed countries from delivery methods
            this._rpc({
                route: '/web_delivery_countries/get_allowed_countries',
                params: {},
            }).then(function (result) {
                var allowedCountries = result.country_ids || [];

                // Hide countries not in allowed list
                countrySelect.find('option').each(function () {
                    var $option = $(this);
                    var countryId = parseInt($option.val());

                    // Keep the placeholder option
                    if ($option.val() === '') {
                        return;
                    }

                    // Hide if not in allowed countries
                    if (allowedCountries.indexOf(countryId) === -1) {
                        $option.hide();
                    } else {
                        $option.show();
                    }
                });
            });
        },

        _onCountryChange: function (ev) {
            // Your custom logic on country change
            console.log('Country changed');
        },
    });

    return publicWidget.registry.WebsiteCheckoutCountryFilter;
});
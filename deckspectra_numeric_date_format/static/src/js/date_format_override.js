/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";

const formatters = registry.category("formatters");
const originalDate = formatters.get("date");
const originalDateTime = formatters.get("datetime");

patch(DateTimeField, {
    defaultProps: {
        ...DateTimeField.defaultProps,
        numeric: true,
    },
});
patch(DateTimeField.prototype, {
    setup() {
        super.setup();
        this.props.numeric = true;
    },
});

formatters.add(
    "date",
    (value, options = {}) =>
        originalDate(value, { ...options, numeric: true }),
    { force: true }
);

formatters.add(
    "datetime",
    (value, options = {}) =>
        originalDateTime(value, { ...options, numeric: true }),
    { force: true }
);

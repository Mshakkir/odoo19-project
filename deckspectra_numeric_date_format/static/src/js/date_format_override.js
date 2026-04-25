/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { DateField } from "@web/views/fields/date/date_field"; // ← ADD THIS

const formatters = registry.category("formatters");
const originalDate = formatters.get("date");
const originalDateTime = formatters.get("datetime");

// Patch DateTimeField
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

// ← ADD: Patch DateField as well
patch(DateField, {
    defaultProps: {
        ...DateField.defaultProps,
        numeric: true,
    },
});
patch(DateField.prototype, {
    setup() {
        super.setup();
        this.props.numeric = true;
    },
});

// Override formatters
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













///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { patch } from "@web/core/utils/patch";
//import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
//
//const formatters = registry.category("formatters");
//const originalDate = formatters.get("date");
//const originalDateTime = formatters.get("datetime");
//
//patch(DateTimeField, {
//    defaultProps: {
//        ...DateTimeField.defaultProps,
//        numeric: true,
//    },
//});
//patch(DateTimeField.prototype, {
//    setup() {
//        super.setup();
//        this.props.numeric = true;
//    },
//});
//
//formatters.add(
//    "date",
//    (value, options = {}) =>
//        originalDate(value, { ...options, numeric: true }),
//    { force: true }
//);
//
//formatters.add(
//    "datetime",
//    (value, options = {}) =>
//        originalDateTime(value, { ...options, numeric: true }),
//    { force: true }
//);

/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { DateField } from "@web/views/fields/date/date_field";

const formatters = registry.category("formatters");
const originalDate = formatters.get("date");
const originalDateTime = formatters.get("datetime");

function formatToNumeric(value) {
    if (!value) return "";
    // value is a luxon DateTime object
    const d = value.toFormat("dd/MM/yy");
    return d;
}

function formatDateTimeToNumeric(value) {
    if (!value) return "";
    return value.toFormat("dd/MM/yy HH:mm:ss");
}

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

// Patch DateField
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

// Override date formatter → DD/MM/YY
formatters.add(
    "date",
    (value, options = {}) => {
        if (!value) return "";
        return formatToNumeric(value);
    },
    { force: true }
);

// Override datetime formatter → DD/MM/YY HH:mm:ss
formatters.add(
    "datetime",
    (value, options = {}) => {
        if (!value) return "";
        return formatDateTimeToNumeric(value);
    },
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

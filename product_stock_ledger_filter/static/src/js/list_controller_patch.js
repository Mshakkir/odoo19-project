/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { ColumnFilterComponent } from "./column_filter_component";

// Register the component globally
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        // Make component available
        if (this.props.resModel === 'product.stock.ledger.line') {
            // Component will be used in template
        }
    },
});

// Register component in the global scope
ListController.components = {
    ...ListController.components,
    ColumnFilterComponent,
};
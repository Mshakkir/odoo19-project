/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { ColumnFilterComponent } from "./column_filter_component";

patch(ListController.prototype, {
    setup() {
        super.setup();

        // Check if this is the product stock ledger list
        if (this.props.resModel === 'product.stock.ledger.line') {
            this.showColumnFilter = true;
        }
    },
});

// Add column filter button to list view
ListController.components = {
    ...ListController.components,
    ColumnFilterComponent,
};

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { ColumnFilterComponent } from "./column_filter_component";

// Patch to add column filter component
patch(ListController.prototype, {
    get componentProps() {
        const props = super.componentProps;
        if (this.props.resModel === 'product.stock.ledger.line') {
            props.columnFilter = {
                showFilter: true,
                Component: ColumnFilterComponent,
            };
        }
        return props;
    },
});

// Add the component to ListController
ListController.components = {
    ...ListController.components,
    ColumnFilterComponent,
};
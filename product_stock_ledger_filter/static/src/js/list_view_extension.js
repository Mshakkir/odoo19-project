/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { ColumnFilterComponent } from "./column_filter_component";

// Custom List Controller with Column Filter Button
class ColumnFilterListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.columnFilterComponent = ColumnFilterComponent;
    }

    get controlPanelProps() {
        const props = super.controlPanelProps;
        if (this.props.resModel === 'product.stock.ledger.line') {
            props.columnFilter = true;
        }
        return props;
    }
}

// Create custom list view with column filter support
const columnFilterListView = {
    ...listView,
    Controller: ColumnFilterListController,
    controllerProps(genericProps, viewProps) {
        const props = listView.controllerProps(genericProps, viewProps);
        return props;
    },
};

// Register the custom view
registry.category("views").add("column_filter_list", columnFilterListView);
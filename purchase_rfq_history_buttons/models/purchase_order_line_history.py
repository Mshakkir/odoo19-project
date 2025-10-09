# purchase_rfq_history_buttons/models/purchase_order_line_history.py
from odoo import api, models, _
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _action_open_window(self, name, res_model, domain, view_mode='tree,form'):
        """Generic helper to return an action window for a domain."""
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': view_mode,
            'domain': domain,
            'target': 'current',
        }

    def action_view_sales_history(self):
        """Open sale.order.line list filtered by this product."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("Please set a product on the line first."))
        domain = [('product_id', '=', self.product_id.id)]
        return self._action_open_window(_("Sales History"), 'sale.order.line', domain)

    def action_view_purchase_history(self):
        """Open purchase.order.line list filtered by this product."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("Please set a product on the line first."))
        domain = [('product_id', '=', self.product_id.id)]
        return self._action_open_window(_("Purchase History"), 'purchase.order.line', domain)

    def action_view_stock_history(self):
        """Open stock.move list filtered by this product."""
        self.ensure_one()
        if not self.product_id:
            raise UserError(_("Please set a product on the line first."))
        domain = [('product_id', '=', self.product_id.id)]
        return self._action_open_window(_("Stock History"), 'stock.move', domain)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_sales_history_header(self):
        """Header button: open sales history for the first product line."""
        if not self.order_line:
            raise UserError(_("Please add at least one product line."))
        return self.order_line[0].action_view_sales_history()

    def action_view_purchase_history_header(self):
        if not self.order_line:
            raise UserError(_("Please add at least one product line."))
        return self.order_line[0].action_view_purchase_history()

    def action_view_stock_history_header(self):
        if not self.order_line:
            raise UserError(_("Please add at least one product line."))
        return self.order_line[0].action_view_stock_history()

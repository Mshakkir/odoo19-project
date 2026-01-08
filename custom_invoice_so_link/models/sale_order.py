from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_invoice_status(self):
        """Override to ensure proper invoice status computation"""
        super(SaleOrder, self)._compute_invoice_status()

        # Additional check for custom invoice links
        for order in self:
            if order.invoice_status == 'to invoice':
                # Check if there are any confirmed invoices linked via sale_order_id
                custom_invoices = self.env['account.move'].search([
                    ('sale_order_id', '=', order.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '!=', 'cancel')
                ])

                if custom_invoices:
                    # Check if all lines are invoiced
                    all_invoiced = all(
                        line.qty_invoiced >= line.product_uom_qty
                        for line in order.order_line
                        if not line.display_type and line.product_id
                    )

                    if all_invoiced:
                        order.invoice_status = 'invoiced'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_invoice_status(self):
        """Override to ensure proper line invoice status"""
        super(SaleOrderLine, self)._compute_invoice_status()

        # Force recalculation when invoice lines are linked
        for line in self:
            if line.product_id and not line.display_type:
                # Get actual invoiced quantity from invoice lines
                precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

                # Check both standard and custom invoice links
                invoice_lines = self.env['account.move.line'].search([
                    ('sale_line_ids', 'in', line.ids),
                    ('move_id.state', '!=', 'cancel'),
                    ('move_id.move_type', 'in', ['out_invoice', 'out_refund'])
                ])

                if invoice_lines:
                    line.qty_invoiced = sum(invoice_lines.mapped('quantity'))
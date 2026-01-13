from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse associated with this invoice line',
        domain="[('company_id', '=', company_id)]",
        copy=True
    )

    def _prepare_account_move_line(self, move=False):
        """Override to include warehouse when creating invoice lines from SO/PO"""
        res = super(AccountMoveLine, self)._prepare_account_move_line(move=move)

        # Get warehouse from sale order line or purchase order line
        if self._context.get('default_warehouse_id'):
            res['warehouse_id'] = self._context.get('default_warehouse_id')

        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _prepare_invoice_line_from_po_line(self, line):
        """Override to transfer warehouse from PO line to invoice line"""
        res = super(AccountMove, self)._prepare_invoice_line_from_po_line(line)

        # Transfer warehouse from purchase order line
        if hasattr(line, 'warehouse_id') and line.warehouse_id:
            res['warehouse_id'] = line.warehouse_id.id

        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """Override to transfer warehouse from SO line to invoice line"""
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)

        # Transfer warehouse from sale order line
        if self.warehouse_id:
            res['warehouse_id'] = self.warehouse_id.id

        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        """Override to transfer warehouse from PO line to invoice line"""
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)

        # Transfer warehouse from purchase order line
        if self.warehouse_id:
            res['warehouse_id'] = self.warehouse_id.id

        return res
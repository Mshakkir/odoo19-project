from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,
        copy=False,
        help='Warehouse associated with this invoice from the related sale order'
    )

    @api.depends('invoice_line_ids.sale_line_ids.order_id.warehouse_id')
    def _compute_warehouse_id(self):
        """
        Compute warehouse from related sale order.
        If invoice is created from a sale order, it will automatically
        get the warehouse from that order.
        """
        for move in self:
            warehouse = False
            if move.move_type in ('out_invoice', 'out_refund'):
                # Get warehouse from sale order lines
                sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
                if sale_orders:
                    # Take the first warehouse found
                    warehouse = sale_orders[0].warehouse_id

                # If no sale order, try to get from picking
                if not warehouse:
                    pickings = self.env['stock.picking'].search([
                        ('sale_id.invoice_ids', 'in', move.ids)
                    ], limit=1)
                    if pickings:
                        warehouse = pickings.picking_type_id.warehouse_id

            move.warehouse_id = warehouse

    def write(self, vals):
        """Allow manual warehouse selection"""
        return super(AccountMove, self).write(vals)
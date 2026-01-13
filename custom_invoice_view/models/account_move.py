from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=True
    )

    @api.depends('invoice_origin', 'line_ids.sale_line_ids')
    def _compute_warehouse_id(self):
        for move in self:
            warehouse = False

            # Method 1: From sale order lines (most reliable)
            sale_lines = move.line_ids.sale_line_ids
            if sale_lines:
                warehouse = sale_lines[0].order_id.warehouse_id

            # Method 2: From invoice origin
            elif move.invoice_origin:
                sale_order = self.env['sale.order'].search([
                    ('name', '=', move.invoice_origin)
                ], limit=1)
                if sale_order:
                    warehouse = sale_order.warehouse_id

            # Method 3: From stock pickings (if needed)
            if not warehouse:
                picking = self.env['stock.picking'].search([
                    ('origin', '=', move.invoice_origin)
                ], limit=1)
                if picking:
                    warehouse = picking.picking_type_id.warehouse_id

            move.warehouse_id = warehouse
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sequence_number = fields.Integer(
        string='SN',
        compute='_compute_sequence_number',
        store=False
    )

    product_code = fields.Char(
        string='P. Code',
        related='product_id.default_code',
        readonly=True
    )

    @api.depends('order_id.order_line', 'display_type')
    def _compute_sequence_number(self):
        for order in self.mapped('order_id'):
            number = 1
            # Only count lines with display_type 'product' or empty (regular lines)
            for line in order.order_line.filtered(lambda l: l.display_type in ['product', False]):
                line.sequence_number = number
                number += 1
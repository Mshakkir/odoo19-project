from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

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

    @api.depends('move_id.invoice_line_ids')
    def _compute_sequence_number(self):
        for move in self.mapped('move_id'):
            number = 1
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                line.sequence_number = number
                number += 1
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

    untaxed_amount_after_discount = fields.Monetary(
        string='Untax Amount',
        compute='_compute_untaxed_amount_after_discount',
        store=True
    )

    tax_amount = fields.Monetary(
        string='Tax Value',
        compute='_compute_tax_amount',
        store=True
    )

    @api.depends('move_id.invoice_line_ids')
    def _compute_sequence_number(self):
        for move in self.mapped('move_id'):
            number = 1
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                line.sequence_number = number
                number += 1

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_untaxed_amount_after_discount(self):
        for line in self:
            if line.display_type == 'product':
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                line.untaxed_amount_after_discount = price * line.quantity
            else:
                line.untaxed_amount_after_discount = 0.0

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids')
    def _compute_tax_amount(self):
        for line in self:
            if line.display_type == 'product':
                # Calculate tax amount from tax_ids
                line.tax_amount = line.price_tax if hasattr(line, 'price_tax') else 0.0
            else:
                line.tax_amount = 0.0
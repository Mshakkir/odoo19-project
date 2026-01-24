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

    tax_amount = fields.Monetary(
        string='Tax Value',
        compute='_compute_tax_amount',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('move_id.invoice_line_ids', 'display_type')
    def _compute_sequence_number(self):
        for move in self.mapped('move_id'):
            number = 1
            # Only count lines with display_type 'product' or empty (regular lines)
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type in ['product', False]):
                line.sequence_number = number
                number += 1

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids', 'move_id.currency_id')
    def _compute_tax_amount(self):
        for line in self:
            if line.display_type == 'product' and line.tax_ids:
                # Calculate the base price after discount
                price_after_discount = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                base_amount = price_after_discount * line.quantity

                # Compute taxes on the base amount
                tax_results = line.tax_ids.compute_all(
                    price_after_discount,
                    line.move_id.currency_id,
                    line.quantity,
                    product=line.product_id,
                    partner=line.move_id.partner_id
                )

                # Extract tax amount from computation
                line.tax_amount = tax_results['total_included'] - tax_results['total_excluded']
            else:
                line.tax_amount = 0.0
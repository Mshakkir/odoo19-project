from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """Override to propagate analytic to receivable/payable lines"""
        lines_vals_list = super()._stock_account_prepare_anglo_saxon_out_lines_vals()
        return lines_vals_list

    @api.model
    def _prepare_move_line_vals(self, line_vals):
        """Ensure analytic distribution is set on all lines"""
        return line_vals


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to automatically copy analytic_distribution
        to receivable/payable lines when invoice is created
        """
        moves = self.env['account.move'].browse([vals.get('move_id') for vals in vals_list if vals.get('move_id')])

        for vals in vals_list:
            move = moves.filtered(lambda m: m.id == vals.get('move_id'))

            # Skip if analytic_distribution already set
            if vals.get('analytic_distribution'):
                continue

            # For receivable/payable lines, copy from product lines
            if move and vals.get('account_id'):
                account = self.env['account.account'].browse(vals['account_id'])

                # If this is a receivable or payable account
                if account.account_type in ['asset_receivable', 'liability_payable']:
                    # Find analytic from product lines in the same move
                    product_lines = move.invoice_line_ids.filtered(
                        lambda l: l.analytic_distribution and l.display_type == 'product'
                    )

                    if product_lines:
                        # Use the analytic from the first product line
                        vals['analytic_distribution'] = product_lines[0].analytic_distribution

        return super().create(vals_list)

    def write(self, vals):
        """
        Override write to propagate analytic distribution when invoice lines change
        """
        res = super().write(vals)

        # When invoice line analytic is updated, update receivable/payable lines too
        if 'analytic_distribution' in vals:
            for line in self:
                if line.display_type == 'product' and line.move_id:
                    # Update receivable/payable lines in the same invoice
                    receivable_payable_lines = line.move_id.line_ids.filtered(
                        lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable']
                    )

                    if receivable_payable_lines and vals.get('analytic_distribution'):
                        receivable_payable_lines.with_context(
                            check_move_validity=False
                        ).write({
                            'analytic_distribution': vals['analytic_distribution']
                        })

        return res
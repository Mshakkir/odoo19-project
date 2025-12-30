from odoo import models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Override to add analytic distribution from invoice lines"""
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)

        # Get the reconciled invoices
        if self.reconciled_invoice_ids:
            # Get analytic distribution from invoice lines
            analytic_distribution = self._get_analytic_from_invoices()

            if analytic_distribution:
                # Add analytic distribution to the receivable/payable line
                for line_vals in line_vals_list:
                    account = self.env['account.account'].browse(line_vals.get('account_id'))
                    # Only add to receivable/payable lines, not to bank lines
                    if account.account_type in ('asset_receivable', 'liability_payable'):
                        line_vals['analytic_distribution'] = analytic_distribution

        return line_vals_list

    def _get_analytic_from_invoices(self):
        """Get analytic distribution from related invoices"""
        self.ensure_one()

        # Dictionary to aggregate analytic distributions
        total_analytic = {}
        total_amount = 0.0

        for invoice in self.reconciled_invoice_ids:
            for line in invoice.invoice_line_ids:
                if line.analytic_distribution:
                    line_amount = abs(line.price_subtotal)
                    total_amount += line_amount

                    # Aggregate analytic distributions weighted by amount
                    for analytic_id, percentage in line.analytic_distribution.items():
                        analytic_id_int = int(analytic_id)
                        weighted_value = (percentage / 100) * line_amount
                        total_analytic[analytic_id_int] = total_analytic.get(analytic_id_int, 0) + weighted_value

        # Convert back to percentage distribution
        if total_amount and total_analytic:
            final_distribution = {}
            for analytic_id, weighted_amount in total_analytic.items():
                percentage = (weighted_amount / total_amount) * 100
                final_distribution[str(analytic_id)] = round(percentage, 2)
            return final_distribution

        return {}

    def action_post(self):
        """Override post to update analytic distribution after move creation"""
        res = super().action_post()

        for payment in self:
            if payment.reconciled_invoice_ids:
                analytic_distribution = payment._get_analytic_from_invoices()

                if analytic_distribution and payment.move_id:
                    # Update the move lines with analytic distribution
                    for line in payment.move_id.line_ids:
                        if line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                            line.analytic_distribution = analytic_distribution

        return res
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountDaybookAnalyticWizard(models.TransientModel):
    _inherit = 'account.daybook.report'

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'rel_daybook_analytic_account_rel',
        'wizard_id',
        'analytic_id',
        string='Analytic Accounts'
    )

    def action_show_details(self):
        """Show account move lines filtered by selected dates and analytic accounts"""
        self.ensure_one()

        _logger.info(f"Date From: {self.date_from}, Date To: {self.date_to}")
        _logger.info(f"Selected Analytic Accounts: {self.analytic_account_ids.mapped('name')}")

        # Get all move lines in date range first
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        move_lines = self.env['account.move.line'].search(domain)
        _logger.info(f"Total move lines in date range: {len(move_lines)}")

        # If analytic accounts are selected, filter further
        if self.analytic_account_ids:
            filtered_lines = self.env['account.move.line']
            for line in move_lines:
                if line.analytic_distribution:
                    _logger.info(f"Line {line.id} analytic_distribution: {line.analytic_distribution}")
                    # Check if any selected analytic account is in the distribution
                    for acc in self.analytic_account_ids:
                        if str(acc.id) in line.analytic_distribution:
                            filtered_lines |= line
                            break

            _logger.info(f"Filtered lines with analytic: {len(filtered_lines)}")
            final_domain = [('id', 'in', filtered_lines.ids)]
        else:
            final_domain = domain

        _logger.info(f"Final domain: {final_domain}")

        return {
            'name': 'Analytic Account Details',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': final_domain,
            'target': 'current',
            'context': {'create': False},
        }
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_id',
        store=True,
        readonly=True,
    )

    @api.depends('line_ids.analytic_distribution')
    def _compute_analytic_account_id(self):
        """
        Compute the analytic account from invoice lines.
        Takes the first analytic account found in the invoice lines.
        """
        for move in self:
            analytic_account = False

            # Get invoice lines (exclude lines with display_type)
            invoice_lines = move.line_ids.filtered(
                lambda l: not l.display_type and l.analytic_distribution
            )

            if invoice_lines:
                # Get the first line's analytic distribution
                first_line = invoice_lines[0]
                if first_line.analytic_distribution:
                    # analytic_distribution is a JSON field like: {"1": 100}
                    # where keys are analytic_account_id
                    analytic_ids = [int(key) for key in first_line.analytic_distribution.keys()]
                    if analytic_ids:
                        analytic_account = self.env['account.analytic.account'].browse(analytic_ids[0])

            move.analytic_account_id = analytic_account
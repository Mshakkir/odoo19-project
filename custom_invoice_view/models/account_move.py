# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Warehouse',
        compute='_compute_analytic_account_id',
        store=True,
    )

    invoice_date_formatted = fields.Char(
        string='Invoice Date',
        compute='_compute_formatted_dates',
        store=False,
    )

    invoice_date_due_formatted = fields.Char(
        string='Due Date',
        compute='_compute_formatted_dates',
        store=False,
    )

    @api.depends('invoice_date', 'invoice_date_due')
    def _compute_formatted_dates(self):
        for move in self:
            move.invoice_date_formatted = (
                move.invoice_date.strftime('%d/%m/%Y')
                if move.invoice_date else ''
            )
            move.invoice_date_due_formatted = (
                move.invoice_date_due.strftime('%d/%m/%Y')
                if move.invoice_date_due else ''
            )

    @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_distribution')
    def _compute_analytic_account_id(self):
        """
        Compute the analytic account from invoice lines.
        Takes the first analytic account found in the product invoice lines.
        """
        for move in self:
            analytic_account_id = False

            # Check invoice_line_ids (only for invoices)
            if move.invoice_line_ids:
                for line in move.invoice_line_ids:
                    if line.analytic_distribution:
                        # analytic_distribution format: {"account_id": percentage}
                        # Example: {"5": 100} means 100% to account ID 5
                        account_ids = list(line.analytic_distribution.keys())
                        if account_ids:
                            try:
                                analytic_account_id = int(account_ids[0])
                                break  # Take first found
                            except (ValueError, TypeError):
                                continue

            move.analytic_account_id = analytic_account_id if analytic_account_id else False
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

    invoice_date_display = fields.Char(
        string='Bill Date',
        compute='_compute_date_display',
        store=False,
    )

    invoice_date_due_display = fields.Char(
        string='Due Date',
        compute='_compute_date_display',
        store=False,
    )

    # Needed for column_invisible condition in list view
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    # -------------------------------------------------------
    # SAR converted amount fields for list view
    # All use manual_currency_rate from purchase_bill_form_modified
    # Falls back to system rate if manual rate not set
    # -------------------------------------------------------

    amount_total_sar = fields.Monetary(
        string='Total (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    amount_residual_sar = fields.Monetary(
        string='Amount Due (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    amount_untaxed_sar = fields.Monetary(
        string='Tax Excluded (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    amount_tax_sar = fields.Monetary(
        string='Tax (SAR)',
        compute='_compute_sar_amounts',
        currency_field='company_currency_id',
        store=True,
    )

    @api.depends(
        'amount_total', 'amount_residual', 'amount_untaxed', 'amount_tax',
        'currency_id', 'company_id', 'invoice_date', 'date',
        'manual_currency_rate', 'manual_currency_rate_stored',
    )
    def _compute_sar_amounts(self):
        """
        Convert all amount fields to company currency (SAR)
        using manual_currency_rate when set, otherwise system rate.
        """
        for move in self:
            company = move.company_id
            invoice_currency = move.currency_id
            company_currency = company.currency_id

            # Same currency — no conversion needed
            if not invoice_currency or invoice_currency == company_currency:
                move.amount_total_sar = move.amount_total
                move.amount_residual_sar = move.amount_residual
                move.amount_untaxed_sar = move.amount_untaxed
                move.amount_tax_sar = move.amount_tax
                continue

            # Get rate: prefer manual, fallback to system
            rate = move.manual_currency_rate if hasattr(move, 'manual_currency_rate') else 0.0

            if not rate:
                # System rate fallback
                rate_date = move.invoice_date or move.date or fields.Date.today()
                try:
                    rate_record = self.env['res.currency.rate'].search([
                        ('currency_id', '=', invoice_currency.id),
                        ('company_id', '=', company.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    if rate_record and rate_record.inverse_company_rate:
                        rate = rate_record.inverse_company_rate
                    else:
                        rates = invoice_currency._get_rates(company, rate_date)
                        unit_per_sar = rates.get(invoice_currency.id, 1.0)
                        rate = (1.0 / unit_per_sar) if unit_per_sar else 1.0
                except Exception:
                    rate = 1.0

            move.amount_total_sar = move.amount_total * rate
            move.amount_residual_sar = abs(move.amount_residual) * rate
            move.amount_untaxed_sar = abs(move.amount_untaxed) * rate
            move.amount_tax_sar = abs(move.amount_tax) * rate

    @api.depends('invoice_date', 'invoice_date_due')
    def _compute_date_display(self):
        for move in self:
            move.invoice_date_display = (
                move.invoice_date.strftime('%d/%m/%y') if move.invoice_date else ''
            )
            move.invoice_date_due_display = (
                move.invoice_date_due.strftime('%d/%m/%y') if move.invoice_date_due else ''
            )

    @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_distribution')
    def _compute_analytic_account_id(self):
        """
        Compute the analytic account from invoice lines.
        Takes the first analytic account found in the product invoice lines.
        """
        for move in self:
            analytic_account_id = False
            if move.invoice_line_ids:
                for line in move.invoice_line_ids:
                    if line.analytic_distribution:
                        account_ids = list(line.analytic_distribution.keys())
                        if account_ids:
                            try:
                                analytic_account_id = int(account_ids[0])
                                break
                            except (ValueError, TypeError):
                                continue
            move.analytic_account_id = analytic_account_id if analytic_account_id else False







# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     analytic_account_id = fields.Many2one(
#         'account.analytic.account',
#         string='Warehouse',
#         compute='_compute_analytic_account_id',
#         store=True,
#     )
#
#     invoice_date_display = fields.Char(
#         string='Bill Date',
#         compute='_compute_date_display',
#         store=False,
#     )
#
#     invoice_date_due_display = fields.Char(
#         string='Due Date',
#         compute='_compute_date_display',
#         store=False,
#     )
#
#     @api.depends('invoice_date', 'invoice_date_due')
#     def _compute_date_display(self):
#         for move in self:
#             move.invoice_date_display = (
#                 move.invoice_date.strftime('%d/%m/%y') if move.invoice_date else ''
#             )
#             move.invoice_date_due_display = (
#                 move.invoice_date_due.strftime('%d/%m/%y') if move.invoice_date_due else ''
#             )
#
#     @api.depends('invoice_line_ids', 'invoice_line_ids.analytic_distribution')
#     def _compute_analytic_account_id(self):
#         """
#         Compute the analytic account from invoice lines.
#         Takes the first analytic account found in the product invoice lines.
#         """
#         for move in self:
#             analytic_account_id = False
#
#             # Check invoice_line_ids (only for invoices)
#             if move.invoice_line_ids:
#                 for line in move.invoice_line_ids:
#                     if line.analytic_distribution:
#                         # analytic_distribution format: {"account_id": percentage}
#                         # Example: {"5": 100} means 100% to account ID 5
#                         account_ids = list(line.analytic_distribution.keys())
#                         if account_ids:
#                             try:
#                                 analytic_account_id = int(account_ids[0])
#                                 break  # Take first found
#                             except (ValueError, TypeError):
#                                 continue
#
#             move.analytic_account_id = analytic_account_id if analytic_account_id else False

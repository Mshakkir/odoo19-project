# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_sales_report_data(self, report_type, record_id=None, date_from=None, date_to=None):
        """
        Get sales invoice report data based on report type
        """
        # Convert string dates to date objects if needed
        if date_from and isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
        if date_to and isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)

        if report_type == 'product' and record_id:
            # Get invoice lines with specific product
            line_domain = [
                ('product_id', '=', record_id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('display_type', 'in', [False, 'product'])  # Include product lines
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            invoice_lines = self.env['account.move.line'].search(line_domain)
            invoices = invoice_lines.mapped('move_id')

        elif report_type == 'category' and record_id:
            # Get products in category
            products = self.env['product.product'].search([
                ('categ_id', '=', record_id)
            ])
            line_domain = [
                ('product_id', 'in', products.ids),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('display_type', 'in', [False, 'product'])
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            invoice_lines = self.env['account.move.line'].search(line_domain)
            invoices = invoice_lines.mapped('move_id')

        elif report_type == 'partner' and record_id:
            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('partner_id', '=', record_id)
            ]
            if date_from:
                domain.append(('invoice_date', '>=', date_from))
            if date_to:
                domain.append(('invoice_date', '<=', date_to))
            invoices = self.search(domain)

        elif report_type == 'warehouse' and record_id:
            line_domain = [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('display_type', 'in', [False, 'product'])
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            invoice_lines = self.env['account.move.line'].search(line_domain)
            invoices = invoice_lines.mapped('move_id')

        elif report_type == 'salesman' and record_id:
            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_user_id', '=', record_id)
            ]
            if date_from:
                domain.append(('invoice_date', '>=', date_from))
            if date_to:
                domain.append(('invoice_date', '<=', date_to))
            invoices = self.search(domain)
        else:
            invoices = self.browse()

        return invoices
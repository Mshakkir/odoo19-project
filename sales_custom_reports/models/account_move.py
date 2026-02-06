# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_sales_report_data(self, report_type, record_id=None, date_from=None, date_to=None):
        """
        Get sales invoice report data based on report type
        """
        # Base domain for customer invoices that are posted
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ]

        if date_from:
            domain.append(('invoice_date', '>=', date_from))
        if date_to:
            domain.append(('invoice_date', '<=', date_to))

        if report_type == 'product' and record_id:
            # Get invoice lines with specific product
            line_domain = [
                ('product_id', '=', record_id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('display_type', '=', False)  # Exclude section and note lines
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
                ('display_type', '=', False)
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            invoice_lines = self.env['account.move.line'].search(line_domain)
            invoices = invoice_lines.mapped('move_id')

        elif report_type == 'partner' and record_id:
            domain.append(('partner_id', '=', record_id))
            invoices = self.search(domain)

        elif report_type == 'warehouse' and record_id:
            # For invoices, we can check the warehouse from picking or use a custom field
            # Here we'll search for invoices related to stock pickings from that warehouse
            line_domain = [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('display_type', '=', False)
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            invoice_lines = self.env['account.move.line'].search(line_domain)
            # Filter by warehouse if there's a link, otherwise get all
            # This is a simplified approach - you may need to customize based on your workflow
            invoices = invoice_lines.mapped('move_id')

        elif report_type == 'salesman' and record_id:
            domain.append(('invoice_user_id', '=', record_id))
            invoices = self.search(domain)
        else:
            invoices = self.browse()

        return invoices
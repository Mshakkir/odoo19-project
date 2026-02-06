# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_sales_report_data(self, report_type, record_id=None, date_from=None, date_to=None):
        """
        Get sales invoice report data based on report type
        """
        _logger.info("=" * 80)
        _logger.info("DEBUG: get_sales_report_data called")
        _logger.info(f"DEBUG: report_type = {report_type}")
        _logger.info(f"DEBUG: record_id = {record_id}")
        _logger.info(f"DEBUG: date_from = {date_from} (type: {type(date_from)})")
        _logger.info(f"DEBUG: date_to = {date_to} (type: {type(date_to)})")

        # Convert string dates to date objects if needed
        if date_from and isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
            _logger.info(f"DEBUG: date_from converted to {date_from}")
        if date_to and isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)
            _logger.info(f"DEBUG: date_to converted to {date_to}")

        if report_type == 'product' and record_id:
            _logger.info(f"DEBUG: Processing PRODUCT report for product_id = {record_id}")

            # First, let's check if the product exists
            product = self.env['product.product'].browse(record_id)
            _logger.info(f"DEBUG: Product found = {product.name if product else 'NOT FOUND'}")

            # Get invoice lines with specific product
            line_domain = [
                ('product_id', '=', record_id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
            ]

            _logger.info(f"DEBUG: Initial line_domain (before date filter) = {line_domain}")

            # Search without date filter first to see if there are ANY lines
            all_lines = self.env['account.move.line'].search(line_domain)
            _logger.info(f"DEBUG: Found {len(all_lines)} invoice lines WITHOUT date filter")

            if all_lines:
                for line in all_lines:
                    _logger.info(f"DEBUG: Line ID={line.id}, Product={line.product_id.name}, "
                                 f"Invoice={line.move_id.name}, Invoice Date={line.move_id.invoice_date}, "
                                 f"Display Type={line.display_type}")

            # Now add date filters
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            _logger.info(f"DEBUG: Final line_domain (with date filter) = {line_domain}")

            invoice_lines = self.env['account.move.line'].search(line_domain)
            _logger.info(f"DEBUG: Found {len(invoice_lines)} invoice lines WITH date filter")

            if invoice_lines:
                for line in invoice_lines:
                    _logger.info(f"DEBUG: Filtered Line ID={line.id}, Product={line.product_id.name}, "
                                 f"Invoice={line.move_id.name}, Invoice Date={line.move_id.invoice_date}")

            invoices = invoice_lines.mapped('move_id')
            _logger.info(f"DEBUG: Final invoices count = {len(invoices)}")

            if invoices:
                for inv in invoices:
                    _logger.info(
                        f"DEBUG: Invoice = {inv.name}, Date = {inv.invoice_date}, Partner = {inv.partner_id.name}")

        elif report_type == 'category' and record_id:
            _logger.info(f"DEBUG: Processing CATEGORY report for category_id = {record_id}")

            # Get products in category
            products = self.env['product.product'].search([
                ('categ_id', '=', record_id)
            ])
            _logger.info(f"DEBUG: Found {len(products)} products in category")

            line_domain = [
                ('product_id', 'in', products.ids),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            _logger.info(f"DEBUG: line_domain = {line_domain}")

            invoice_lines = self.env['account.move.line'].search(line_domain)
            _logger.info(f"DEBUG: Found {len(invoice_lines)} invoice lines")

            invoices = invoice_lines.mapped('move_id')
            _logger.info(f"DEBUG: Final invoices count = {len(invoices)}")

        elif report_type == 'partner' and record_id:
            _logger.info(f"DEBUG: Processing PARTNER report for partner_id = {record_id}")

            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('partner_id', '=', record_id)
            ]
            if date_from:
                domain.append(('invoice_date', '>=', date_from))
            if date_to:
                domain.append(('invoice_date', '<=', date_to))

            _logger.info(f"DEBUG: domain = {domain}")
            invoices = self.search(domain)
            _logger.info(f"DEBUG: Final invoices count = {len(invoices)}")

        elif report_type == 'warehouse' and record_id:
            _logger.info(f"DEBUG: Processing WAREHOUSE report for warehouse_id = {record_id}")

            line_domain = [
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
            ]
            if date_from:
                line_domain.append(('move_id.invoice_date', '>=', date_from))
            if date_to:
                line_domain.append(('move_id.invoice_date', '<=', date_to))

            _logger.info(f"DEBUG: line_domain = {line_domain}")

            invoice_lines = self.env['account.move.line'].search(line_domain)
            _logger.info(f"DEBUG: Found {len(invoice_lines)} invoice lines")

            invoices = invoice_lines.mapped('move_id')
            _logger.info(f"DEBUG: Final invoices count = {len(invoices)}")

        elif report_type == 'salesman' and record_id:
            _logger.info(f"DEBUG: Processing SALESMAN report for user_id = {record_id}")

            domain = [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_user_id', '=', record_id)
            ]
            if date_from:
                domain.append(('invoice_date', '>=', date_from))
            if date_to:
                domain.append(('invoice_date', '<=', date_to))

            _logger.info(f"DEBUG: domain = {domain}")
            invoices = self.search(domain)
            _logger.info(f"DEBUG: Final invoices count = {len(invoices)}")
        else:
            _logger.info("DEBUG: No matching report type or record_id is None")
            invoices = self.browse()

        _logger.info(f"DEBUG: Returning {len(invoices)} invoices")
        _logger.info("=" * 80)
        return invoices
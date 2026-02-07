# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ReportByProductWizard(models.TransientModel):
    _name = 'report.by.product.wizard'
    _description = 'Report by Product Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All')
    ], string='Invoice Status', default='all')

    def action_apply(self):
        """Apply filter and show product report - DEBUG VERSION"""
        self.ensure_one()

        _logger.info("=" * 80)
        _logger.info("DEBUG: Report by Product Wizard - action_apply() called")
        _logger.info("=" * 80)

        # Log wizard parameters
        _logger.info(f"Product ID: {self.product_id.id}")
        _logger.info(f"Product Name: {self.product_id.display_name}")
        _logger.info(f"Date From: {self.date_from}")
        _logger.info(f"Date To: {self.date_to}")
        _logger.info(f"Invoice State: {self.invoice_state}")

        # Check if SQL view has any data at all
        self.env.cr.execute("SELECT COUNT(*) FROM product_invoice_report")
        total_count = self.env.cr.fetchone()[0]
        _logger.info(f"Total records in product_invoice_report view: {total_count}")

        # Check records for this specific product
        self.env.cr.execute("""
            SELECT COUNT(*) 
            FROM product_invoice_report 
            WHERE product_id = %s
        """, (self.product_id.id,))
        product_count = self.env.cr.fetchone()[0]
        _logger.info(f"Records for product {self.product_id.id}: {product_count}")

        # Show sample records for this product
        if product_count > 0:
            self.env.cr.execute("""
                SELECT invoice_number, invoice_state, invoice_date, quantity, price_subtotal
                FROM product_invoice_report 
                WHERE product_id = %s
                LIMIT 5
            """, (self.product_id.id,))
            _logger.info("Sample records from SQL view:")
            for row in self.env.cr.fetchall():
                _logger.info(f"  Invoice: {row[0]}, State: {row[1]}, Date: {row[2]}, Qty: {row[3]}, Amount: {row[4]}")

        # Check invoice lines directly
        self.env.cr.execute("""
            SELECT am.name, am.state, am.invoice_date, ail.quantity, ail.price_subtotal
            FROM account_move_line ail
            JOIN account_move am ON ail.move_id = am.id
            WHERE am.move_type IN ('out_invoice', 'out_refund')
            AND ail.product_id = %s
            AND ail.display_type IS NULL
            LIMIT 5
        """, (self.product_id.id,))
        direct_results = self.env.cr.fetchall()
        _logger.info(f"Direct query from account_move_line: {len(direct_results)} records")
        for row in direct_results:
            _logger.info(f"  Invoice: {row[0]}, State: {row[1]}, Date: {row[2]}, Qty: {row[3]}, Amount: {row[4]}")

        # Build domain for the report model
        domain = [('product_id', '=', self.product_id.id)]

        _logger.info(f"Initial domain: {domain}")

        # Only filter by state if not 'all'
        if self.invoice_state and self.invoice_state != 'all':
            domain.append(('invoice_state', '=', self.invoice_state))
            _logger.info(f"Added state filter: invoice_state = {self.invoice_state}")

        # Only add date filters if they are set
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
            _logger.info(f"Added date_from filter: >= {self.date_from}")
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
            _logger.info(f"Added date_to filter: <= {self.date_to}")

        _logger.info(f"Final domain: {domain}")

        # Test the domain
        test_records = self.env['product.invoice.report'].search(domain)
        _logger.info(f"Records matching domain: {len(test_records)}")

        if test_records:
            _logger.info("Sample matching records:")
            for rec in test_records[:5]:
                _logger.info(
                    f"  ID: {rec.id}, Invoice: {rec.invoice_number}, State: {rec.invoice_state}, Date: {rec.invoice_date}")
        else:
            _logger.warning("NO RECORDS MATCH THE DOMAIN!")

            # Try without filters
            all_records = self.env['product.invoice.report'].search([('product_id', '=', self.product_id.id)])
            _logger.info(f"Records without date/state filter: {len(all_records)}")
            if all_records:
                _logger.info("Records exist but are filtered out by date or state!")
                for rec in all_records[:3]:
                    _logger.info(
                        f"  Invoice: {rec.invoice_number}, State: {rec.invoice_state}, Date: {rec.invoice_date}")

        _logger.info("=" * 80)
        _logger.info("END DEBUG")
        _logger.info("=" * 80)

        return {
            'name': f'Sales Report - {self.product_id.display_name}',
            'type': 'ir.actions.act_window',
            'res_model': 'product.invoice.report',
            'view_mode': 'list,pivot,graph',
            'domain': domain,
            'context': {'search_default_product_id': self.product_id.id},
            'target': 'current',
        }
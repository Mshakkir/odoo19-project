# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def get_product_purchase_history(self, product_id):
        """
        Fetch purchase history for a given product from vendor bills
        Returns list of invoice lines with supplier info
        """
        _logger.info("=" * 80)
        _logger.info("PURCHASE HISTORY - Product ID: %s", product_id)

        if not product_id:
            return []

        # First, let's check if there are ANY lines with this product
        all_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
        ])
        _logger.info("Total lines with product_id=%s: %s", product_id, len(all_lines))

        # Check move types
        for line in all_lines[:5]:  # Check first 5
            _logger.info("  Line ID %s: move_type=%s, state=%s, display_type=%s",
                         line.id,
                         line.move_id.move_type if line.move_id else 'NO MOVE',
                         line.move_id.state if line.move_id else 'NO STATE',
                         line.display_type if hasattr(line, 'display_type') else 'NO ATTR')

        # Now search for vendor bills specifically
        invoice_lines = self.env['account.move.line'].search([
            ('product_id', '=', product_id),
            ('move_id.move_type', '=', 'in_invoice'),
        ], limit=50)

        _logger.info("Vendor bill lines found: %s", len(invoice_lines))

        history = []
        for line in invoice_lines:
            _logger.info("Processing line ID: %s", line.id)

            # Skip if move is not in valid state
            if line.move_id.state not in ['draft', 'posted']:
                _logger.info("  SKIP: state=%s", line.move_id.state)
                continue

            # Skip lines without product
            if not line.product_id:
                _logger.info("  SKIP: no product")
                continue

            # Skip display lines (section/note)
            if hasattr(line, 'display_type') and line.display_type:
                _logger.info("  SKIP: display_type=%s", line.display_type)
                continue

            _logger.info("  ADDING to history")

            history.append({
                'id': line.id,
                'order_name': line.move_id.name or '',
                'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
                'date_order': line.move_id.invoice_date.strftime('%Y-%m-%d') if line.move_id.invoice_date else '',
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.name if line.product_uom_id else '',
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'currency': line.currency_id.symbol if line.currency_id else '',
                'state': line.move_id.state,
            })

        # Sort by date in Python (descending)
        history.sort(key=lambda x: x['date_order'], reverse=True)

        _logger.info("Final history count: %s", len(history))
        _logger.info("=" * 80)

        return history
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
        _logger.info("PURCHASE HISTORY DEBUG - START")
        _logger.info("Product ID received: %s (type: %s)", product_id, type(product_id))

        if not product_id:
            _logger.warning("No product_id provided!")
            return []

        try:
            # Search for vendor bill lines with this product
            _logger.info("Starting search for vendor bill lines...")
            _logger.info("Search domain: [('product_id', '=', %s), ('move_id.move_type', '=', 'in_invoice')]",
                         product_id)

            invoice_lines = self.env['account.move.line'].search([
                ('product_id', '=', product_id),
                ('move_id.move_type', '=', 'in_invoice'),
            ], order='move_id.date desc', limit=50)

            _logger.info("Search completed. Found %s lines", len(invoice_lines))

            history = []
            for idx, line in enumerate(invoice_lines):
                _logger.info("Processing line %s/%s (ID: %s)", idx + 1, len(invoice_lines), line.id)

                try:
                    # Log line details
                    _logger.info("  - Move: %s", line.move_id.name if line.move_id else 'NO MOVE')
                    _logger.info("  - State: %s", line.move_id.state if line.move_id else 'NO STATE')
                    _logger.info("  - Product: %s", line.product_id.name if line.product_id else 'NO PRODUCT')

                    # Skip if move is not in valid state
                    if not line.move_id or line.move_id.state not in ['draft', 'posted']:
                        _logger.info("  - SKIPPED: Invalid state")
                        continue

                    # Skip lines without product
                    if not line.product_id:
                        _logger.info("  - SKIPPED: No product")
                        continue

                    # Skip display lines (section/note)
                    if hasattr(line, 'display_type') and line.display_type:
                        _logger.info("  - SKIPPED: Display type = %s", line.display_type)
                        continue

                    # Build history record
                    _logger.info("  - Building history record...")

                    record = {
                        'id': line.id,
                        'order_name': line.move_id.name or '',
                        'partner_name': line.move_id.partner_id.name if line.move_id.partner_id else '',
                    }
                    _logger.info("  - Basic fields OK")

                    # Date handling
                    if line.move_id.invoice_date:
                        record['date_order'] = line.move_id.invoice_date.strftime('%Y-%m-%d')
                    elif line.move_id.date:
                        record['date_order'] = line.move_id.date.strftime('%Y-%m-%d')
                    else:
                        record['date_order'] = ''
                    _logger.info("  - Date: %s", record['date_order'])

                    # Quantity and UOM
                    record['product_qty'] = line.quantity
                    record['product_uom'] = line.product_uom_id.name if line.product_uom_id else ''
                    _logger.info("  - Quantity: %s %s", record['product_qty'], record['product_uom'])

                    # Prices
                    record['price_unit'] = line.price_unit
                    record['price_subtotal'] = line.price_subtotal
                    _logger.info("  - Price unit: %s", record['price_unit'])
                    _logger.info("  - Subtotal: %s", record['price_subtotal'])

                    # Currency
                    record['currency'] = line.currency_id.symbol if line.currency_id else ''
                    _logger.info("  - Currency: %s", record['currency'])

                    # State
                    record['state'] = line.move_id.state
                    _logger.info("  - State: %s", record['state'])

                    history.append(record)
                    _logger.info("  - Record added successfully!")

                except Exception as line_error:
                    _logger.error("Error processing line %s: %s", line.id, str(line_error))
                    _logger.exception("Full traceback:")
                    continue

            _logger.info("Processing complete. Total records: %s", len(history))
            _logger.info("PURCHASE HISTORY DEBUG - END")
            _logger.info("=" * 80)

            return history

        except Exception as e:
            _logger.error("CRITICAL ERROR in get_product_purchase_history: %s", str(e))
            _logger.exception("Full traceback:")
            _logger.info("=" * 80)
            raise
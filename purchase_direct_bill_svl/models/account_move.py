from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_direct_bill = fields.Boolean(
        string='Direct Bill (No PO)',
        default=False,
        help='If enabled, SVL will be auto-created on bill confirmation'
    )
    auto_create_svl = fields.Boolean(
        string='Auto Create Stock Valuation',
        default=True,
    )
    svl_created = fields.Boolean(
        string='SVL Created',
        default=False,
        readonly=True,
        copy=False,
    )

    def action_post(self):
        """Override to create SVL when posting direct bills."""
        res = super().action_post()
        for move in self:
            if (move.move_type == 'in_invoice'
                    and move.is_direct_bill
                    and move.auto_create_svl
                    and not move.svl_created):
                try:
                    move._create_svl_for_direct_bill()
                except Exception as e:
                    _logger.error(
                        'SVL creation failed for bill %s: %s',
                        move.name, str(e)
                    )
                    raise UserError(
                        _('SVL Creation Error: %s\n\n'
                          'Please check that stock_account module '
                          'is installed.') % str(e)
                    )
        return res

    def _is_storable_product(self, product):
        """
        Check if product is storable in Odoo 19.
        In Odoo 17+, storable products use detailed_type='product'
        """
        if not product:
            return False

        # Odoo 19 / 17+ way
        if hasattr(product, 'detailed_type'):
            return product.detailed_type == 'product'

        # Odoo 16 and below fallback
        return product.type == 'product'

    def _is_auto_valuation(self, product):
        """
        Check if product category uses automated/perpetual valuation.
        """
        categ = product.categ_id
        if not categ:
            return False

        # Check property_valuation on category
        valuation = categ.property_valuation
        return valuation == 'real_time'

    def _create_svl_for_direct_bill(self):
        """
        Create Stock Valuation Layers and Stock Moves
        for direct vendor bills without PO.
        Compatible with Odoo 19 CE.
        """

        # --- Safety Check: Ensure stock.valuation.layer exists ---
        # Use self.env.registry instead of self.env for reliable model check
        if 'stock.valuation.layer' not in self.env.registry:
            raise UserError(_(
                'stock.valuation.layer model not found.\n'
                'Please ensure the following modules are installed:\n'
                '- stock_account\n'
                '- stock_landed_costs'
            ))

        svl_model = self.env['stock.valuation.layer']
        stock_move_model = self.env['stock.move']

        # Get supplier location
        supplier_location = self.env.ref(
            'stock.stock_location_suppliers',
            raise_if_not_found=False
        )
        if not supplier_location:
            supplier_location = self.env['stock.location'].search([
                ('usage', '=', 'supplier')
            ], limit=1)

        if not supplier_location:
            raise UserError(_(
                'Supplier stock location not found. '
                'Please check your stock configuration.'
            ))

        svl_created_count = 0

        for line in self.invoice_line_ids:
            product = line.product_id

            # --- Check 1: Product must exist ---
            if not product:
                continue

            # --- Check 2: Must be storable product (Odoo 19 compatible) ---
            if not self._is_storable_product(product):
                _logger.info(
                    'Skipping product %s - not a storable product '
                    '(detailed_type=%s)',
                    product.name,
                    getattr(product, 'detailed_type', product.type)
                )
                continue

            # --- Check 3: Must use automated/perpetual valuation ---
            if not self._is_auto_valuation(product):
                _logger.info(
                    'Skipping product %s - not using automated valuation',
                    product.name
                )
                continue

            # --- Check 4: Skip if already linked to PO ---
            if line.purchase_line_id:
                _logger.info(
                    'Skipping product %s - already linked to PO',
                    product.name
                )
                continue

            # --- Get destination location ---
            dest_location = self._get_incoming_location(line)

            # --- Calculate unit cost (price without tax) ---
            unit_cost = line.price_unit
            quantity = line.quantity

            if quantity <= 0:
                continue

            _logger.info(
                'Creating SVL for product %s: qty=%s, cost=%s',
                product.name, quantity, unit_cost
            )

            # --- Create Stock Move ---
            stock_move_vals = {
                'name': _('Direct Bill: %s') % self.name,
                'product_id': product.id,
                'product_uom_qty': quantity,
                'product_uom': line.product_uom_id.id
                    if line.product_uom_id
                    else product.uom_id.id,
                'location_id': supplier_location.id,
                'location_dest_id': dest_location.id,
                'state': 'done',
                'origin': self.name,
                'company_id': self.company_id.id,
                'price_unit': unit_cost,
            }
            stock_move = stock_move_model.sudo().create(stock_move_vals)

            # --- Create Stock Move Line ---
            self.env['stock.move.line'].sudo().create({
                'move_id': stock_move.id,
                'product_id': product.id,
                'product_uom_id': line.product_uom_id.id
                    if line.product_uom_id
                    else product.uom_id.id,
                'qty_done': quantity,
                'location_id': supplier_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.company_id.id,
            })

            # --- Create Stock Valuation Layer (SVL) ---
            total_value = unit_cost * quantity
            svl_vals = {
                'product_id': product.id,
                'quantity': quantity,
                'unit_cost': unit_cost,
                'value': total_value,
                'remaining_qty': quantity,
                'remaining_value': total_value,
                'stock_move_id': stock_move.id,
                'company_id': self.company_id.id,
                'description': _(
                    'Direct Bill %s - %s'
                ) % (self.name, product.name),
            }
            svl = svl_model.sudo().create(svl_vals)

            _logger.info(
                'SVL created: id=%s, product=%s, value=%s',
                svl.id, product.name, total_value
            )

            # --- Update product standard price if Standard Price method ---
            costing_method = product.categ_id.property_cost_method
            if costing_method == 'standard':
                product.sudo().write({'standard_price': unit_cost})

            # --- Update AVCO cost ---
            elif costing_method == 'average':
                # Recalculate average cost
                existing_qty = product.qty_available - quantity
                existing_value = existing_qty * product.standard_price
                new_avg = (existing_value + total_value) / (
                    existing_qty + quantity
                ) if (existing_qty + quantity) > 0 else unit_cost
                product.sudo().write({'standard_price': new_avg})

            svl_created_count += 1

        # --- Mark SVL as created ---
        if svl_created_count > 0:
            self.sudo().write({'svl_created': True})
            _logger.info(
                'Successfully created %s SVL(s) for bill %s',
                svl_created_count, self.name
            )
        else:
            _logger.warning(
                'No SVL created for bill %s - '
                'check product types and valuation settings',
                self.name
            )
            raise UserError(_(
                'No Stock Valuation Layers were created!\n\n'
                'Please check:\n'
                '1. Products are set as "Storable Product"\n'
                '2. Product Category Inventory Valuation = '
                '"Perpetual (at invoicing)"\n'
                '3. stock_account module is installed'
            ))

    def _get_incoming_location(self, line):
        """
        Get the correct incoming stock location for the product.
        """
        # Try warehouse default location
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if warehouse and warehouse.lot_stock_id:
            return warehouse.lot_stock_id

        # Fallback: search for internal location
        internal_location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if internal_location:
            return internal_location

        # Last fallback
        return self.env.ref(
            'stock.stock_location_stock',
            raise_if_not_found=True
        )

    def button_create_svl_manually(self):
        """Manual button to create SVL if auto-creation was skipped."""
        self.ensure_one()

        if self.move_type != 'in_invoice':
            raise UserError(_(
                'SVL can only be created for vendor bills.'
            ))
        if self.state != 'posted':
            raise UserError(_(
                'Please confirm/post the bill first before '
                'creating SVL manually.'
            ))
        if self.svl_created:
            raise UserError(_(
                'SVL has already been created for this bill. '
                'Cannot create duplicate SVL.'
            ))

        self._create_svl_for_direct_bill()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _(
                    'Stock Valuation Layers created successfully '
                    'for bill %s'
                ) % self.name,
                'type': 'success',
                'sticky': False,
            }
        }
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# ============================================================================
# CRITICAL: Odoo 19 CE has multiple SVL model name variants
# Try all known variants; the diagnostic script will identify the correct one
# ============================================================================
SVL_MODEL_CANDIDATES = [
    # Standard name (most common)
    'stock.valuation.layer',

    # Odoo 19.0 with stock_account refactoring
    'stock_account.valuation.layer',
    'stock.account.valuation.layer',

    # Odoo 18 → 19 migration variant
    'account.stock.valuation.report',

    # If stock_landed_costs extends the model
    'stock.valuation.layer.revaluation',

    # As a fallback, try the adjustment model
    'stock.valuation.adjustment.lines',
]


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
                except UserError:
                    # Re-raise UserError as-is (our diagnostic messages)
                    raise
                except Exception as e:
                    _logger.error(
                        'SVL creation failed for bill %s: %s',
                        move.name, str(e), exc_info=True
                    )
                    raise UserError(
                        _('SVL Creation Error: %s\n\n'
                          'The stock.valuation.layer model could not be instantiated.\n\n'
                          'NEXT STEP:\n'
                          '1. Run: python manage.py shell\n'
                          '2. Then: exec(open("diagnostic_shell.py").read())\n'
                          '3. Share the output so the correct model name can be identified.\n\n'
                          'Technical: %s') % (
                            str(e)[:200],
                            str(e)[-100:]
                        )
                    )
        return res

    def _is_storable_product(self, product):
        """
        Check if product needs stock valuation in Odoo 19 CE.

        Odoo 19 CE: Product Type = 'Goods' + Track Inventory = True
        Internally this is type='consu' with tracking enabled,
        OR type='product' depending on the WMS module variant.
        """
        if not product:
            return False

        # Method 1: explicit is_storable property (some Odoo 19 builds)
        if hasattr(product, 'is_storable'):
            return bool(product.is_storable)

        # Method 2: detailed_type (Odoo 16-18 style)
        if hasattr(product, 'detailed_type'):
            if product.detailed_type == 'product':
                return True
            if product.detailed_type == 'consu':
                return self._product_tracks_inventory(product)

        # Method 3: base type field
        if product.type == 'product':
            return True

        # Odoo 19 CE: type='consu' (Goods) + Track Inventory = True
        if product.type == 'consu':
            return self._product_tracks_inventory(product)

        return False

    def _product_tracks_inventory(self, product):
        """
        Odoo 19 CE: 'Goods' + Track Inventory checkbox ticked.
        The checkbox is stored in various ways depending on build.
        """
        tmpl = getattr(product, 'product_tmpl_id', product)
        for field_name in ['is_storable', 'storable_ok',
                           'inventory_tracking', 'track_inventory']:
            if hasattr(tmpl, field_name) and getattr(tmpl, field_name):
                return True

        # Lot/Serial tracking means inventory is tracked
        tracking = getattr(product, 'tracking', 'none')
        if tracking and tracking != 'none':
            return True

        return product.type == 'consu'

    def _is_auto_valuation(self, product):
        """Check if product category uses automated/perpetual valuation."""
        categ = product.categ_id
        if not categ:
            return False
        valuation = getattr(categ, 'property_valuation', None)
        return valuation == 'real_time'

    def _get_svl_model(self):
        """
        Safely retrieve the stock.valuation.layer model.
        Tries multiple known model names for WMS module compatibility.

        Returns: model instance or raises UserError with diagnostics.
        """
        attempted_models = []

        for model_name in SVL_MODEL_CANDIDATES:
            try:
                # Check if model is in registry
                if model_name not in self.env.registry.models:
                    attempted_models.append(f"{model_name}: NOT IN REGISTRY")
                    continue

                # Try to instantiate
                model = self.env[model_name]

                # Try a simple search to verify it's actually usable
                test_count = model.search_count([('id', '=', 0)])

                _logger.info(
                    'SVL model found and working: %s', model_name
                )
                return model

            except Exception as ex:
                attempted_models.append(
                    f"{model_name}: {str(ex)[:80]}"
                )
                _logger.warning(
                    'Model %s failed: %s', model_name, str(ex)[:100]
                )
                continue

        # If we get here, none of the candidates worked
        # Collect ALL models for diagnostic purposes
        all_models = sorted(self.env.registry.models.keys())
        valuation_models = sorted([
            m for m in all_models
            if any(kw in m.lower() for kw in [
                'valuation', 'svl', 'layer', 'stock.account', 'adjustment'
            ])
        ])

        _logger.error(
            'No SVL model found. '
            'Attempted: %s. '
            'Valuation-related models available: %s',
            attempted_models, valuation_models
        )

        # Build user-friendly error with diagnostic data
        error_msg = (
            'Cannot find stock.valuation.layer model.\n\n'
            'Attempted models:\n'
        )
        for attempt in attempted_models:
            error_msg += f'  ✗ {attempt}\n'

        error_msg += '\n\nValuation-related models in your system:\n'
        for m in valuation_models:
            error_msg += f'  ✓ {m}\n'

        error_msg += (
            '\n\nTO FIX:\n'
            '1. Ensure stock_account module is INSTALLED (not just enabled)\n'
            '2. Run this in Odoo shell:\n'
            '   $ python manage.py shell\n'
            '   >>> exec(open("diagnostic_shell.py").read())\n'
            '3. Share the output to identify the correct model name\n'
            '4. Update SVL_MODEL_CANDIDATES in account_move.py\n\n'
            'Common causes:\n'
            '  • stock_account module not installed (stuck in "To Install")\n'
            '  • Odoo 19 CE variant with different naming\n'
            '  • stock_landed_costs extends the model with different name\n'
        )

        raise UserError(error_msg)

    def _create_svl_for_direct_bill(self):
        """
        Create Stock Valuation Layers and Stock Moves
        for direct vendor bills without PO.
        Compatible with Odoo 19 CE (Goods + Track Inventory).
        """
        _logger.info(
            'Starting SVL creation for direct bill: %s', self.name
        )

        svl_model = self._get_svl_model()
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
                'Please check your stock configuration.\n\n'
                'Go to: Inventory → Configuration → Locations\n'
                'Create a location with Usage = "Supplier"'
            ))

        svl_created_count = 0
        diag_products = []

        for line in self.invoice_line_ids:
            product = line.product_id

            if not product:
                continue

            # Diagnostic tracking
            product_diag = {
                'name': product.name,
                'type': product.type,
                'tracking': getattr(product, 'tracking', 'N/A'),
                'is_storable': getattr(product, 'is_storable', 'N/A'),
            }
            diag_products.append(product_diag)

            if not self._is_storable_product(product):
                _logger.info(
                    'Skipping %s - not storable '
                    '(type=%s, tracking=%s, is_storable=%s)',
                    product.name, product.type,
                    getattr(product, 'tracking', 'N/A'),
                    getattr(product, 'is_storable', 'N/A'),
                )
                continue

            if not self._is_auto_valuation(product):
                _logger.info(
                    'Skipping %s - not real_time valuation '
                    '(property_valuation=%s)',
                    product.name,
                    getattr(product.categ_id, 'property_valuation', 'N/A'),
                )
                continue

            if line.purchase_line_id:
                _logger.info(
                    'Skipping %s - linked to PO', product.name)
                continue

            dest_location = self._get_incoming_location(line)
            unit_cost = line.price_unit
            quantity = line.quantity

            if quantity <= 0:
                continue

            _logger.info(
                'Creating SVL for %s: qty=%s, cost=%s',
                product.name, quantity, unit_cost
            )

            # --- Create Stock Move ---
            stock_move = stock_move_model.sudo().create({
                'name': _('Direct Bill: %s') % self.name,
                'product_id': product.id,
                'product_uom_qty': quantity,
                'product_uom': (
                    line.product_uom_id.id
                    if line.product_uom_id else product.uom_id.id
                ),
                'location_id': supplier_location.id,
                'location_dest_id': dest_location.id,
                'state': 'done',
                'origin': self.name,
                'company_id': self.company_id.id,
                'price_unit': unit_cost,
            })

            # --- Create Stock Move Line ---
            self.env['stock.move.line'].sudo().create({
                'move_id': stock_move.id,
                'product_id': product.id,
                'product_uom_id': (
                    line.product_uom_id.id
                    if line.product_uom_id else product.uom_id.id
                ),
                'qty_done': quantity,
                'location_id': supplier_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.company_id.id,
            })

            # --- Create Stock Valuation Layer ---
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
                    'Direct Bill %s - %s') % (self.name, product.name),
            }

            # Only add account_move_id if the field exists
            if 'account_move_id' in svl_model._fields:
                svl_vals['account_move_id'] = self.id

            svl = svl_model.sudo().create(svl_vals)
            _logger.info(
                'SVL created: id=%s, product=%s, value=%s',
                svl.id, product.name, total_value
            )

            # --- Update product cost price ---
            costing_method = getattr(
                product.categ_id, 'property_cost_method', False)
            if costing_method == 'standard':
                product.sudo().write({'standard_price': unit_cost})
            elif costing_method == 'average':
                existing_qty = product.qty_available - quantity
                existing_value = existing_qty * product.standard_price
                new_avg = (
                    (existing_value + total_value) / (existing_qty + quantity)
                    if (existing_qty + quantity) > 0 else unit_cost
                )
                product.sudo().write({'standard_price': new_avg})

            svl_created_count += 1

        # --- Mark SVL as created or raise helpful error ---
        if svl_created_count > 0:
            self.sudo().write({'svl_created': True})
            _logger.info(
                'Created %s SVL(s) for bill %s',
                svl_created_count, self.name
            )
        else:
            # Build diagnostic info for the error message
            diag = []
            for p_diag in diag_products:
                diag.append(
                    '• %s: type=%s | tracking=%s | is_storable=%s' % (
                        p_diag['name'],
                        p_diag['type'],
                        p_diag['tracking'],
                        p_diag['is_storable'],
                    )
                )

            raise UserError(_(
                'No Stock Valuation Layers were created!\n\n'
                'This usually means:\n\n'
                '1. PRODUCT CONFIGURATION:\n'
                '   Products must have:\n'
                '     ✓ Type = "Goods"\n'
                '     ✓ Track Inventory = Checked\n'
                '   Current products:\n%s\n\n'
                '2. CATEGORY COSTING METHOD:\n'
                '   Go to: Inventory → Configuration → Product Categories\n'
                '   Edit each category used by your products:\n'
                '     ✓ Costing Method = "Average Cost" or "Standard"\n'
                '     ✓ Inventory Valuation = "Automated (Perpetual)"\n\n'
                '3. IF STILL FAILING:\n'
                '   Run the diagnostic script (see error message from SVL model lookup)\n'
                '   to identify which model name is being used.'
            ) % '\n'.join(diag))

    def _get_incoming_location(self, line):
        """Get the correct incoming stock location."""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if warehouse and warehouse.lot_stock_id:
            return warehouse.lot_stock_id

        internal_location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if internal_location:
            return internal_location

        return self.env.ref(
            'stock.stock_location_stock',
            raise_if_not_found=True
        )

    def button_create_svl_manually(self):
        """Manual button to create SVL if auto-creation was skipped."""
        self.ensure_one()

        if self.move_type != 'in_invoice':
            raise UserError(_('SVL can only be created for vendor bills.'))
        if self.state != 'posted':
            raise UserError(_(
                'Please confirm/post the bill first before creating SVL.'
            ))
        if self.svl_created:
            raise UserError(_(
                'SVL has already been created for this bill.'
            ))

        self._create_svl_for_direct_bill()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _(
                    'Stock Valuation Layers created successfully for bill %s'
                ) % self.name,
                'type': 'success',
                'sticky': False,
            }
        }
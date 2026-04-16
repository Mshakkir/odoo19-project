from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Possible SVL model names depending on Odoo version / WMS module
SVL_MODEL_CANDIDATES = [
    'stock.valuation.layer',
    'stock.valuation.layer.revaluation',
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
        # Check product template level flags
        tmpl = getattr(product, 'product_tmpl_id', product)
        for field_name in ['is_storable', 'storable_ok',
                           'inventory_tracking', 'track_inventory']:
            if hasattr(tmpl, field_name) and getattr(tmpl, field_name):
                return True

        # Lot/Serial tracking means inventory is tracked
        tracking = getattr(product, 'tracking', 'none')
        if tracking and tracking != 'none':
            return True

        # Odoo 19 CE: if type='consu' and the Track Inventory box is checked,
        # Odoo stores this as type='consu' but the product participates in
        # stock moves. We treat ALL consu products with real_time valuation
        # as eligible — the _is_auto_valuation check gates this properly.
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
        If not found, lists all valuation-related models in the error
        so you can identify the correct model name.
        """
        for model_name in SVL_MODEL_CANDIDATES:
            if model_name in self.env.registry.models:
                try:
                    model = self.env[model_name]
                    model.search_count([('id', '=', 0)])
                    _logger.info('Using SVL model: %s', model_name)
                    return model
                except Exception as ex:
                    _logger.warning(
                        'Model %s in registry but not usable: %s',
                        model_name, ex
                    )
                    continue

        # Collect all valuation-related models to help diagnose
        valuation_models = sorted([
            m for m in self.env.registry.models
            if 'valuation' in m or 'svl' in m or 'layer' in m
        ])

        _logger.error(
            'stock.valuation.layer not found. '
            'Valuation-related models available: %s', valuation_models
        )

        raise UserError(_(
            'Cannot find stock.valuation.layer model.\n\n'
            'Valuation-related models found in your system:\n%s\n\n'
            'NEXT STEP: Run the diagnostic script (diagnostic_shell.py) '
            'in Odoo shell and share the output so the correct model '
            'name can be identified and used.'
        ) % ('\n'.join('  - ' + m for m in valuation_models)
             if valuation_models else '  (none found)'))

    def _create_svl_for_direct_bill(self):
        """
        Create Stock Valuation Layers and Stock Moves
        for direct vendor bills without PO.
        Compatible with Odoo 19 CE (Goods + Track Inventory).
        """
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
                'Please check your stock configuration.'
            ))

        svl_created_count = 0

        for line in self.invoice_line_ids:
            product = line.product_id

            if not product:
                continue

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
            for line in self.invoice_line_ids:
                p = line.product_id
                if p:
                    diag.append(
                        '• %s: type=%s | tracking=%s | is_storable=%s '
                        '| valuation=%s | costing=%s' % (
                            p.name,
                            p.type,
                            getattr(p, 'tracking', 'N/A'),
                            getattr(p, 'is_storable', 'N/A'),
                            getattr(p.categ_id, 'property_valuation', 'N/A'),
                            getattr(p.categ_id, 'property_cost_method', 'N/A'),
                        )
                    )

            raise UserError(_(
                'No Stock Valuation Layers were created!\n\n'
                'Product diagnostics:\n%s\n\n'
                'To fix, go to:\n'
                'Inventory → Configuration → Product Categories\n'
                '→ Open "Goods / Pneumatics Items"\n'
                '→ Set Costing Method (e.g. Average Cost)\n'
                '→ Set Inventory Valuation = Automated (Perpetual)\n\n'
                'Also confirm your products have:\n'
                '  Product Type = Goods  +  Track Inventory ✅ checked'
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
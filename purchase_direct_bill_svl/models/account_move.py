from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
                move._create_svl_for_direct_bill()
        return res

    def _create_svl_for_direct_bill(self):
        """
        Create Stock Valuation Layers and Stock Moves
        for direct vendor bills without PO.
        """
        svl_model = self.env['stock.valuation.layer']
        stock_move_model = self.env['stock.move']

        for line in self.invoice_line_ids:
            product = line.product_id

            # Only process storable products
            if (not product
                    or product.type != 'consu'
                    or not product.valuation == 'real_time'):
                continue

            # Skip if already linked to PO
            if line.purchase_line_id:
                continue

            # Get the incoming location
            location = self._get_incoming_location(line)

            # 1. Create Stock Move
            stock_move = stock_move_model.create({
                'name': _('Direct Bill: %s') % self.name,
                'product_id': product.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'location_id': self.env.ref(
                    'stock.stock_location_suppliers').id,
                'location_dest_id': location.id,
                'state': 'done',
                'origin': self.name,
                'account_move_ids': [(4, self.id)],
            })

            # 2. Create Stock Move Line
            stock_move.write({
                'move_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_id': line.product_uom_id.id,
                    'qty_done': line.quantity,
                    'location_id': self.env.ref(
                        'stock.stock_location_suppliers').id,
                    'location_dest_id': location.id,
                })]
            })

            # 3. Calculate unit cost (without tax)
            unit_cost = line.price_unit

            # 4. Create Stock Valuation Layer (SVL)
            svl_model.create({
                'product_id': product.id,
                'quantity': line.quantity,
                'unit_cost': unit_cost,
                'value': unit_cost * line.quantity,
                'stock_move_id': stock_move.id,
                'company_id': self.company_id.id,
                'description': _(
                    'Direct Bill %s - %s') % (self.name, product.name),
            })

            # 5. Update product standard price if AVCO
            if product.categ_id.property_cost_method == 'average':
                product._compute_average_price(
                    0, line.quantity, stock_move
                )

        # Mark SVL as created
        self.svl_created = True

    def _get_incoming_location(self, line):
        """Get the correct incoming stock location."""
        # Check if product has specific location
        if line.product_id.property_stock_inventory:
            return line.product_id.property_stock_inventory

        # Use company default incoming location
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if warehouse:
            return warehouse.lot_stock_id

        # Fallback to main stock location
        return self.env.ref('stock.stock_location_stock')

    def button_create_svl_manually(self):
        """Manual button to create SVL if auto-creation was skipped."""
        self.ensure_one()
        if self.move_type != 'in_invoice':
            raise UserError(_('SVL can only be created for vendor bills.'))
        if self.state != 'posted':
            raise UserError(_('Please confirm the bill first.'))
        if self.svl_created:
            raise UserError(_('SVL already created for this bill.'))

        self._create_svl_for_direct_bill()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Stock Valuation Layers created successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }
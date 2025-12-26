from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True, copy=False)
    create_delivery = fields.Boolean(string='Create Delivery Order', default=False,
                                     help='Check this to automatically create delivery order on invoice validation')

    def action_post(self):
        """Override the post method to create delivery order after invoice validation"""
        res = super(AccountMove, self).action_post()

        for invoice in self:
            # Only for customer invoices (out_invoice) with create_delivery flag
            if invoice.move_type == 'out_invoice' and invoice.create_delivery and not invoice.picking_id:
                invoice._create_delivery_from_invoice()

        return res

    def _create_delivery_from_invoice(self):
        """Create and validate delivery order from invoice"""
        self.ensure_one()

        # Check if there are stockable products
        stockable_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id and l.product_id.type == 'product'
        )

        if not stockable_lines:
            return

        # Get warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not warehouse:
            raise UserError(_('No warehouse found for company %s') % self.company_id.name)

        # Get stock location
        location_id = warehouse.lot_stock_id.id
        location_dest_id = self.env.ref('stock.stock_location_customers').id

        # Create picking (delivery order)
        picking_type = warehouse.out_type_id

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_type': 'direct',
            'company_id': self.company_id.id,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock moves for each invoice line
        for line in stockable_lines:
            if line.quantity <= 0:
                continue

            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': self.company_id.id,
                'picking_type_id': picking_type.id,
            }

            self.env['stock.move'].create(move_vals)

        # Confirm and validate the picking
        picking.action_confirm()

        # Auto-validate the picking (set quantities done)
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty

        picking.button_validate()

        # Link picking to invoice
        self.picking_id = picking.id

        return picking

    def action_view_delivery(self):
        """Smart button to view related delivery order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Order'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
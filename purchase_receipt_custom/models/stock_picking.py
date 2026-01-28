# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        compute='_compute_purchase_order_id',
        inverse='_inverse_purchase_order_id',
        store=False,
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]"
    )

    @api.depends('origin')
    def _compute_purchase_order_id(self):
        """Compute purchase order from origin field"""
        for picking in self:
            if picking.origin and picking.picking_type_code == 'incoming':
                # Try to find purchase order by name
                po = self.env['purchase.order'].search([
                    ('name', '=', picking.origin)
                ], limit=1)
                picking.purchase_order_id = po.id if po else False
            else:
                picking.purchase_order_id = False

    def _inverse_purchase_order_id(self):
        """When purchase order is selected, update origin and fill product lines"""
        for picking in self:
            if picking.purchase_order_id:
                picking.origin = picking.purchase_order_id.name
                # Auto-fill product lines from purchase order
                picking._auto_fill_from_purchase_order()

    @api.onchange('partner_id')
    def _onchange_partner_id_domain(self):
        """Clear purchase order when partner changes"""
        if self.partner_id:
            # Clear purchase order if partner changed
            if self.purchase_order_id and self.purchase_order_id.partner_id != self.partner_id:
                self.purchase_order_id = False
                self.origin = False
        else:
            self.purchase_order_id = False
            self.origin = False

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        """Auto-fill move lines when purchase order is selected"""
        if self.purchase_order_id:
            self.origin = self.purchase_order_id.name
            self._auto_fill_from_purchase_order()

    def _auto_fill_from_purchase_order(self):
        """Fill product lines from selected purchase order"""
        self.ensure_one()

        if not self.purchase_order_id or self.state not in ['draft', 'waiting', 'confirmed', 'assigned']:
            return

        # Clear existing move lines that are not done
        self.move_ids.filtered(lambda m: m.state != 'done').unlink()

        # Create move lines from purchase order lines
        move_lines = []
        for po_line in self.purchase_order_id.order_line:
            if po_line.product_id.type in ['product', 'consu']:
                # Calculate quantity to receive (ordered - already received)
                qty_to_receive = po_line.product_qty - po_line.qty_received

                if qty_to_receive > 0:
                    move_vals = {
                        'name': po_line.name or po_line.product_id.display_name,
                        'product_id': po_line.product_id.id,
                        'product_uom_qty': qty_to_receive,
                        'product_uom': po_line.product_uom.id,
                        'location_id': self.location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'picking_id': self.id,
                        'company_id': self.company_id.id,
                        'date': self.scheduled_date,
                        'date_deadline': self.date_deadline,
                        'picking_type_id': self.picking_type_id.id,
                        'partner_id': self.partner_id.id,
                        'state': 'draft',
                        'origin': self.origin,
                        'description_picking': po_line.name,
                    }
                    move_lines.append((0, 0, move_vals))

        if move_lines:
            self.move_ids = move_lines
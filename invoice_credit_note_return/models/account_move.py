# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    return_picking_count = fields.Integer(
        string='Return Count',
        compute='_compute_return_picking_count',
        store=False
    )
    return_picking_ids = fields.Many2many(
        'stock.picking',
        string='Return Pickings',
        compute='_compute_return_picking_ids',
        store=False
    )

    @api.depends('invoice_line_ids')
    def _compute_return_picking_count(self):
        """Compute the number of return pickings linked to this credit note"""
        for move in self:
            if move.move_type == 'out_refund':
                # Find return pickings based on the original invoice
                original_invoice = move.reversed_entry_id
                if original_invoice:
                    pickings = self.env['stock.picking'].search([
                        ('origin', '=', original_invoice.name),
                        ('picking_type_code', '=', 'incoming'),
                        ('state', '!=', 'cancel')
                    ])
                    move.return_picking_count = len(pickings)
                else:
                    move.return_picking_count = 0
            else:
                move.return_picking_count = 0

    @api.depends('invoice_line_ids')
    def _compute_return_picking_ids(self):
        """Compute return pickings linked to this credit note"""
        for move in self:
            if move.move_type == 'out_refund':
                original_invoice = move.reversed_entry_id
                if original_invoice:
                    pickings = self.env['stock.picking'].search([
                        ('origin', '=', original_invoice.name),
                        ('picking_type_code', '=', 'incoming'),
                        ('state', '!=', 'cancel')
                    ])
                    move.return_picking_ids = pickings
                else:
                    move.return_picking_ids = False
            else:
                move.return_picking_ids = False

    def action_create_return(self):
        """Create a return picking for the credit note"""
        self.ensure_one()

        if self.move_type != 'out_refund':
            raise UserError(_('This function is only available for credit notes.'))

        # Get the original invoice
        original_invoice = self.reversed_entry_id
        if not original_invoice:
            raise UserError(_('No original invoice found for this credit note.'))

        # Find the delivery order(s) related to the original invoice
        sale_order = self.env['sale.order'].search([
            ('name', '=', original_invoice.invoice_origin)
        ], limit=1)

        if not sale_order:
            raise UserError(_('No sale order found for this invoice.'))

        # Get outgoing pickings from the sale order
        outgoing_pickings = sale_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
        )

        if not outgoing_pickings:
            raise UserError(_('No validated delivery found for this sale order.'))

        # Use the first delivery (or you could let user choose)
        picking_to_return = outgoing_pickings[0]

        # Create return wizard
        return_picking_wizard = self.env['stock.return.picking'].with_context(
            active_id=picking_to_return.id,
            active_model='stock.picking'
        ).create({})

        # Get product lines from credit note
        credit_note_products = {}
        for line in self.invoice_line_ids:
            if line.product_id and line.product_id.type in ['product', 'consu']:
                credit_note_products[line.product_id.id] = abs(line.quantity)

        # Update return wizard lines to match credit note quantities
        for wizard_line in return_picking_wizard.product_return_moves:
            product_id = wizard_line.product_id.id
            if product_id in credit_note_products:
                wizard_line.quantity = credit_note_products[product_id]
            else:
                # Set to 0 if not in credit note
                wizard_line.quantity = 0

        # Create the return picking
        return_wizard_result = return_picking_wizard.create_returns()

        if return_wizard_result and 'res_id' in return_wizard_result:
            return_picking_id = return_wizard_result['res_id']
            return_picking = self.env['stock.picking'].browse(return_picking_id)

            # Update the origin to link with the credit note
            return_picking.write({
                'origin': f"{original_invoice.name} - Credit Note: {self.name}"
            })

            # Open the created return picking
            return {
                'name': _('Return Delivery'),
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_mode': 'form',
                'res_id': return_picking_id,
                'target': 'current',
            }

        raise UserError(_('Failed to create return picking.'))

    def action_view_returns(self):
        """View return pickings related to this credit note"""
        self.ensure_one()

        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.return_picking_ids

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        else:
            action['domain'] = [('id', '=', False)]

        return action
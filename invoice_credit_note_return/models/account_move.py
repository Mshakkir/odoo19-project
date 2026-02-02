# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_count = fields.Integer(
        string='Delivery Count',
        compute='_compute_delivery_count',
        store=False
    )

    def _compute_delivery_count(self):
        """Compute the number of deliveries linked to this invoice"""
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                # For credit notes, try to find the original invoice's delivery
                if move.move_type == 'out_refund' and move.reversed_entry_id:
                    original_invoice = move.reversed_entry_id
                    invoice_to_check = original_invoice
                else:
                    invoice_to_check = move

                # Search for stock pickings by invoice name
                pickings = self.env['stock.picking'].search([
                    '|',
                    ('origin', 'ilike', invoice_to_check.name),
                    ('sale_id.name', '=', invoice_to_check.invoice_origin),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '!=', 'cancel')
                ])

                # Alternative: search by sale order if invoice_origin exists
                if not pickings and invoice_to_check.invoice_origin:
                    pickings = self.env['stock.picking'].search([
                        ('origin', '=', invoice_to_check.invoice_origin),
                        ('picking_type_code', '=', 'outgoing'),
                        ('state', '!=', 'cancel')
                    ])

                move.delivery_count = len(pickings)
            else:
                move.delivery_count = 0

    def action_view_delivery(self):
        """View delivery orders related to this invoice or credit note"""
        self.ensure_one()

        # For credit notes, get the original invoice
        if self.move_type == 'out_refund' and self.reversed_entry_id:
            invoice_to_check = self.reversed_entry_id
        else:
            invoice_to_check = self

        # Search for stock pickings
        pickings = self.env['stock.picking'].search([
            '|',
            ('origin', 'ilike', invoice_to_check.name),
            ('sale_id.name', '=', invoice_to_check.invoice_origin),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '!=', 'cancel')
        ])

        # Alternative search if not found
        if not pickings and invoice_to_check.invoice_origin:
            pickings = self.env['stock.picking'].search([
                ('origin', '=', invoice_to_check.invoice_origin),
                ('picking_type_code', '=', 'outgoing'),
                ('state', '!=', 'cancel')
            ])

        if not pickings:
            raise UserError(_('No delivery order found for this invoice.'))

        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
            action['view_mode'] = 'tree,form'
        else:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
            action['view_mode'] = 'form'

        # Add context to help users understand they need to use the Return button
        if self.move_type == 'out_refund':
            action['context'] = {
                'default_origin': f"{invoice_to_check.name} - Credit Note: {self.name}"
            }
            action['help'] = """<p>This is the original delivery for the invoice.</p>
                              <p>To process a return:</p>
                              <ol>
                                <li>Click the "Return" button at the top of this delivery order</li>
                                <li>Adjust quantities to match your credit note</li>
                                <li>Validate the return</li>
                              </ol>"""

        return action
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
    delivery_picking_ids = fields.Many2many(
        'stock.picking',
        string='Deliveries',
        compute='_compute_delivery_picking_ids',
        store=False
    )

    @api.depends('name', 'partner_id')
    def _compute_delivery_count(self):
        """Compute the number of deliveries linked to this invoice/credit note"""
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                # For credit notes, find deliveries from the original invoice
                if move.move_type == 'out_refund' and move.reversed_entry_id:
                    invoice_name = move.reversed_entry_id.name
                else:
                    invoice_name = move.name

                # Search for pickings linked to this invoice
                pickings = self.env['stock.picking'].search([
                    '|',
                    ('origin', 'ilike', invoice_name),
                    ('origin', 'ilike', move.name),
                    ('partner_id', '=', move.partner_id.id),
                    ('state', '!=', 'cancel')
                ])
                move.delivery_count = len(pickings)
            else:
                move.delivery_count = 0

    @api.depends('name', 'partner_id')
    def _compute_delivery_picking_ids(self):
        """Compute deliveries linked to this invoice/credit note"""
        for move in self:
            if move.move_type in ['out_invoice', 'out_refund']:
                # For credit notes, find deliveries from the original invoice
                if move.move_type == 'out_refund' and move.reversed_entry_id:
                    invoice_name = move.reversed_entry_id.name
                else:
                    invoice_name = move.name

                # Search for pickings linked to this invoice
                pickings = self.env['stock.picking'].search([
                    '|',
                    ('origin', 'ilike', invoice_name),
                    ('origin', 'ilike', move.name),
                    ('partner_id', '=', move.partner_id.id),
                    ('state', '!=', 'cancel')
                ])
                move.delivery_picking_ids = pickings
            else:
                move.delivery_picking_ids = False

    def action_view_delivery(self):
        """View deliveries related to this invoice/credit note"""
        self.ensure_one()

        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.delivery_picking_ids

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        else:
            action['domain'] = [('id', '=', False)]

        return action
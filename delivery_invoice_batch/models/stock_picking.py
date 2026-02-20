from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        compute='_compute_invoice_ids',
        store=False,
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_ids',
        store=False,
    )

    @api.depends('name')
    def _compute_invoice_ids(self):
        for picking in self:
            invoices = self.env['account.move'].search([
                ('invoice_origin', 'ilike', picking.name)
            ])
            picking.invoice_ids = invoices
            picking.invoice_count = len(invoices)

    def action_create_invoice(self):
        """Open wizard to create invoice from delivery notes"""
        return {
            'name': _('Create Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'stock.picking',
            }
        }

    def action_view_invoices(self):
        """View invoices related to this delivery note"""
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }
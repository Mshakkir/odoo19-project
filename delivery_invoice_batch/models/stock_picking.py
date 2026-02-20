import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_logger.info("DEBUG delivery_invoice_batch: stock_picking.py module-level code executing")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    _logger.info("DEBUG delivery_invoice_batch: StockPicking class body executing")

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
        _logger.info(
            "DEBUG delivery_invoice_batch: action_create_invoice called on pickings: %s",
            self.ids
        )
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
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    invoiced = fields.Boolean(
        string='Invoiced',
        compute='_compute_invoiced',
        store=True,
        help="Indicates if this delivery has been invoiced"
    )

    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        compute='_compute_invoice_ids',
        help="Invoices linked to this delivery"
    )

    @api.depends('move_ids.sale_line_id.invoice_lines')
    def _compute_invoiced(self):
        """Check if delivery is invoiced"""
        for picking in self:
            invoiced = False
            if picking.sale_id:
                # Check if related sale order lines are invoiced
                sale_lines = picking.move_ids.mapped('sale_line_id')
                if sale_lines and all(line.qty_invoiced >= line.product_uom_qty for line in sale_lines):
                    invoiced = True
            picking.invoiced = invoiced

    @api.depends('move_ids.sale_line_id.invoice_lines.move_id')
    def _compute_invoice_ids(self):
        """Get related invoices"""
        for picking in self:
            invoices = picking.move_ids.mapped('sale_line_id.invoice_lines.move_id').filtered(
                lambda m: m.state != 'cancel'
            )
            picking.invoice_ids = invoices

    def action_open_delivery_invoice_wizard(self):
        """Open wizard to create invoice from multiple deliveries"""
        return {
            'name': 'Create Invoice from Deliveries',
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_ids': self.ids,
                'default_partner_id': self[0].partner_id.id if len(set(self.mapped('partner_id'))) == 1 else False,
            }
        }